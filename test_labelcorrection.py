import pytest
import copy
import labelcorrection as lc

TEST_COMMAND = '(set-name (interval 3 4.7 5.0 "d" "focus_bird") "b")'
TEST_LABELS = [{'start': 1.0, 'stop': 2.1, 'name': 'a'},
               {'start': 2.1, 'stop': 3.5, 'name': 'b'},
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

def test_tokenize():
    tkns = lc.tokenize(TEST_COMMAND)
    assert len(tkns) == 12
    assert tkns[0] == '('
    assert tkns[5] == '4.7'
    assert tkns[8] == '"focus_bird"'
    assert tkns[11] == ')'
    
    tkns = lc.tokenize('string "spaces preserved"')
    assert len(tkns) == 2
    assert tkns[0] == 'string'
    assert tkns[1] == '"spaces preserved"'

def test_atomize():
    assert lc.atomize('1') == 1
    assert lc.atomize('1.5') == 1.5
    assert lc.atomize('(') == '('
    assert lc.atomize('"focus_bird"') == 'focus_bird'
    assert isinstance(lc.atomize('set-name'), lc.Symbol)
    assert lc.atomize('set-name') == 'set_name'

def test_parse_and_read_from_tokens():
    with pytest.raises(SyntaxError):
        lc.read_from_tokens([])
    
    with pytest.raises(SyntaxError):
        lc.read_from_tokens([')'])
    
    nested_list = lc.parse(TEST_COMMAND)
    assert len(nested_list) == 3
    assert len(nested_list[1]) == 6
    assert nested_list[0] == 'set_name'
    assert nested_list[1][0] == 'interval'
    assert nested_list[1][5] == 'focus_bird'

def test_evaluate():
    def complex_proc(**kwargs):
        for a in kwargs:
            if isinstance(kwargs[a], float):
                kwargs[a] += 1.0
        return kwargs
    test_env = {'symbol': 'answer',
                'simple_proc': dict,
                'complex_proc': complex_proc}
    
    assert lc.evaluate(lc.Symbol('symbol'), test_env) == 'answer'
    
    assert lc.evaluate(1.5, test_env) == 1.5
    
    expr = [lc.Symbol('simple_proc'),
            '#:start', 1.5, '#:stop', 2.0, '#:name', 'a']
    result = lc.evaluate(expr, test_env)
    assert isinstance(result, dict)
    assert result['start'] == 1.5
    assert result['stop'] == 2.0
    assert result['name'] == 'a'
    
    expr[0] = lc.Symbol('complex_proc')
    result = lc.evaluate(expr, test_env)
    assert isinstance(result, dict)
    assert result['start'] == 2.5
    assert result['stop'] == 3.0
    assert result['name'] == 'a'

def test_whole_stack():
    labels = copy.deepcopy(TEST_LABELS)
    test_env = lc.lc_env()
    test_env.update({'labels': labels})
    
    cmd = '(set-name #:labels labels #:index 0 #:new-name "b")'
    lc.evaluate(lc.parse(cmd), test_env)
    assert labels[0]['name'] == 'b'
    
    cmd = '(move-boundary #:labels labels #:index 1 #:which "start" #:delta -0.1)'
    lc.evaluate(lc.parse(cmd), test_env)
    assert labels[1]['start'] == TEST_LABELS[1]['start'] - 0.1
    
    cmd = '(merge #:labels labels #:index1 1 #:index2 2)'
    lc.evaluate(lc.parse(cmd), test_env)
    assert len(labels) == len(TEST_LABELS) - 1
    assert labels[1]['stop'] == TEST_LABELS[2]['stop']
    
    cmd = '(split #:labels labels #:index 1 #:split-pt 3.5)'
    lc.evaluate(lc.parse(cmd), test_env)
    assert len(labels) == len(TEST_LABELS)
    assert labels[1]['stop'] == TEST_LABELS[1]['stop']