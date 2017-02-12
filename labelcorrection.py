import copy
import itertools

# raw operations
def set_name(labels, index, new_name):
    labels[index]['name'] = new_name

def move_bd(labels, index, which, delta):
    if which not in ('start', 'stop'):
        raise IndexError('boundary name not recognized: ' + which)
    labels[index][which] += delta

def merge_adjacent(labels, index1, index2):
    if index2 != index1 + 1:
        raise ValueError('can only merge index-adjacent intervals')
    labels[index1]['stop'] = labels[index2]['stop']
    new_name = labels[index1]['name'] + '+' + labels[index2]['name']
    labels[index1]['name'] = new_name
    labels.pop(index2)

def split(labels, index, split_pt):
    if not (split_pt > labels[index]['start'] and
            split_pt < labels[index]['stop']):
        raise ValueError('split point must be within interval')
    new_point = copy.deepcopy(labels[index])
    new_point['start'] = split_pt
    new_point['name'] = ''
    labels[index]['stop'] = split_pt
    labels.insert(index + 1, new_point)

def delete(labels, index):
    labels.pop(index)

def create(labels, index, start, stop, name, **kwargs):
    new_point = {'start': start,
                 'stop': stop,
                 'name': name}
    new_point.update(kwargs)
    labels.insert(index, new_point)

# parsing stuff
class Symbol(str): pass


def lc_env():
    env = {}
    env.update({'set_name': set_name,
                'move_boundary': move_bd,
                'merge': merge,
                'split': split,
                'delete': delete,
                'create': create,
                'interval': dict,
                'new_val': dict})
    return env


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
            if len(token) > 1:
                third_pass.append(token[:-1])
            third_pass.append(')')
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
            return Symbol(token.replace('-', '_'))


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


def evaluate(expr, env=lc_env):
    if isinstance(expr, Symbol):
        return env[expr]
    elif not isinstance(expr, list):
        return expr
    else:
        proc = evaluate(expr[0], env)
        kwargs = {p[0][2:]: evaluate(p[1], env) for p in _grouper(expr[1:], 2)}
        return proc(**kwargs)


def _grouper(iterable, n):
    """Returns nonoverlapping windows of input of length n."""
    args = [iter(iterable)] * n
    return itertools.izip_longest(*args)