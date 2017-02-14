import copy
import itertools
import numbers
import tempfile
import codecs
import yaml
import uuid

class CorrectionStack:
    def __init__(self, labels, label_file=None, apply=False,
                 corr_file=None, dir=None, no_file=False):
        """Creates a CorrectionStack.
        
           labels -- a list of dicts denoted event data
           label_file -- filename string
           apply -- bool; if True corrections in corr_file are applied
           corr_file -- filename string; if None, a tempfile is made
           dir -- directory in which to create tempfile
           no_file -- bool; if True, no file is created or used"""
        self.labels = labels
        if corr_file is None:
            if no_file:
                self.corr_file = None
            else:
                temp_file = tempfile.NamedTemporaryFile(mode='w',
                                                        suffix='.corr',
                                                        dir=dir,
                                                        delete=False)
                temp_file.close()
                self.corr_file = temp_file.name
            self.stack = []
            self.pc = -1
            self.written = self.pc
            self.dirty = True
            self.uuid = str(uuid.uuid4())
            self.label_file = label_file
        else:
            self.read_from_file(corr_file, already_applied=(not apply))
            if apply:
                self.redo_all()
    
    def read_from_file(self, file=None, already_applied=True):
        """Read a stack of corrections plus metadata from file.
           
           file -- if not present, use self.file
           already_applied -- bool; if False, apply loaded corrections"""
        if file is None:
            file = self.corr_file
        with codecs.open(file, 'r', encoding='utf-8') as fp:
            file_data = yaml.safe_load(fp)
            self.uuid = file_data['uuid']
            self.stack = file_data['operations']
            self.label_file = file_data['label_file']
        self.corr_file = file
        self.written = len(self.stack) - 1
        self.dirty = False
        if already_applied:
            self.pc = self.written
        else:
            self.pc = -1
    
    def write_to_file(self, file=None):
        """Write stack of corrections plus metadata to file.
           
           file -- if not present, use self.file"""
        if file is None:
            file = self.corr_file
        with codecs.open(file, 'w', encoding='utf-8') as fp:
            file_data = {'uuid': self.uuid,
                         'label_file': self.label_file,
                         'operations': self.stack[:self.pc + 1]}
            header = """# corrections file using YAML syntax\n---\n"""
            fp.write(header)
            fp.write(yaml.safe_dump(file_data, default_flow_style=False))
    
    def undo(self):
        """Undoes last applied correction.
           
           No effect if pc is at bottom of stack.
           If dipping below written pointer, set dirty flag."""
        if self.pc >= 0:
            self._apply(invert(self.stack[self.pc]))
            self.pc -= 1
            if self.pc < self.written:
                self.dirty = True
    
    def redo(self):
        """Redoes next undone correction.
           
           No effect if pc is at top of stack."""
        stacklen = len(self.stack)
        if stacklen > 0 and self.pc < stacklen - 1:
            self.pc += 1
            self._apply(self.stack[self.pc])
    
    def push(self, cmd):
        """Adds command string to top of stack and execute it.
           
           If pc not at top of stack, discards entire stack above it."""
        if self.pc >= 0 and self.pc < len(self.stack) - 1:
            self.stack = self.stack[:(self.pc + 1)]
        self.stack.append(cmd)
        self.pc += 1
        self._apply(cmd)
    
    def peek(self, index=None):
        """Returns command string at top of stack, or index.
           
           If index is outside stack, returns None."""
        if index is None:
            index = self.pc
        if index < len(self.stack) and index >= 0:
            return self.stack[index]
        else:
            return None
    
    def _apply(self, cmd):
        """Executes command string, applied to labels."""
        env = lc_env()
        env.update({'labels': self.labels})
        evaluate(parse(cmd), env)
    
    def redo_all(self):
        """Executes all commands above pc in stack."""
        while self.pc < len(self.stack) - 1:
            self.redo()
    
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

    def rename(self, index, new_name):
        """Generates command string to rename an interval.
           
           new_name -- string"""
        op = 'set_name'
        target_name = 'interval'
        target = {'index': index,
                  'name': self.labels[index]['name']}
        other_args = {'new_name': new_name}
        return self._gen_code(op, target_name, target, other_args)

    def set_start(self, index, new_start):
        """Generates command string to move an interval's start.
           
           new_start -- float"""
        op = 'set_boundary'
        target_name = 'interval'
        target = {'index': index,
                  'bd': self.labels[index]['start']}
        other_args = {'which': 'start', 'new_bd': new_start}
        return self._gen_code(op, target_name, target, other_args)

    def set_stop(self, index, new_stop):
        """Generates command string to move an interval's stop.
           
           new_stop -- float"""
        op = 'set_boundary'
        target_name = 'interval'
        target = {'index': index,
                  'bd': self.labels[index]['stop']}
        other_args = {'which': 'stop', 'new_bd': new_stop}
        return self._gen_code(op, target_name, target, other_args)

    def merge_next(self, index, new_name=None):
        """Generates command string to merge an interval and its successor.
           
           new_name -- string; if absent, new interval name is concatenation
                       of two parents' names"""
        op = 'merge_next'
        target_name = 'interval_pair'
        target = {'index': index,
                  'name': self.labels[index]['name'],
                  'sep': self.labels[index]['stop'],
                  'next_name': self.labels[index + 1]['name']}
        if new_name is None:
            new_name = target['name'] + target['next_name']
        other_args = {'new_name': new_name,
                      'new_sep': None,
                      'new_next_name': None}
        return self._gen_code(op, target_name, target, other_args)

    def split(self, index, new_sep, new_name=None, new_next_name=None):
        """Generates command string to split an interval in two.
           
           new_sep -- number; must be within interval's limits
           new_name -- string; if absent"""
        op = 'split'
        target_name = 'interval_pair'
        target = {'index': index,
                  'name': self.labels[index]['name'],
                  'sep': None,
                  'next_name': None}
        if new_name is None:
            new_name = target['name']
        if new_next_name is None:
            new_next_name = ''
        other_args = {'new_name': new_name,
                      'new_sep': new_sep,
                      'new_next_name': new_next_name}
        return self._gen_code(op, target_name, target, other_args)

    def delete(self, index):
        """Generates command string to delete an interval."""
        op = 'delete'
        target_name = 'interval'
        target = {'index': index}
        target.update(self.labels[index])
        other_args = {}
        return self._gen_code(op, target_name, target, other_args)

    def create(self, index, start, **kwargs):
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

def _split(labels, target, new_name, new_sep, new_next_name, **kwargs):
    if not (new_sep > labels[target['index']]['start'] and
            new_sep < labels[target['index']]['stop']):
        raise ValueError('split point must be within interval')
    index = target['index']
    new_point = copy.deepcopy(labels[index])
    new_point['start'] = new_sep
    new_point['name'] = new_next_name
    labels[index]['stop'] = new_sep
    labels[index]['name'] = new_name
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


def lc_env():
    """Returns the default environment for s-expression evaluation."""
    env = {'set_name': _set_name,
           'set_boundary': _set_bd,
           'merge_next': _merge_next,
           'split': _split,
           'delete': _delete,
           'create': _create,
           'interval': dict,
           'interval_pair': dict}
    return env


def evaluate(expr, env=lc_env()):
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
