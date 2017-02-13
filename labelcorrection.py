import copy
import itertools
import numbers
import tempfile

class CorrectionStack:
    def __init__(self):
        self.labels = []
        self.stack = []
        self.pc = -1
        self.written = -1
        self.dirty = True
        self.file = tempfile.NamedTemporaryFile(mode='w',
                                                suffix='.corr',
                                                delete=False)
    
    def undo(self):
        if self.pc >= 0:
            self.apply(invert(self.stack[self.pc]))
            self.pc -= 1
            if self.pc < self.written:
                self.dirty = True
    
    def redo(self):
        stacklen = len(self.stack)
        if stacklen > 0 and self.pc < stacklen - 1:
            self.pc += 1
            self.apply(self.stack[self.pc])
    
    def push(self, cmd):
        if self.pc >= 0 and self.pc < len(self.stack) - 1:
            self.stack = self.stack[:(self.pc + 1)]
        self.stack.append(cmd)
        self.pc += 1
        self.apply(cmd)
    
    def pop(self):
        self.undo()
        return self.peek(self.pc + 1)
    
    def peek(self, index=self.pc):
        if index < len(self.stack) and index >= 0:
            return self.stack[self.pc]
        else
            return None
    
    def apply(self, cmd):
        env = lc_env()
        env.update({'labels': self.labels})
        evaluate(parse(cmd), env)

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


# code-generators

def _gen_code(op, target_name, target, other_args):
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

def cg_set_name(labels, index, new_name):
    op = 'set_name'
    target_name = 'interval'
    target = {'index': index,
              'name': labels[index]['name']}
    other_args = {'new_name': new_name}
    return _gen_code(op, target_name, target, other_args)

def cg_set_start(labels, index, new_start):
    op = 'set_boundary'
    target_name = 'interval'
    target = {'index': index,
              'bd': labels[index]['start']}
    other_args = {'which': 'start', 'new_bd': new_start}
    return _gen_code(op, target_name, target, other_args)

def cg_set_stop(labels, index, new_stop):
    op = 'set_boundary'
    target_name = 'interval'
    target = {'index': index,
              'bd': labels[index]['stop']}
    other_args = {'which': 'stop', 'new_bd': new_stop}
    return _gen_code(op, target_name, target, other_args)

def cg_merge_next(labels, index, new_name=None):
    op = 'merge_next'
    target_name = 'interval_pair'
    target = {'index': index,
              'name': labels[index]['name'],
              'sep': labels[index]['stop'],
              'next_name': labels[index + 1]['name']}
    if new_name is None:
        new_name = target['name'] + target['next_name']
    other_args = {'new_name': new_name,
                  'new_sep': None,
                  'new_next_name': None}
    return _gen_code(op, target_name, target, other_args)

def cg_split(labels, index, new_sep, new_name=None, new_next_name=None):
    op = 'split'
    target_name = 'interval_pair'
    target = {'index': index,
              'name': labels[index]['name'],
              'sep': None,
              'next_name': None}
    if new_name is None:
        new_name = target['name']
    if new_next_name is None:
        new_next_name = ''
    other_args = {'new_name': new_name,
                  'new_sep': new_sep,
                  'new_next_name': new_next_name}
    return _gen_code(op, target_name, target, other_args)

def cg_delete(labels, index):
    op = 'delete'
    target_name = 'interval'
    target = {'index': index}
    target.update(labels[index])
    other_args = {}
    return _gen_code(op, target_name, target, other_args)

def cg_create(labels, index, start, **kwargs):
    op = 'create'
    target_name = 'interval'
    target = {'index': index,
              'start': start}
    target.update(kwargs)
    other_args = {}
    return _gen_code(op, target_name, target, other_args)

# invert operations

INVERSE_TABLE = {'set_name': 'set_name',
                 'set_boundary': 'set_boundary',
                 'merge_next': 'split',
                 'split': 'merge_next',
                 'delete': 'create',
                 'create': 'delete'}

def invert(cmd):
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
    cmd = ''
    cmd += token_list[0]
    for t in token_list[1:]:
        if t != ')' and cmd[-1] != '(':
            cmd += ' '
        cmd += t
    return cmd

def write_to_tokens(ntl):
    token_list = []
    token_list.append('(')
    for t in ntl:
        if isinstance(t, list):
            token_list.extend(write_to_tokens(t))
        else:
            token_list.append(deatomize(t))
    token_list.append(')')
    return token_list

def deatomize(a):
    if a is None:
        return 'null'
    elif isinstance(a, KeyArg):
        if len(a) > 1:
            return '#:' + a[0] + a[1:].replace('_', '-')
        else:
            return '#:' + a
    elif isinstance(a, Symbol):
        if len(a) > 1:
            return a[0] + a[1:].replace('_', '-')
        else:
            return a
    elif isinstance(a, str):
        return '"' + a + '"'
    elif isinstance(a, numbers.Number):
        return str(a)
    else:
        raise ValueError('unknown atomic type: ' + str(a))

# parser & evaluator

class Symbol(str): pass

class KeyArg(Symbol): pass

def tokenize(command):
    first_pass = command.split()
    second_pass = []
    in_string = False
    for token in first_pass:
        num_quotes = token.count('"')
        if num_quotes % 2 != 0 and not in_string:
            # open quote
            second_pass.append(token)
            in_string = True
        elif num_quotes % 2 != 0 and in_string:
            # close quote
            second_pass[-1] += ' ' + token
            in_string = False
        elif num_quotes == 0 and in_string:
            # middle words in quote
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
    if token[0] == '"':
        return token[1:-1].decode('string_escape')
    if token == 'null':
        return None
    try:
        return int(token)
    except ValueError:
        try:
            return float(token)
        except ValueError:
            if len(token) > 1:
                token = token.replace('-', '_')
            if len(token) > 2 and token[:2] == '#:':
                return KeyArg(token[2:])
            return Symbol(token)


def read_from_tokens(token_list):
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


def parse(command):
    return read_from_tokens(tokenize(command))


def lc_env():
    env = {}
    env.update({'set_name': _set_name,
                'set_boundary': _set_bd,
                'merge_next': _merge_next,
                'split': _split,
                'delete': _delete,
                'create': _create,
                'interval': dict,
                'interval_pair': dict})
    return env


def evaluate(expr, env=lc_env()):
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
    return itertools.izip_longest(*args)
