import copy
import itertools
import numbers

# raw operations
def set_name(labels, target, new_name, **kwargs):
    labels[target['index']]['name'] = new_name

def set_bd(labels, target, which, new_bd, **kwargs):
    if which not in ('start', 'stop'):
        raise KeyError('boundary name not recognized: ' + which)
    labels[target['index']][which] = new_bd

def merge_next(labels, target, **kwargs):
    index = target['index']
    labels[index]['stop'] = labels[index + 1]['stop']
    new_name = labels[index]['name'] + labels[index + 1]['name']
    labels[index]['name'] = new_name
    labels.pop(index + 1)

def split(labels, target, new_name, new_sep, new_next_name, **kwargs):
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

def delete(labels, target, **kwargs):
    labels.pop(target['index'])

def create(labels, target, **kwargs):
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
    ntl = parse(cmd)
    op = ntl[0]
    inverse = INVERSE_TABLE[op]
    target = ntl[ntl.index('target') + 1]
    for i in range(len(ntl)):
        curr = ntl[i]
        if len(curr) >= 4 and curr[:4] == 'new_':
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
        return '#:' + a
    elif isinstance(a, Symbol):
        if len(a) > 1:
            return a[0] + a[1:].replace('_', '-')
        else:
            return a
    elif isinstance(a, str):
        if len(a) > 2 and a[:2] == '#:':
            return a
        else:
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
            temp = []
            while len(token) > 0 and token[-1] == ')':
                token = token[:-1]
                temp.insert(0, ')')
            temp.insert(0, token)
            third_pass.extend(temp)
        else:
            third_pass.append(token)
    return third_pass


def atomize(token):
    if token[0] == '"':
        return token[1:-1].decode('string_escape')
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
    env.update({'null': None,
                'set_name': set_name,
                'set_boundary': set_bd,
                'merge_next': merge_next,
                'split': split,
                'delete': delete,
                'create': create,
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