import copy
import itertools
import numbers
import tempfile
import codecs
import yaml
import uuid
import hashlib
import collections

__version__ = "0.2"

BUFF_SIZE = 65536 # 64kb

class CorrectionStack:
    def __init__(self, labels, event_file, ops_file, load, apply=False):
        """Creates a CorrectionStack.
        
           labels -- a list of dicts denoted event data
           event_file -- filename string
           ops_file -- filename string to save operations
           load -- bool; if True, load from ops_file
           apply -- bool; if True and if load, apply corrections in ops_file"""
        self.labels = labels
        self.file = ops_file
        if load:
            self.read_from_file(apply=apply)
        else:
            self.undo_stack = collections.deque()
            self.redo_stack = collections.deque()
            self.uuid = str(uuid.uuid4())
            self.evfile_hash = _buff_hash_file(event_file)
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_value, exc_trace):
        if exc_type is None:
            self.write_to_file()
            return True
        else:
            self.write_to_file(self.file + '.bak')
            return False
    
    def read_from_file(self, file=None, apply=False):
        """Read a stack of corrections plus metadata from file.
           
           file -- if not present, use self.file
           apply -- bool; if True, apply loaded corrections
                          if False, assume corrections already applied"""
        if file:
            self.file = file
        with codecs.open(self.file, 'r', encoding='utf-8') as fp:
            self.undo_stack = collections.deque()
            self.redo_stack = collections.deque()
            for op in fp:
                if op != '\n':
                    if apply:
                        self.push(op.strip())
                    else:
                        self.undo_stack.append(op.strip())
        meta_name = self.file + '.yaml'
        with codecs.open(meta_name, 'r', encoding='utf-8') as mdfp:
            file_data = yaml.safe_load(mdfp)
            self.uuid = file_data['uuid']
            self.evfile_hash = file_data['evfile_hash']
    
    def write_to_file(self, file=None):
        """Write stack of corrections plus metadata to file.
           
           file -- if not present, use self.file"""
        if file:
            self.file = file
        with codecs.open(self.file, 'w', encoding='utf-8') as fp:
            for op in self.undo_stack:
                fp.write(op + '\n')
        meta_name = self.file + '.yaml'
        with codecs.open(meta_name, 'w', encoding='utf-8') as mdfp:
            file_data = {'uuid': self.uuid,
                         'evfile_hash': self.evfile_hash}
            header = """# corrections file using YAML syntax\n---\n"""
            mdfp.write(header)
            mdfp.write(yaml.safe_dump(file_data, default_flow_style=False))
    
    def undo(self):
        """Undoes last executed command, if any."""
        try:
            cmd = self.undo_stack.pop()
        except IndexError:
            pass
        else:
            inv = invert(cmd)
            self.redo_stack.append(inv)
            self._apply(inv)
    
    def redo(self):
        """Redoes last undone command, if any."""
        try:
            cmd = self.redo_stack.pop()
        except IndexError:
            pass
        else:
            inv = invert(cmd)
            self.undo_stack.append(inv)
            self._apply(inv)
    
    def push(self, cmd):
        """Executes command, discarding redo stack."""
        if self.redo_stack:
            self.redo_stack = collections.deque()
        self.undo_stack.append(cmd)
        self._apply(cmd)
    
    def peek(self, index=-1):
        """Returns command string at top of undo stack, or index."""
        return self.undo_stack[index]
    
    def _apply(self, cmd):
        """Executes command string, applied to labels."""
        evaluate(parse(cmd), make_env(labels=self.labels))
    
    # operations
    
    def rename(self, index, new_name):
        """Renames an event."""
        self.push(self.codegen_rename(index, new_name))
    
    def set_start(self, index, new_start):
        """Changes the start time of an event."""
        self.push(self.codegen_set_start(index, new_start))
    
    def set_stop(self, index, new_stop):
        """Changes the stop time of an event."""
        self.push(self.codegen_set_stop(index, new_stop))
    
    def merge_next(self, index, new_name=None):
        """Merges an event with its successor."""
        self.push(self.codegen_merge_next(index, new_name))
    
    def split(self, index, new_sep, new_name=None, new_next_name=None):
        """Splits an event in two."""
        self.push(self.codegen_split(index, new_sep, new_name, new_next_name))
    
    def delete(self, index):
        """Deletes an event."""
        self.push(self.codegen_delete(index))
    
    def create(self, index, start, **kwargs):
        """Creates a new event."""
        self.push(self.codegen_create(index, start, **kwargs))
    
    # code generators
    
    def _gen_code(self, op, target_name, target, other_args):
        """Generates a command string for the given op.
           
           op -- string
           target_name -- string
           target -- dict
           other_args -- dict"""
        ntl = [Symbol(op)]
        ntl.append(KeyArg('labels'))
        ntl.append(Symbol('labels'))
        ntl.append(KeyArg('target'))
        ntl.append([Symbol(target_name)])
        for k, a in target.items():
            ntl[-1].append(KeyArg(k))
            ntl[-1].append(a)
        for k, a in other_args.items():
            ntl.append(KeyArg(k))
            ntl.append(a)
        return detokenize(write_to_tokens(ntl))

    def codegen_rename(self, index, new_name):
        """Generates command string to rename an interval.
           
           new_name -- string"""
        op = 'set_name'
        target_name = 'interval'
        target = {'index': index,
                  'name': self.labels[index]['name']}
        other_args = {'new_name': new_name}
        return self._gen_code(op, target_name, target, other_args)

    def codegen_set_start(self, index, new_start):
        """Generates command string to move an interval's start.
           
           new_start -- float"""
        op = 'set_boundary'
        target_name = 'interval'
        target = {'index': index,
                  'bd': self.labels[index]['start']}
        other_args = {'which': 'start', 'new_bd': new_start}
        return self._gen_code(op, target_name, target, other_args)

    def codegen_set_stop(self, index, new_stop):
        """Generates command string to move an interval's stop.
           
           new_stop -- float"""
        op = 'set_boundary'
        target_name = 'interval'
        target = {'index': index,
                  'bd': self.labels[index]['stop']}
        other_args = {'which': 'stop', 'new_bd': new_stop}
        return self._gen_code(op, target_name, target, other_args)

    def codegen_merge_next(self, index, new_name=None):
        """Generates command string to merge an interval and its successor.
           
           new_name -- string; if absent, new interval name is concatenation
                       of two parents' names"""
        op = 'merge_next'
        target_name = 'interval_pair'
        target = {'index': index,
                  'name': self.labels[index]['name'],
                  'stop': self.labels[index]['stop'],
                  'next_start': self.labels[index + 1]['start'],
                  'next_name': self.labels[index + 1]['name']}
        if new_name is None:
            new_name = target['name'] + target['next_name']
        other_args = {'new_name': new_name,
                      'new_stop': None,
                      'new_next_start': None,
                      'new_next_name': None}
        columns = [c for c in self.labels[index].keys()
                   if c not in ('start', 'stop', 'name')]
        for c in columns:
            target[c] = self.labels[index][c]
            target['next_' + c] = self.labels[index + 1][c]
            other_args['new_' + c] = None
            other_args['new_next_' + c] = None
        return self._gen_code(op, target_name, target, other_args)

    def codegen_split(self, index, new_sep, new_name=None,
                      new_next_name=None, **kwargs):
        """Generates command string to split an interval in two.
           
           new_sep -- number; must be within interval's limits
           new_name -- string; if absent"""
        op = 'split'
        target_name = 'interval_pair'
        target = {'index': index,
                  'name': self.labels[index]['name'],
                  'stop': self.labels[index]['stop'],
                  'next_name': None,
                  'next_start': None,}
        if new_name is None:
            new_name = target['name']
        if new_next_name is None:
            new_next_name = ''
        other_args = {'new_name': new_name,
                      'new_stop': new_sep,
                      'new_next_start': new_sep,
                      'new_next_name': new_next_name}
        columns = [c for c in self.labels[index].keys()
                   if c not in ('start', 'stop', 'name')]
        for c in columns:
            target[c] = self.labels[index][c]
            target['next_' + c] = None
            other_args['new_' + c] = kwargs['new_' + c]
            other_args['new_next_' + c] = kwargs['new_next_' + c]
        return self._gen_code(op, target_name, target, other_args)

    def codegen_delete(self, index):
        """Generates command string to delete an interval."""
        op = 'delete'
        target_name = 'interval'
        target = {'index': index}
        target.update(self.labels[index])
        other_args = {}
        return self._gen_code(op, target_name, target, other_args)

    def codegen_create(self, index, start, **kwargs):
        """Generates command string to create a new interval.
           
           start -- float
           kwargs -- any other column values the interval possesses"""
        op = 'create'
        target_name = 'interval'
        target = {'index': index,
                  'start': start}
        target.update(kwargs)
        other_args = {}
        return self._gen_code(op, target_name, target, other_args)


# raw operations

def _set_name(labels, target, new_name, **kwargs):
    labels[target['index']]['name'] = new_name

def _set_bd(labels, target, which, new_bd, **kwargs):
    if which not in ('start', 'stop'):
        raise KeyError('boundary name not recognized: ' + which)
    labels[target['index']][which] = new_bd

def _merge_next(labels, target, **kwargs):
    index = target['index']
    labels[index]['stop'] = labels[index + 1]['stop']
    labels[index]['name'] = kwargs['new_name']
    labels.pop(index + 1)

def _split(labels, target, **kwargs):
    if not (kwargs['new_stop'] > labels[target['index']]['start'] and
            kwargs['new_next_start'] < labels[target['index']]['stop']):
        raise ValueError('split point must be within interval')
    index = target['index']
    new_point = copy.deepcopy(labels[index])
    for key in kwargs:
        if key[:9] == 'new_next_':
            new_point[key[9:]] = kwargs[key]
        elif key[:4] == 'new_':
            labels[index][key[4:]] = kwargs[key]
    labels.insert(index + 1, new_point)

def _delete(labels, target, **kwargs):
    labels.pop(target['index'])

def _create(labels, target, **kwargs):
    index = target['index']
    new_point = {'start': target['start'],
                 'stop': target['stop'],
                 'name': target['name']}
    del target['start'], target['stop'], target['name'], target['index']
    new_point.update(target)
    labels.insert(index, new_point)

# invert operations

INVERSE_TABLE = {'set_name': 'set_name',
                 'set_boundary': 'set_boundary',
                 'merge_next': 'split',
                 'split': 'merge_next',
                 'delete': 'create',
                 'create': 'delete'}

def invert(cmd):
    """Generates a command string for the inverse of cmd."""
    ntl = parse(cmd)
    op = ntl[0]
    inverse = INVERSE_TABLE[op]
    target = ntl[ntl.index('target') + 1]
    for i in range(len(ntl)):
        curr = ntl[i]
        if isinstance(curr, KeyArg) and len(curr) >= 4 and curr[:4] == 'new_':
            oldname = curr[4:]
            oldval = copy.deepcopy(target[target.index(oldname) + 1])
            target[target.index(oldname) + 1] = copy.deepcopy(ntl[i + 1])
            ntl[i + 1] = oldval
    inverse_ntl = [Symbol(inverse)]
    inverse_ntl.extend(ntl[1:])
    return detokenize(write_to_tokens(inverse_ntl))

# reverse parsing

def detokenize(token_list):
    """Turns a flat list of tokens into a command."""
    cmd = token_list[0]
    for t in token_list[1:]:
        if t != ')' and cmd[-1] != '(':
            cmd += ' '
        cmd += t
    return cmd

def write_to_tokens(ntl):
    """Turns an s-expression into a flat token list."""
    token_list = ['(']
    for t in ntl:
        if isinstance(t, list):
            token_list.extend(write_to_tokens(t))
        else:
            token_list.append(deatomize(t))
    token_list.append(')')
    return token_list

def deatomize(a):
    """Turns an atom into a token."""
    if a is None:
        return 'null'
    elif isinstance(a, Symbol):
        ret = a[0] + a[1:].replace('_', '-')
        if isinstance(a, KeyArg):
            ret = '#:' + ret
        return ret
    elif isinstance(a, str):
        return '"' + a + '"'
    elif isinstance(a, numbers.Number):
        return str(a)
    else:
        raise ValueError('unknown atomic type: ' + str(a))

# parser & evaluator

class Symbol(str): pass

class KeyArg(Symbol): pass

def tokenize(cmd):
    """Turns a command string into a flat token list."""
    second_pass = []
    in_string = False
    for token in cmd.split():
        num_quotes = token.count('"')
        if num_quotes % 2 == 1 and not in_string: # open quote
            second_pass.append(token)
            in_string = True
        elif num_quotes % 2 == 1 and in_string: # close quote
            second_pass[-1] += ' ' + token
            in_string = False
        elif num_quotes == 0 and in_string: # middle words in quote
            second_pass[-1] += ' ' + token
        else:
            second_pass.append(token)
    third_pass = []
    for token in second_pass:
        if token[0] == '(':
            third_pass.append('(')
            if len(token) > 1:
                third_pass.append(token[1:])
        elif token[-1] == ')':
            ct = token.count(')')
            third_pass.append(token[:-ct])
            for _ in range(ct):
                third_pass.append(')')
        else:
            third_pass.append(token)
    return third_pass


def atomize(token):
    """Turns a token into an atom."""
    if token[0] == '"':
        try:
            return token[1:-1].decode('string_escape')
        except AttributeError: # python 2/3 support
            return token[1:-1]
    if token == 'null':
        return None
    try:
        return int(token)
    except ValueError:
        try:
            return float(token)
        except ValueError:
            token = token[0] + token[1:].replace('-', '_')
            if token[:2] == '#:':
                return KeyArg(token[2:])
            return Symbol(token)


def read_from_tokens(token_list):
    """Turns a flat token list into an s-expression."""
    if len(token_list) == 0:
        raise SyntaxError('unexpected EOF')
    token = token_list.pop(0)
    if token == '(':
        nested_list = []
        while token_list[0] != ')':
            nested_list.append(read_from_tokens(token_list))
        token_list.pop(0)
        return nested_list
    elif token == ')':
        raise SyntaxError('unexpected )')
    else:
        return atomize(token)


def parse(cmd):
    """Turns a command string into an s-expression."""
    return read_from_tokens(tokenize(cmd))


def make_env(**kwargs):
    """Returns an environment for s-expression evaluation."""
    env = {'set_name': _set_name,
           'set_boundary': _set_bd,
           'merge_next': _merge_next,
           'split': _split,
           'delete': _delete,
           'create': _create,
           'interval': dict,
           'interval_pair': dict}
    env.update(kwargs)
    return env


def evaluate(expr, env=make_env()):
    """Evaluates an s-expression in the context of an environment."""
    if isinstance(expr, Symbol):
        return env[expr]
    elif not isinstance(expr, list):
        return expr
    else:
        proc = evaluate(expr[0], env)
        kwargs = {p[0]: evaluate(p[1], env) for p in _grouper(expr[1:], 2)}
        return proc(**kwargs)


def _grouper(iterable, n):
    """Returns nonoverlapping windows of input of length n.
    
       Copied from itertools recipe suggestions."""
    args = [iter(iterable)] * n
    try:
        return itertools.izip_longest(*args)
    except AttributeError: # python 2/3 support
        return itertools.zip_longest(*args)

def _buff_hash_file(filename):
    with open(filename, 'rb') as file:
        data = file.read(BUFF_SIZE)
        hash = hashlib.sha1()
        while data:
            hash.update(data)
            data = file.read(BUFF_SIZE)
    return hash.hexdigest()
