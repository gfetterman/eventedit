import pytest
import copy
import labelcorrection as lc

TEST_LABELS = [{'start': 1.0, 'stop': 2.1, 'name': 'a'},
               {'start': 2.1, 'stop': 3.0, 'name': 'b'},
               {'start': 3.5, 'stop': 4.2, 'name': 'c'},
               {'start': 4.7, 'stop': 5.0, 'name': 'd'}]

def test_set_name():
    labels = copy.deepcopy(TEST_LABELS)
    lc.set_name(labels, 3, 'b')
    assert labels[3]['name'] == 'b'

def test_move_bd():
    labels = copy.deepcopy(TEST_LABELS)
    with pytest.raises(IndexError):
        lc.move_bd(labels, 3, 'foo', 0.1)
    
    lc.move_bd(labels, 3, 'start', -0.1)
    assert round(labels[3]['start'], 2) == 4.6

    lc.move_bd(labels, 3, 'stop', 1.4)
    assert round(labels[3]['stop'], 2) == 6.4

def test_merge_adjacent():
    labels = copy.deepcopy(TEST_LABELS)
    with pytest.raises(ValueError):
        lc.merge_adjacent(labels, 3, 5)
    
    lc.merge_adjacent(labels, 1, 2)
    assert len(labels) == 3
    assert labels[1]['stop'] == 4.2
    assert labels[1]['name'] == 'b+c'
    assert labels[2]['name'] == 'd'

def test_split():
    labels = copy.deepcopy(TEST_LABELS)
    with pytest.raises(ValueError):
        lc.split(labels, 3, 1.0)
    
    lc.split(labels, 3, 4.8)
    assert len(labels) == 5
    assert labels[3]['stop'] == 4.8
    assert labels[3]['name'] == 'd'
    assert labels[4]['start'] == 4.8
    assert labels[4]['stop'] == 5.0
    assert labels[4]['name'] == ''

def test_delete():
    labels = copy.deepcopy(TEST_LABELS)
    lc.delete(labels, 2)
    assert len(labels) == 3
    assert labels[2]['name'] == 'd'

def test_create():
    labels = copy.deepcopy(TEST_LABELS)
    lc.create(labels, 2, 3.1, 3.3, 'c2', tier='female')
    assert len(labels) == 5
    assert labels[2]['start'] == 3.1
    assert labels[2]['stop'] == 3.3
    assert labels[2]['name'] == 'c2'
    assert labels[2]['tier'] == 'female'
    assert labels[3]['name'] == 'c'
