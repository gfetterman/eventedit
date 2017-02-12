import copy

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
