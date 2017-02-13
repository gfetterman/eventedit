import pytest
import copy
import labelcorrection as lc

TEST_COMMAND = '(set-name (interval 3 4.7 5.0 "d" "focus_bird") "b")'
TEST_LABELS = [{'start': 1.0, 'stop': 2.1, 'name': 'a'},
               {'start': 2.1, 'stop': 3.5, 'name': 'b'},
               {'start': 3.5, 'stop': 4.2, 'name': 'c'},
               {'start': 4.7, 'stop': 5.0, 'name': 'd'}]

def test__set_name():
    labels = copy.deepcopy(TEST_LABELS)
    lc._set_name(labels, {'index': 3}, 'b', discard='spam')
    assert labels[3]['name'] == 'b'

def test__set_bd():
    labels = copy.deepcopy(TEST_LABELS)
    with pytest.raises(KeyError):
        lc._set_bd(labels, {'index': 3}, 'foo', 3.4)
    
    lc._set_bd(labels, {'index': 3}, 'start', 4.6, discard='spam')
    assert round(labels[3]['start'], 2) == 4.6

    lc._set_bd(labels, {'index': 3}, 'stop', 6.4)
    assert round(labels[3]['stop'], 2) == 6.4

def test__merge_next():
    labels = copy.deepcopy(TEST_LABELS)
    lc._merge_next(labels, {'index': 1}, discard='spam')
    assert len(labels) == 3
    assert labels[1]['stop'] == 4.2
    assert labels[1]['name'] == 'bc'
    assert labels[2]['name'] == 'd'

def test__split():
    labels = copy.deepcopy(TEST_LABELS)
    with pytest.raises(ValueError):
        lc._split(labels, {'index': 3}, 'd', 1.0, 'e')
    
    lc._split(labels, {'index': 3}, 'd', 4.8, 'e')
    assert len(labels) == 5
    assert labels[3]['stop'] == 4.8
    assert labels[3]['name'] == 'd'
    assert labels[4]['start'] == 4.8
    assert labels[4]['stop'] == 5.0
    assert labels[4]['name'] == 'e'

def test__delete():
    labels = copy.deepcopy(TEST_LABELS)
    lc._delete(labels, {'index': 2})
    assert len(labels) == 3
    assert labels[2]['name'] == 'd'

def test__create():
    labels = copy.deepcopy(TEST_LABELS)
    new_interval = {'index': 2,
                    'start': 3.1,
                    'stop': 3.3,
                    'name': 'c2',
                    'tier': 'female'}
    lc._create(labels, new_interval)
    assert len(labels) == 5
    with pytest.raises(KeyError):
        labels[2]['index']
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
            lc.KeyArg('start'), 1.5,
            lc.KeyArg('stop'), 2.0,
            lc.KeyArg('name'), 'a']
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
    
    cmd = """(set-name #:labels labels
                       #:target (interval #:index 0 #:name "a")
                       #:new-name "b")"""
    lc.evaluate(lc.parse(cmd), test_env)
    assert labels[0]['name'] == 'b'
    
    cmd = """(set-boundary #:labels labels
                           #:target (interval #:index 1 #:bd 3.141)
                           #:which "start"
                           #:new-bd 2.2)"""
    lc.evaluate(lc.parse(cmd), test_env)
    assert labels[1]['start'] == 2.2
    
    cmd = """(merge-next #:labels labels
                         #:target (interval-pair #:index 1
                                                 #:name "b"
                                                 #:sep 3.240
                                                 #:next-name "silence")
                         #:new-name null
                         #:new-sep null
                         #:new-next-name null)"""
    lc.evaluate(lc.parse(cmd), test_env)
    assert len(labels) == len(TEST_LABELS) - 1
    assert labels[1]['stop'] == TEST_LABELS[2]['stop']
    
    cmd = """(split #:labels labels
                    #:target (interval-pair #:index 1
                                            #:name null
                                            #:sep null
                                            #:next-name null)
                    #:new-name "b"
                    #:new-sep 3.5
                    #:new-next-name "c")"""
    lc.evaluate(lc.parse(cmd), test_env)
    assert len(labels) == len(TEST_LABELS)
    assert labels[1]['stop'] == TEST_LABELS[1]['stop']