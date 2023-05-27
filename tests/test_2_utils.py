from typing import Mapping, Iterable
from itertools import product
from functools import partial

from configlayer.types import ItemError
from configlayer.exceptions import InputError, InitError, CheckValueError, CheckTypeError
from configlayer.utils import (
    is_dunder, is_internal, is_hidden, is_exception, is_holder,                     # Bool checks
    as_holder, as_holder_stated, as_dict, as_dict_stated,                           # Type casting
    safe, with_type,                                                                # Common
    fmt_dict, fmt_obj_errors, fmt_name, fmt_exc,                                    # Formatters
    split,                                                                          # Split
    join, sentence, sentences,                                                      # Joins
    check_input, check_lengths, check_absent, check_extra, check_items, check_type, check_types,   # Data checks
    decorate_methods, init_reraise, set_slots_defaults,                             # Decorators
    get_cls_obj, get_cls_attr, get_attrs, GetName,                                  # Getters
    UID, Locker)                                                                    # Uncategorized

from _utilities import raises, subtest
from _data import empty_func, increment_str, wrong_func, wrong_func_3, WrongCast


# Bool checks


def test_is_dunder():
    variants = ('', '_', '__', '___')
    data = [f'{start}name{end}' for start in variants for end in variants]
    data.remove('__name__')
    assert is_dunder('__name__')
    assert not any(map(is_dunder, data))


def test_is_internal():
    variants = ('_', '__', '___')
    data = [f'{start}name{end}' for start in variants for end in variants]
    data.remove('__name__')
    assert all(map(is_internal, data))
    assert not is_internal('name')
    assert not is_internal('name_')
    assert not is_internal('name__')
    assert not is_internal('name___')
    assert not is_internal('__name__')


def test_is_hidden():
    variants = ('_', '__', '___')
    data = [f'{start}name{end}' for start in variants for end in variants]
    assert all(map(is_hidden, data))
    assert not is_hidden('name')
    assert not is_hidden('name_')
    assert not is_hidden('name__')
    assert not is_hidden('name___')
    assert is_hidden('__name__')


def test_is_exception():
    assert is_exception(Exception)
    assert is_exception(Exception(''))
    assert is_exception(ValueError)
    assert is_exception(ValueError(''))
    assert not is_exception(Exception, ValueError)
    assert not is_exception(Exception(''), ValueError)
    assert not is_exception(None)
    assert not is_exception(None, ValueError)


def test_is_holder():
    holder_types = tuple, list, set, dict
    not_holder_types = bool, int, float, str, bytes, bytearray

    assert is_holder(None) is None
    assert all(is_holder(x()) for x in holder_types) is True
    assert any(is_holder(x()) for x in not_holder_types) is False
    assert not any(is_holder(x(), holder_types) for x in holder_types)

    exc = partial(InputError, 'exclude', must_be='type or types', func_name='is_holder()')
    raises(exc(received='5 (int)'), is_holder, 5, 5)
    raises(exc(received='5 (int) at pos 0'), is_holder, 5, (5, int))
    raises(exc(received="'some'='string' (str)"), is_holder, 5, {'some': 'string', 'another': str})


# Type casting


def test_as_holder():
    assert as_holder(None, default=None) is None
    assert as_holder(None, None) is None
    assert as_holder(None, [1]) == [1]
    assert as_holder(None) == ()
    assert as_holder('1') == ('1',)
    assert as_holder([]) == []
    assert as_holder([1]) == [1]
    assert as_holder(['1']) == ['1']
    assert as_holder(['1'], exclude=(list,)) == (['1'],)

    raises(InputError('exclude', func_name='is_holder()', must_be='type or types',
                      received="'1' (str) at pos 1"),
           as_holder, ['1'], exclude=(list, '1'))

    raises(InputError('exclude', func_name='is_holder()', must_be='type or types',
                      received="'1' (str) at pos 1, 2.13 (float) at pos 2"),
           as_holder, ['1'], exclude=(list, '1', 2.13))


def test_as_holder_stated():
    assert as_holder_stated(None, default=None) == (None, None)
    assert as_holder_stated(None, None) == (None, None)
    assert as_holder_stated(None, [1]) == (None, [1])
    assert as_holder_stated(None) == (None, ())
    assert as_holder_stated('1') == (False, ('1',))
    assert as_holder_stated([]) == (True, [])
    assert as_holder_stated([1]) == (True, [1])
    assert as_holder_stated(['1']) == (True, ['1'])
    assert as_holder_stated(['1'], exclude=(list,)) == (False, (['1'],))

    raises(InputError('exclude', func_name='is_holder()', must_be='type or types',
                      received="'1' (str) at pos 1"),
           as_holder_stated, ['1'], exclude=(list, '1'))

    raises(InputError('exclude', func_name='is_holder()', must_be='type or types',
                      received="'1' (str) at pos 1, 2.13 (float) at pos 2"),
           as_holder_stated, ['1'], exclude=(list, '1', 2.13))


def test_as_mapping():
    def modify(x):
        return ((str(v), v) for v in x)

    raises(TypeError("'int' object is not iterable"), as_dict, 5)
    t1 = (0, '1')
    t2 = ('0', '1')
    t3 = ('0',)
    t4 = ('0', 1, 2)
    d1 = {0: 0, 1: '1'}
    d2 = {'0': 0, '1': '1'}
    d3 = {'0': 0}
    d4 = {'0': 0, 1: '1'}

    # input mapping
    assert as_dict(d1) == d1                             # -> input
    assert as_dict(d1, modify) == d1                     # -> input
    assert as_dict(d1, t2) == d1                         # -> input
    assert as_dict(d1, t3) == d1                         # -> input
    assert as_dict(d1, t4) == d1                         # -> input
    assert as_dict(d1, t2, strict=True) == d1            # -> input
    assert as_dict(d1, t3, strict=True) == d1            # -> input
    assert as_dict(d1, t4, strict=True) == d1            # -> input

    # input not mapping iterable
    assert as_dict(t1) == d1                             # -> default func
    assert as_dict(t1, modify) == d2                     # -> modify func
    assert as_dict(t1, t2) == d2                         # -> iterable
    assert as_dict(t1, t3) == d3                         # -> iterable less
    assert as_dict(t1, t4) == d4                         # -> iterable more
    assert as_dict(t1, t2, strict=True) == d2            # -> iterable strict
    raises(ValueError, as_dict, t1, t3, strict=True)     # -> iterable strict less error
    raises(ValueError, as_dict, t1, t4, strict=True)     # -> iterable strict more error


def test_as_mapping_stated():
    def modify(x):
        return ((str(v), v) for v in x)

    raises(TypeError("'int' object is not iterable"), as_dict, 5)
    t1 = (0, '1')
    t2 = ('0', '1')
    t3 = ('0',)
    t4 = ('0', 1, 2)
    d1 = {0: 0, 1: '1'}
    d2 = {'0': 0, '1': '1'}
    d3 = {'0': 0}
    d4 = {'0': 0, 1: '1'}

    # input mapping
    assert as_dict_stated(d1) == (True, d1)                      # -> input state
    assert as_dict_stated(d1, modify) == (True, d1)              # -> input state
    assert as_dict_stated(d1, t2) == (True, d1)                  # -> input state
    assert as_dict_stated(d1, t3) == (True, d1)                  # -> input state
    assert as_dict_stated(d1, t4) == (True, d1)                  # -> input state
    assert as_dict_stated(d1, t2, strict=True) == (True, d1)     # -> input state
    assert as_dict_stated(d1, t3, strict=True) == (True, d1)     # -> input state
    assert as_dict_stated(d1, t4, strict=True) == (True, d1)     # -> input state

    # input not mapping iterable
    assert as_dict_stated(t1) == (False, d1)                     # -> default func state
    assert as_dict_stated(t1, modify) == (False, d2)             # -> modify func
    assert as_dict_stated(t1, t2) == (False, d2)                 # -> iterable
    assert as_dict_stated(t1, t3) == (False, d3)                 # -> iterable less
    assert as_dict_stated(t1, t4) == (False, d4)                 # -> iterable more
    assert as_dict_stated(t1, t2, strict=True) == (False, d2)    # -> iterable strict
    raises(ValueError, as_dict_stated, t1, t3, strict=True)      # -> iterable strict less error
    raises(ValueError, as_dict_stated, t1, t4, strict=True)      # -> iterable strict more error


# Common


def test_safe():
    assert safe(increment_str, '5') == 6
    assert safe(wrong_func_3, 'x', y=5).args == ("Cannot change value ('x',), {'y': 5}", )
    assert safe(increment_str, '5', _res_=increment_str) == 7
    assert safe(increment_str, '5', _res_=55) == 55
    assert safe(wrong_func, 'x').args == ('Wrong func!', )
    assert safe(wrong_func, 'x', _exc_=repr) == "TypeError('Wrong func!')"
    assert safe(wrong_func, 'x', _exc_=55) == 55


def test_with_type():
    assert with_type(type) == "type (type)"
    assert with_type(5) == "5 (int)"
    assert with_type('any') == "'any' (str)"

    assert with_type(type, key1='some') == "type (type=type, key1='some')"
    assert with_type(5, key1='some', type=0.1) == "5 (key1='some', type=int)"
    assert with_type('any', k=0, k3=False, k2=True) == "'any' (type=str, k=0, k3=False, k2=True)"


# Formatters


def test_fmt_dict():
    obj = {0: 0, 1: '1', '2': 2, 'item': 'value'}
    fmts = (str, repr)
    seps = ('=', ': ')
    for i, kf, sep, vf in (st := subtest('', 8, product(fmts, seps, fmts))):
        st.send(('', fmt_dict(obj, kf, sep, vf),
                 tuple(f'{kf(k)}{sep}{vf(v)}' for k, v in obj.items())))


def test_fmt_obj_errors():
    obj = object()
    errors = [(ItemError('1', 1, ''),), (ItemError('1', 1, ''), ItemError(2, '2', '2'))]
    rns = ({}, {'result_name': 'some name'})
    khs = ({}, {'key_handler': str})
    seps = ({}, {'kv_sep': ': '})
    bools = [False, True]

    # Check all Extra - 192 cases
    cases = product([obj], [(), *errors], [False], bools, bools, bools, rns, khs, seps)
    for i, o, *args, rn, kh, sep in (st := subtest('All Extra', 192, cases)):
        st.send(('', fmt_obj_errors(o, *args, **rn, **kh, **sep), (with_type(o),)))

    # Check all no errors - 128 cases
    cases = product([obj], [()], bools, bools, bools, bools, rns, khs, seps)
    for i, o, *args, rn, kh, sep in (st := subtest('All no errors', 128, cases)):
        st.send(('', fmt_obj_errors(o, *args, **rn, **kh, **sep), (with_type(o),)))

    # Check all not holders - 64 cases
    cases = product([obj], errors, [True], [False], bools, bools, rns, khs, seps)
    for i, o, e, *args, r, rn, kh, sep in (st := subtest('All not holders', 64, cases)):
        res = with_type(e[0].value, **{rn.get('result_name', 'result'): e[0].result} if r else {})
        st.send(('', fmt_obj_errors(o, e, *args, r, **rn, **kh, **sep), (res,)))

    # Check all mappings - 32 cases
    cases = product([obj], errors, [True], [True], [True], bools, rns, khs, seps)
    for i, o, e, *args, r, rn, kh, sep in (st := subtest('All mappings', 32, cases)):
        h = kh.get('key_handler', repr)
        s = sep.get('kv_sep', '=')
        res = (f"{h(k)}{s}{with_type(v, **{rn.get('result_name', 'result'): info} if r else {})}"
               for k, v, info in e)
        st.send(('', fmt_obj_errors(o, e, *args, r, **rn, **kh, **sep), tuple(res)))

    # Check all left (not mapping holder that has errors and exists) - 32 cases
    cases = product([obj], errors, [True], [True], [False], bools, rns, khs, seps)
    for i, o, e, *args, r, rn, kh, sep in (st := subtest('All left', 32, cases)):
        res = tuple(f"{with_type(v)} at pos {i}" + (f' ({info})' if r else '') for i, v, info in e)
        st.send(('', fmt_obj_errors(o, e, *args, r, **rn, **kh, **sep), res))


def test_fmt_name():
    for results, kwargs in [
        ('items item items',        {}),
        ('params param params',     {'item_name': 'param'}),
        ('param item items',        {'default': 'param'}),
        ('param(s) param params',   {'item_name': 'param', 'default': 'param(s)'})
    ]:
        for obj, result in zip([(), ['a'], {'b': '1', 'c': 0}], results.split(), strict=True):
            assert fmt_name(obj, **kwargs) == result


def test_fmt_exc():
    msg_set = ('', 'some message')
    exc_set = (Exception, TypeError)
    args_set = ((), (0,), (1, 2))
    kwargs_set = ({}, {'str': 'here'}, {'sentences': ('msg1', 'msg2'), 'dict': {'k1': 1, 'k2': 2}})

    def_set = (msg_set, exc_set, args_set, kwargs_set)

    name_set = ('', 'name')
    n_args_set = ((), ('arg',), ('arg1', 'arg2'))
    in_kw_set = ((), *((x,) for x in kwargs_set))
    input_exc_set = [(n, *a, *k) for n, a, k in product(name_set, n_args_set, in_kw_set)]

    # Check default error exception, fixed empty input_exc param
    st = subtest('Default exception', 36, product(*def_set))
    for i, msg, exc, args, kwargs in st:
        recv_exc = fmt_exc((), msg, exc, *args, **kwargs)

        exc_msg = InputError(msg=msg, **kwargs).args[0] if kwargs else msg
        wait_exc = exc(exc_msg, *args) if exc_msg else exc(*args)

        st.send(('', type(recv_exc), exc))
        r_msg, *r_left = recv_exc.args or ('',)
        w_msg, *w_left = wait_exc.args or ('',)
        st.send(('Message or arg - args[0]', r_msg, w_msg))
        st.send(('', r_left, w_left))

    # Check input error exception
    st = subtest('Input exception', 864, product(input_exc_set, *def_set),
                 {'Message - args[0]': 144})
    for i, input_exc, msg, exc, args, kwargs in st:
        recv_exc = fmt_exc(input_exc, msg, exc, *args, **kwargs)

        name, *params, in_kw = (input_exc if isinstance(input_exc[-1], dict) else (*input_exc, {}))
        in_kw |= {k: v for k, v in kwargs.items() if k not in in_kw}
        wait_exc = InputError(*params, msg=msg, func_name=name, args=args, **in_kw)

        st.send(('', type(recv_exc), InputError))
        r_msg, *r_left = recv_exc.args
        w_msg, *w_left = wait_exc.args
        st.send(('Message - args[0]', r_msg, w_msg))
        st.send(('', r_left, w_left))


# Split


def test_split():
    e_value = ValueError('3')
    data_dict = {'0': 0, '1': 1, 'E': e_value, 'T': (1, 2), 'L': [1, -1], 'F': False, 'N': None}
    data_list = list(data_dict.values())

    # support funcs
    def to_tuples(values: Iterable[dict]):
        return tuple(tuple(x.values()) for x in values)

    # funcs for test
    def change(x, val=1):
        return (not x) if isinstance(x, bool) else (x + val) if isinstance(x, int) else x

    def is_int_key(k, _):
        return isinstance(k, int)

    # data values (f - fixed, s - standard, m - modified)
    fe, fn = {'E': e_value}, {'N': None}
    s0, s1, st, sl, sf = {'0': 0}, {'1': 1}, {'T': (1, 2)}, {'L': [1, -1]}, {'F': False}
    m0, m1, mt, ml, mf = {'0': 1}, {'1': 2}, {'T': 3}, {'L': 0}, {'F': True}

    # possible bool condition results
    b_______ = s1 | fe | st | sl, s0 | sf | fn
    b____s__ = s1 | st | sl, s0 | fe | sf | fn

    b_c_____ = s0 | s1 | fe | st | sl | sf, fn
    b_c___m_ = m0 | m1 | fe | st | sl | mf, fn
    b_c__s__ = s0 | s1 | st | sl | sf, fe | fn
    b_c__sm_ = m0 | m1 | st | sl | mf, fe | fn
    b_c_u___ = s0 | s1 | fe | st | sf, sl | fn
    b_c_u_m_ = m0 | m1 | fe | mt | mf, ml | fn
    b_c_us__ = s0 | s1 | st | sf, fe | sl | fn
    b_c_usm_ = m0 | m1 | mt | mf, fe | ml | fn

    b______i = b_______[::-1]

    b_c____i = b_c_____[::-1]
    b_c___mi = b_c___m_[::-1]
    b_c_u__i = b_c_u___[::-1]
    b_c_u_mi = b_c_u_m_[::-1]

    # possible is_exception condition results
    i_______ = fe, s0 | s1 | st | sl | sf | fn
    i____s__ = {}, data_dict

    i_c___m_ = fe, m0 | m1 | st | sl | mf | fn
    i_c__sm_ = {}, m0 | m1 | fe | st | sl | mf | fn
    i_c_u_m_ = fe, m0 | m1 | mt | ml | mf | fn
    i_c_usm_ = {}, m0 | m1 | fe | mt | ml | mf | fn

    i______i = i_______[::-1]
    i_c___mi = i_c___m_[::-1]
    i_c_u_mi = i_c_u_m_[::-1]

    # defaults test
    assert split(data_dict) == b_______
    assert split(data_list) == to_tuples(b_______)

    # general params tests
    conditions = (bool, is_exception)
    funcs = (None, change)
    bool_keys = ('unpack', 'safely', 'modify', 'cond_invert')[::-1]
    bool_kwargs = [dict(zip(bool_keys, x)) for x in product((False, True), repeat=len(bool_keys))]
    for i, (args, results) in enumerate(zip(product(conditions, funcs), [
        (b_______, b_______, b____s__, b____s__, b_______, b_______, b____s__, b____s__,
         b______i, b______i, b______i, b______i, b______i, b______i, b______i, b______i),
        (b_c_____, b_c_u___, b_c__s__, b_c_us__, b_c___m_, b_c_u_m_, b_c__sm_, b_c_usm_,
         b_c____i, b_c_u__i, b_c____i, b_c_u__i, b_c___mi, b_c_u_mi, b_c___mi, b_c_u_mi),
        (i_______, i_______, i____s__, i____s__, i_______, i_______, i____s__, i____s__,
         i______i, i______i, i______i, i______i, i______i, i______i, i______i, i______i),
        (i_______, i_______, i____s__, i____s__, i_c___m_, i_c_u_m_, i_c__sm_, i_c_usm_,
         i______i, i______i, i______i, i______i, i_c___mi, i_c_u_mi, i_c___mi, i_c_u_mi)
    ], strict=True)):
        for j, (kwargs, expected) in enumerate(zip(bool_kwargs, results, strict=True)):
            try:
                assert split(data_dict, *args, **kwargs) == expected
                assert split(data_list, *args, **kwargs) == to_tuples(expected)
                vs, ws = split(data_list, *args, as_dicts=True, **kwargs)
                ve, we = expected
                assert all(isinstance(x, int) for x in tuple(vs.keys()) + tuple(ws.keys()))
                assert tuple(vs.values()) == tuple(ve.values())
                assert tuple(ws.values()) == tuple(we.values())
            except Exception:
                raise Exception(f"{i=} ({args = }), {j=} ({kwargs = })")

    # cond_key and cond_value params test
    e_kv____ = InputError('cond_key', 'cond_value', must_be='at least one True or not filled',
                          func_name='split()', received='cond_key = False, cond_value = False')
    b__vl___ = to_tuples(b_______)
    b_k_d___ = (data_dict, {})
    b_k_l___ = to_tuples((s1 | fe | st | sl | sf | fn, s0))
    for (key, value), expected in zip(product((None, False, True), repeat=2), (
        (b_______, b__vl___),                         # None  None  -> False, True
        (b_k_d___, b_k_l___),                         # None  False -> True, False
        (b_______, b__vl___),                         # None  True  -> False, True
        (b_______, b__vl___),                         # False None  -> False, True
        e_kv____,                                     # False False -> False, False (error)
        (b_______, b__vl___),                         # False True  -> False, True
        (b_k_d___, b_k_l___),                         # True  None  -> True, False
        (b_k_d___, b_k_l___),                         # True  False -> True, False
        (({}, data_dict), (tuple(data_list), ()))     # True  True  -> True,  True  (both)
    ), strict=True):
        if is_exception(expected):
            raises(expected, split, data_dict, cond_key=key, cond_value=value)
            raises(expected, split, data_list, cond_key=key, cond_value=value)
        else:
            args = (is_int_key,) if key == value and key is True else ()
            assert split(data_dict, *args, cond_key=key, cond_value=value) == expected[0]
            assert split(data_list, *args, cond_key=key, cond_value=value) == expected[1]


# Joins

join_dataset = [(0, '', 1, False),
                (0, 'here is a sTrAnGe STRING', 1, False),
                ('here is', 0, 'a sTrAnGe STRING', 1, False),
                (None, 'here is', 0, 'a', False, 'sTrAnGe STRING', 1)]


def _join_tests(func, results_set, sep=', '):
    for typecast in True, False:
        for skip_false, results in zip((True, False), results_set, strict=True):
            kwargs = {'sep': sep, 'typecast': typecast, 'skip_false': skip_false}
            for args, result in zip(join_dataset, results, strict=True):
                if typecast:
                    assert func(*args, **kwargs) == sep.join(result)
                else:
                    raises(TypeError, func, *args, **kwargs)


def test_join():
    results = ([('1',),
                ('here is a sTrAnGe STRING', '1'),
                ('here is', 'a sTrAnGe STRING', '1'),
                ('here is', 'a', 'sTrAnGe STRING', '1')],
               [('0', '', '1', 'False'),
                ('0', 'here is a sTrAnGe STRING', '1', 'False'),
                ('here is', '0', 'a sTrAnGe STRING', '1', 'False'),
                ('None', 'here is', '0', 'a', 'False', 'sTrAnGe STRING', '1')])
    _join_tests(join, results)


def test_sentence():
    results = ([('1',),
                ('Here is a sTrAnGe STRING', '1'),
                ('Here is', 'a sTrAnGe STRING', '1'),
                ('Here is', 'a', 'sTrAnGe STRING', '1')],
               [('0', '', '1', 'False'),
                ('0', 'here is a sTrAnGe STRING', '1', 'False'),
                ('Here is', '0', 'a sTrAnGe STRING', '1', 'False'),
                ('None', 'here is', '0', 'a', 'False', 'sTrAnGe STRING', '1')])
    _join_tests(sentence, results, ' ')


def test_sentences():
    results = ([('1',),
                ('Here is a sTrAnGe STRING', '1'),
                ('Here is', 'A sTrAnGe STRING', '1'),
                ('Here is', 'A', 'STrAnGe STRING', '1')],
               [('0', '', '1', 'False'),
                ('0', 'Here is a sTrAnGe STRING', '1', 'False'),
                ('Here is', '0', 'A sTrAnGe STRING', '1', 'False'),
                ('None', 'Here is', '0', 'A', 'False', 'STrAnGe STRING', '1')])
    _join_tests(sentences, results, '. ')


# Data checks


def test_check_input():
    exc = CheckValueError
    raises(exc("Item is needed, but not provided"), check_input, None, 1)
    raises(exc("Item is not needed, but provided"), check_input, 1, None)
    raises(exc("Some is needed, but not provided"), check_input, None, 1, 'Some')
    raises(exc("Some is not needed, but provided"), check_input, 1, None, 'Some')
    raises(exc("Is not needed, but provided"), check_input, 1, None, '')
    raises(exc("- not"), check_input, 1, None, template='{2}-{1}')
    assert check_input(None, None) is False
    assert check_input(False, False) is True

    exc1 = InputError('name1', msg="Some is not needed, but provided")
    exc2 = InputError(msg="Some is not needed, but provided", func_name='str()')
    raises(exc1, check_input, 1, None, 'Some', input_exc=('', 'name1'))
    raises(exc2, check_input, 1, None, 'Some', input_exc=('str()',))
    assert check_input(1, 1, 'Some', input_exc=('str()',))


def test_check_extra():
    exc = CheckValueError
    vals = (1, '2', 3), [1]
    add = ". Must be not more than expected (1), but received: 1, '2', 3"
    raises(exc("Extra item: 2. Must be not more than expected (1), but received: 1, 2"),
           check_extra, (1, 2), [1])
    raises(exc("Extra items: '2', 3" + add), check_extra, *vals)
    raises(exc("Extra vals: '2', 3" + add), check_extra, *vals, 'val')
    raises(exc("E\n\t'2'\n\t3" + add), check_extra, *vals, template='E\n\t', item_sep='\n\t')
    raises(exc("E items: '2' 3" + add), check_extra, *vals, template='E {}: ', item_sep=' ')
    raises(exc("E items('2',3)" + add), check_extra, *vals, template='E {}({})', item_sep=',')
    raises(exc("E xs('2',3)" + add), check_extra, *vals, 'x', template='E {}({})', item_sep=',')
    raises(exc("E x('2',3)" + add), check_extra, *vals, '', template='E x{}({})', item_sep=',')

    raises(InputError('template', must_be='not more than 2 data places', received="'{}{}{}'",
                      func_name='check_extra()'),
           check_extra, *vals, template='{}{}{}')     # with error
    assert check_extra([1], (1, 2), template='{}{}{}')  # without error, but more pythonic

    assert check_extra(*vals, as_text=True) == "Extra items: '2', 3" + add
    assert check_extra((1, 2), (1, 2), as_text=True) == ""
    assert check_extra((1, 2), (1, 2)) == (1, 2)

    exc_inp = InputError('name1', msg="Extra items: '2', 3" + add)
    raises(exc_inp, check_extra, *vals, input_exc=('', 'name1'))
    assert check_extra(*vals, input_exc=('', 'name1'), as_text=True) == str(exc_inp)

    msg = "Extra strs: 2, 3. Must be not more than expected (1), but received: 1, 2, 3"
    raises(exc(msg), check_extra, *vals, 'str', str)
    raises(exc(msg + ". Some x"), check_extra, *vals, 'str', str, some='x')


def test_check_absent():
    exc = CheckValueError
    vals = [1], (1, '2', 3)
    add = ". Must be not less than expected (1, '2', 3), but received: 1"
    raises(exc("Absent item: 2. Must be not less than expected (1, 2), but received: 1"),
           check_absent, [1], (1, 2))
    raises(exc("Absent items: '2', 3" + add), check_absent, *vals)
    raises(exc("Absent vals: '2', 3" + add), check_absent, *vals, 'val')
    raises(exc("A\n\t'2'\n\t3" + add), check_absent, *vals, template='A\n\t', item_sep='\n\t')
    raises(exc("A items: '2' 3" + add), check_absent, *vals, template='A {}: ', item_sep=' ')
    raises(exc("A items('2',3)" + add), check_absent, *vals, template='A {}({})', item_sep=',')
    raises(exc("A xs('2',3)" + add), check_absent, *vals, 'x', template='A {}({})', item_sep=',')
    raises(exc("A x('2',3)" + add), check_absent, *vals, '', template='A x{}({})', item_sep=',')

    raises(InputError('template', must_be='not more than 2 data places', received="'{}{}{}'",
                      func_name='check_absent()'),
           check_absent, *vals, template='{}{}{}')        # with error
    assert check_absent((1, 2), [1], template='{}{}{}')     # without error, but more pythonic

    assert check_absent(*vals, as_text=True) == "Absent items: '2', 3" + add
    assert check_absent((1, 2), [1], as_text=True) == ""
    assert check_absent((1, 2), [1]) == (1, 2)

    exc_inp = InputError('name1', msg="Absent items: '2', 3" + add)
    raises(exc_inp, check_absent, *vals, input_exc=('', 'name1'))
    assert check_absent(*vals, input_exc=('', 'name1'), as_text=True) == str(exc_inp)

    msg = "Absent strs: 2, 3. Must be not less than expected (1, 2, 3), but received: 1"
    raises(exc(msg), check_absent, *vals, 'str', str)
    raises(exc(msg + ". Some x"), check_absent, *vals, 'str', str, some='x')


def test_check_items():
    exc = CheckValueError
    add1 = ". Must be equal to expected (1), but received: 1, '2', 3"
    raises(exc("Extra item: 2. Must be equal to expected (1), but received: 1, 2"),
           check_items, (1, 2), [1])
    raises(exc("Extra items: '2', 3" + add1), check_items, (1, '2', 3), [1])
    raises(exc("Extra vals: '2', 3" + add1), check_items, (1, '2', 3), [1], 'val')

    add2 = ". Must be equal to expected (1, '2', 3), but received: 1"
    raises(exc("Absent item: 2. Must be equal to expected (1, 2), but received: 1"),
           check_items, [1], (1, 2))
    raises(exc("Absent items: '2', 3" + add2), check_items, [1], (1, '2', 3))
    raises(exc("Absent vals: '2', 3" + add2), check_items, [1], (1, '2', 3), 'val')

    msg = "Extra item: 2. Absent item: 3"
    raises(exc(msg + ". Must be equal to expected (3), but received: 2"), check_items, [2], [3])
    raises(exc(msg + ". Must be equal to expected (1, 3), but received: 1, 2"),
           check_items, (1, 2), (1, 3))

    eav = (1, '2', 4), (1, '3', 5)
    add3 = ". Must be equal to expected (1, '3', 5), but received: 1, '2', 4"
    add4 = ". Must be equal to expected (1, 3, 5), but received: 1, 2, 4"
    msg = "Extra items: '2', 4. Absent items: '3', 5"
    msg2 = ("Extra items: 2, 4. Absent items: 3, 5. "
            "Must be equal to expected (3, 5), but received: 2, 4")
    raises(exc(msg2), check_items, (2, 4), (3, 5))
    raises(exc(msg + add3), check_items, *eav)

    raises(exc("Extra vals: '2', 4. Absent vals: '3', 5" + add3), check_items, *eav, 'val')

    raises(exc("Extra strs: 2, 4. Absent strs: 3, 5" + add4), check_items, *eav, 'str', str)
    raises(exc("Extra strs: 2, 4. Absent strs: 3, 5" + add4 + ". Some x"),
           check_items, *eav, 'str', str, some='x')

    raises(exc("E:\n\t'2'\n\t4\nA:\n\t'3'\n\t5" + add3), check_items, *eav,
           extra_template='E:\n\t', absent_template='A:\n\t', check_sep='\n', item_sep='\n\t')
    raises(exc("E items: '2' 4 | A items: '3' 5" + add3), check_items, *eav,
           extra_template='E {}: ', absent_template='A {}: ', check_sep=' | ', item_sep=' ')
    raises(exc("E items('2',4) | A items('3',5)" + add3), check_items, *eav,
           extra_template='E {}({})', absent_template='A {}({})', check_sep=' | ', item_sep=',')
    raises(exc("E coords('2',4) | A coords('3',5)" + add3), check_items, *eav, 'coord',
           extra_template='E {}({})', absent_template='A {}({})', check_sep=' | ', item_sep=',')
    raises(exc("E coord('2',4) | A coord('3',5)" + add3), check_items, *eav, '',
           extra_template='E coord{}({})', absent_template='A {}coord({})', check_sep=' | ',
           item_sep=',')

    # Template error
    exc = partial(InputError, must_be='not more than 2 data places', received="'{}{}{}'",
                  func_name='check_items()')
    error = exc('extra_template')
    raises(error, check_items, (1, 2), (1, 3), extra_template='{}{}{}')
    raises(error, check_items, (1, 2), (1, 3), extra_template='{}{}{}', absent_template='{}{}')
    error = exc('absent_template')
    raises(error, check_items, (1, 2), (1, 3), absent_template='{}{}{}')
    raises(error, check_items, (1, 2), (1, 3), extra_template='{}{}', absent_template='{}{}{}')

    # Without error, but more pythonic
    assert check_items([1], [1], extra_template='{}{}{}')
    assert check_items([1], [1], absent_template='{}{}{}')
    assert check_items([1], [1], extra_template='{}{}{}', absent_template='{}{}')
    assert check_items([1], [1], extra_template='{}{}', absent_template='{}{}{}')
    assert check_items([1], [1], extra_template='{}{}{}', absent_template='{}{}{}')

    extra_msg = "Extra items: '2', 4"
    absent_msg = "Absent items: '3', 5"
    add_extra = ". Must be not more than expected (1, '3', 5), but received: 1, '2', 4"
    add_absent = ". Must be not less than expected (1, '3', 5), but received: 1, '2', 4"
    assert check_items(*eav, as_text=True) == f'{extra_msg}. {absent_msg}' + add3
    assert check_items(*eav, as_text=True, extra=False) == absent_msg + add_absent
    assert check_items(*eav, as_text=True, absent=False) == extra_msg + add_extra
    assert check_items(*eav, as_text=True, extra=False, absent=False) == ""
    assert check_items(*eav, extra=False, absent=False) == (1, '2', 4)
    assert check_items((1, 2), (1, 2), as_text=True) == ""
    assert check_items((1, 2), (1, 2)) == (1, 2)

    exc_inp = InputError('name1', msg=f'{extra_msg}. {absent_msg}' + add3)
    raises(exc_inp, check_items, *eav, input_exc=('', 'name1'))
    assert check_items(*eav, input_exc=('', 'name1'), as_text=True) == str(exc_inp)


def test_check_lengths():
    assert check_lengths([1], [1])
    assert check_lengths([2], [3])
    assert check_lengths((1, 2, 4), (1, 3, 5))
    exc = CheckValueError
    ev = (1, '2', 3), [1]
    av = ev[::-1]

    # Extra values length
    add1 = ". Must be 1 value long, but received 3"
    raises(exc("Extra value: 2. Must be 1 value long, but received 2"),
           check_lengths, (1, 2), [1])
    raises(exc("Extra vals: '2', 3. Must be 1 val long, but received 3"),
           check_lengths, *ev, 'val')
    raises(exc("Extra values: '2', 3" + add1),
           check_lengths, *ev)

    raises(exc("E\n\t'2'\n\t3" + add1),
           check_lengths, *ev, extra_template='E\n\t', item_sep='\n\t')
    raises(exc("E values: '2' 3" + add1),
           check_lengths, *ev, extra_template='E {}: ', item_sep=' ')
    raises(exc("E values('2',3)" + add1),
           check_lengths, *ev, extra_template='E {}({})', item_sep=',')
    raises(exc("E xs('2',3). Must be 1 x long, but received 3"),
           check_lengths, *ev, 'x', extra_template='E {}({})', item_sep=',')
    raises(exc("E x('2',3). Must be 1  long, but received 3"),
           check_lengths, *ev, '', extra_template='E x{}({})', item_sep=',')

    raises(InputError('template', must_be='not more than 2 data places', received="'{}{}{}'",
                      func_name='check_lengths()'),
           check_lengths, *ev, extra_template='{}{}{}')  # with error

    assert check_lengths(*ev, as_text=True) == "Extra values: '2', 3" + add1
    assert check_lengths([1], (1, 2), absent=False, as_text=True) == ""
    assert check_lengths([1], (1, 2), absent=False) == [1]

    exc_inp = InputError('name1', msg="Extra values: '2', 3" + add1)
    raises(exc_inp, check_lengths, *ev, input_exc=('', 'name1'))
    assert check_lengths(*ev, input_exc=('', 'name1'), as_text=True) == str(exc_inp)

    raises(exc("Extra strs: 2, 3. Must be 1 str long, but received 3"),
           check_lengths, *ev, 'str', str)
    raises(exc("Extra strs: 2, 3. Must be 1 str long, but received 3. Some x"),
           check_lengths, *ev, 'str', str, some='x')

    # Absent values length
    add2 = ". Must be 3 values long, but received 1"
    raises(exc("Absent value: 2. Must be 2 values long, but received 1"),
           check_lengths, [1], (1, 2))
    raises(exc("Absent vals: '2', 3. Must be 3 vals long, but received 1"),
           check_lengths, *av, 'val')
    raises(exc("Absent values: '2', 3" + add2),
           check_lengths, *av)
    raises(exc("A\n\t'2'\n\t3" + add2),
           check_lengths, *av, absent_template='A\n\t', item_sep='\n\t')
    raises(exc("A values: '2' 3" + add2),
           check_lengths, *av, absent_template='A {}: ', item_sep=' ')
    raises(exc("A values('2',3)" + add2),
           check_lengths, *av, absent_template='A {}({})', item_sep=',')
    raises(exc("A xs('2',3). Must be 3 xs long, but received 1"),
           check_lengths, *av, 'x', absent_template='A {}({})', item_sep=',')
    raises(exc("A x('2',3). Must be 3  long, but received 1"),
           check_lengths, *av, '', absent_template='A x{}({})', item_sep=',')

    raises(InputError('template', must_be='not more than 2 data places', received="'{}{}{}'",
                      func_name='check_lengths()'),
           check_lengths, *av, absent_template='{}{}{}')     # with error

    assert check_lengths(*av, as_text=True) == "Absent values: '2', 3" + add2
    assert check_lengths((1, 2), [1], extra=False,  as_text=True) == ""
    assert check_lengths((1, 2), [1], extra=False) == (1, 2)

    exc_inp = InputError('name1', msg="Absent values: '2', 3" + add2)
    raises(exc_inp, check_lengths, *av, input_exc=('', 'name1'))
    assert check_lengths(*av, input_exc=('', 'name1'), as_text=True) == str(exc_inp)

    raises(exc("Absent strs: 2, 3. Must be 3 strs long, but received 1"),
           check_lengths, *av, 'str', str)
    raises(exc("Absent strs: 2, 3. Must be 3 strs long, but received 1. Some x"),
           check_lengths, *av, 'str', str, some='x')

    # Wrong template (without error, but more pythonic)
    assert check_lengths([0], [0], extra_template='{}{}{}')
    assert check_lengths([1], [1], absent_template='{}{}{}')
    assert check_lengths([0], [1], extra_template='{}{}{}', absent_template='{}{}')
    assert check_lengths([1], [0], extra_template='{}{}', absent_template='{}{}{}')
    assert check_lengths([2], [3], extra_template='{}{}{}', absent_template='{}{}{}')


def test_check_type():
    # Check simple
    assert check_type('some', str) == 'some'
    raises(InputError('obj_t', must_be='type or types', received="'int' (str)",
                      func_name='check_type()'),
           check_type, 'some', 'int')

    # Check with typecast if enabled
    assert check_type('5', int, True) == check_type('5', int, typecast=True) == 5
    assert check_type('some', (int, tuple), True) == ('s', 'o', 'm', 'e')

    # Format error
    raises(CheckTypeError("'some' (str) must be int type"), check_type, 'some', int)

    assert isinstance(exc1 := safe(int, 'some'), ValueError)
    raises(CheckTypeError(f"'some' (str) must be int type, typecast to int: {exc1!r}"),
           check_type, 'some', int, True)

    assert isinstance(exc2 := safe(dict, 'some'), ValueError)
    msg = (f"'some' (str) must be int or dict types, typecast to int: {exc1!r}, "
           f"typecast to dict: {exc2!r}")
    raises(CheckTypeError(msg), check_type, 'some', (int, dict), True)

    field_error = CheckTypeError('Field ' + msg)
    raises(field_error, check_type, 'some', (int, dict), True, 'field')
    raises(field_error, check_type, 'some', (int, dict), typecast=True, name='field')


def test_check_types():
    # Check mutually exclusive input parameters
    raises(InputError('one_obj', 'pairs', must_be='not more than one True', received='both',
                      func_name='check_types()'),
           check_types, (), None, one_obj=True, pairs=True)

    # Check input obj
    obj_error = partial(InputError, 'obj', must_be='one or more objects without None',
                        func_name='check_types()')
    raises(obj_error(received="obj = None (objects = ())"), check_types, None, None)
    raises(obj_error(received="obj = ()"), check_types, (), None)
    raises(obj_error(received="obj = (<class 'tuple'>, None)"), check_types, (tuple, None), None)

    # Check input obj_t
    obj_t_error = partial(InputError, 'obj_t', must_be='type or types', func_name='check_types()')
    raises(obj_t_error(received="() (tuple)"), check_types, 1, ())
    raises(obj_t_error(received="None (NoneType)"), check_types, 1, None)
    raises(obj_t_error(received="5 (int)"), check_types, 5, 5)
    raises(obj_t_error(received="5 (int) at pos 0"), check_types, 5, (5, int))
    raises(obj_t_error(received="5 (int) at pos 1"), check_types, 5, (int, 5))
    raises(obj_t_error(received="5 (int) at pos 0, True (bool) at pos 3"),
           check_types, 5, (5, int, str, True))

    # Check typecast specific
    msg = ("5 (int) must be WrongCast or tuple types, "
           "typecast to WrongCast: 5 (int), "
           "typecast to tuple: TypeError(\"'int' object is not iterable\")")
    raises(CheckTypeError(msg), check_types, 5, (WrongCast, tuple), True)

    # Check dicts specific
    msg = "Extra key (without type): '2'. Absent keys (type provided): '3', '4'"
    raises(InputError('obj', msg=msg, func_name='check_types()'),
           check_types, {'1': 1, '2': 2}, {'1': int, '3': str, '4': str})

    # Check pairs specific
    msg = "Extra value (without type): '13'. Must be 1 value long, but received 2"
    raises(InputError('obj', msg=msg, func_name='check_types()'),
           check_types, (5, '13'), str, pairs=True)

    # Check error in single objects
    raises(CheckTypeError("5 (int) must be str type"), check_types, 5, str)
    raises(CheckTypeError("5 (int) must be str or bool types"), check_types, 5, (str, bool))
    raises(CheckTypeError("5 (int) at pos 0 must be str type"), check_types, (5, 'x'), str)
    raises(CheckTypeError("5 (int) at pos 0 must be str or bool types"),
           check_types, (5, 'x'), (str, bool))

    # Check errors in multiple positional objects
    msg = "Several objects are not bool type: 5 (int) at pos 0, 'x' (str) at pos 1"
    raises(CheckTypeError(msg), check_types, (5, 'x'), bool)

    msg = "Several objects are not bool or float types: 5 (int) at pos 0, 'x' (str) at pos 1"
    raises(CheckTypeError(msg), check_types, (5, 'x'), (bool, float))

    msg = ("Several objects has a wrong type:\n"
           "\t5 (int) at pos 0 must be bool type\n"
           "\t'x' (str) at pos 1 must be float type")
    raises(CheckTypeError(msg), check_types, (5, 'x'), (bool, float), pairs=True)

    msg = ("Several objects has a wrong type:\n"
           "\t5 (int) at pos 0 must be bool type\n"
           "\t'x' (str) at pos 1 must be float type")
    raises(CheckTypeError(msg), check_types, (5, 'x'), {1: bool, 2: float}, pairs=True)

    # Check errors in multiple named objects
    dict_item, dict_items = {'name1': 5}, {'name1': 5, 2: '3'}
    raises(CheckTypeError("'name1'=5 (int) must be str type"), check_types, dict_item, str)

    msg = ("'name1'=5 (int) must be WrongCast or tuple types, "
           "typecast to WrongCast: 5 (int), "
           "typecast to tuple: TypeError(\"'int' object is not iterable\")")
    raises(CheckTypeError(msg), check_types, dict_item, (WrongCast, tuple), True)

    msg = "Several objects are not bool type: 'name1'=5 (int), 2='3' (str)"
    raises(CheckTypeError(msg), check_types, dict_items, bool)

    msg = ("Several objects has a wrong type:\n"
           "\tname1: 5 (int) must be bool type\n"
           "\t2: '3' (str) must be float type")
    raises(CheckTypeError(msg), check_types, dict_items, (bool, float), pairs=True)

    msg = ("Several objects has a wrong type:\n"
           "\tname1: 5 (int) must be bool type\n"
           "\t2: '3' (str) must be float type")
    raises(CheckTypeError(msg), check_types, dict_items, {2: float, 'name1': bool})

    # Check named params
    name = 'item'
    raises(CheckTypeError("Item 'name1'=5 (int) must be str type"),
           check_types, dict_item, str, item_name=name)

    msg = ("Item 'name1'=5 (int) must be WrongCast or tuple types, "
           "typecast to WrongCast: 5 (int), "
           "typecast to tuple: TypeError(\"'int' object is not iterable\")")
    raises(CheckTypeError(msg), check_types, dict_item, (WrongCast, tuple), True, item_name=name)

    msg = ("Several items has a wrong type:\n"
           "\tItem name1: 5 (int) must be bool type\n"
           "\tItem 2: '3' (str) must be float type")
    raises(CheckTypeError(msg), check_types, dict_items, (bool, float), pairs=True, item_name=name)

    msg = "Several items are not bool type: 5 (int) at pos 0, '3' (str) at pos 1"
    raises(CheckTypeError(msg), check_types, (5, '3'), bool, item_name=name)

    msg = "Several items are not bool type: 'name1'=5 (int), 2='3' (str)"
    raises(CheckTypeError(msg), check_types, dict_items, bool, item_name=name)

    # Positive check input obj
    assert check_types((), tuple, one_obj=True) == ()
    assert check_types((5,), int) == (5,)
    assert check_types((5,), tuple, one_obj=True) == (5,)

    # Positive check single objects
    assert check_types(5, (str, bool, int)) == 5
    assert check_types(5, (str, bool, int), True) == 5
    assert check_types('5', int, True) == 5

    # Positive check multiple objects
    test_obj = (5, 'x', False)
    assert check_types(test_obj, str, True) == ('5', 'x', 'False')
    assert check_types(test_obj, (str, bool, int)) == test_obj
    assert check_types(test_obj, (str, bool, int), True, pairs=True) == ('5', True, 0)
    assert check_types(dict_items, (str, int)) == dict_items
    assert check_types(dict_items, (str, int), True, pairs=True) == {'name1': '5', 2: 3}
    assert check_types(dict_items, {2: int, 'name1': str}, True) == {'name1': '5', 2: 3}  # noqa

    # Positive check mutually exclusive input parameters
    assert check_types(test_obj, (tuple,), one_obj=True, pairs=False) == test_obj
    assert check_types(test_obj, (int, str, bool), one_obj=False, pairs=True) == test_obj
    assert check_types(test_obj, (int, str), one_obj=False, pairs=False) == test_obj


# Decorators


def test_decorate_methods():    # noqa C901
    class Fixed(str):
        attr = 1
        def visible(self): pass
        def _intern(self): pass
        def __dnd__(self): pass

    def decorator(func):  # noqa
        return 'Processed'

    @decorate_methods(decorator)
    class Empty(Fixed):
        attr = 1

    @decorate_methods(decorator)
    class Visible(Fixed):
        attr = 1
        def visible(self): pass
        def _intern(self): pass
        def __dnd__(self): pass

    @decorate_methods(decorator, exclude=is_hidden)
    class Hidden1(Fixed):
        attr = 1
        def visible(self): pass
        def _intern(self): pass
        def __dnd__(self): pass

    @decorate_methods(decorator, exclude=('_intern', '__dnd__'))
    class Hidden2(Fixed):
        attr = 1
        def visible(self): pass
        def _intern(self): pass
        def __dnd__(self): pass

    @decorate_methods(decorator, exclude=is_internal)
    class Internal1(Fixed):
        attr = 1
        def visible(self): pass
        def _intern(self): pass
        def __dnd__(self): pass

    @decorate_methods(decorator, exclude='_intern')
    class Internal2(Fixed):
        attr = 1
        def visible(self): pass
        def _intern(self): pass
        def __dnd__(self): pass

    @decorate_methods(decorator, exclude=is_dunder)
    class Dunder1(Fixed):
        attr = 1
        def visible(self): pass
        def _intern(self): pass
        def __dnd__(self): pass

    @decorate_methods(decorator, exclude='__dnd__')
    class Dunder2(Fixed):
        attr = 1
        def visible(self): pass
        def _intern(self): pass
        def __dnd__(self): pass

    @decorate_methods(decorator, exclude=lambda x: x)
    class NoOne(Fixed):
        attr = 1
        def visible(self): pass
        def _intern(self): pass
        def __dnd__(self): pass

    @decorate_methods(decorator, exclude=lambda x: '')
    class All(Fixed):
        attr = 1
        def visible(self): pass
        def _intern(self): pass
        def __dnd__(self): pass

    for cls, v_state, h_state, d_state in [(Fixed, False, False, False),
                                           (Empty, False, False, False),
                                           (Visible, True, False, False),
                                           (Hidden1, True, False, False),
                                           (Hidden2, True, False, False),
                                           (Internal1, True, False, True),
                                           (Internal2, True, False, True),
                                           (Dunder1, True, True, False),
                                           (Dunder2, True, True, False),
                                           (NoOne, False, False, False),
                                           (All, True, True, True)]:
        assert cls.attr == 1
        assert (cls.visible == 'Processed') == v_state
        assert (cls._intern == 'Processed') == h_state
        assert (cls.__dnd__ == 'Processed') == d_state


def test_init_reraise():
    class Some1:
        @init_reraise
        def __init__(self, *args, **kwargs):  # noqa
            if kwargs.get('no_exception'):
                return
            raise ValueError('Bad')

    class Some2:
        @init_reraise
        def __init__(self):
            raise ValueError('Bad')

    class Cat:
        @init_reraise('animal')
        def __init__(self):
            raise ValueError('Bad')

    class Dog:
        """Kristy, the dog"""
        @init_reraise('animal', doc=True)
        def __init__(self):
            raise ValueError('Bad')

    def error(view='', *, cn='Some1', tn='class'):
        return InitError(f"Cannot init {tn} {cn!r} (self.__init__({view}))"), ValueError('Bad')

    Some1(no_exception=True)
    raises(error(), Some1)
    raises(error(cn='Some2'), Some2)
    raises(error(cn='Cat', tn='animal'), Cat)
    raises(error(cn='Kristy, the dog', tn='animal'), Dog)

    for kwv, _kwargs in (('', {}), ('x=3', {'x': 3}), ('x=3, y=4', {'x': 3, 'y': 4})):
        for v, _args in (('', ()), ('1', (1,)), ('1, 2', (1, 2))):
            raises(error(f'{v}, {kwv}' if v and kwv else v or kwv), Some1, *_args, **_kwargs)


def test_set_slots_defaults():
    def deco(*args, **kwargs):
        @set_slots_defaults(*args, **kwargs)
        class Deco:  # noqa
            f1 = 1
            f2 = '2'
        return Deco

    def error(params, msg, func_name):
        return InputError(*as_holder(params), func_name=func_name, msg=msg)

    def deco_error(params, msg):
        return error(params, msg, '@set_slots_defaults()')

    def init_error(params, msg):
        return error(params, msg, 'Deco()')

    # Decorator input params error
    raises(deco_error('field_names', '5 (int) must be str type'), deco, 5)
    raises(deco_error('field_names', '5 (int) at pos 2 must be str type'), deco, ('x', 'y', 5))
    raises(deco_error('field_func', '5 (int) must be Callable type'), deco, 'x', 5)
    raises(deco_error('fields_t', '5 (int) must be type type'), deco, 'x', lambda: True, 5)

    # Decorator equality with different ways of fields declaring
    @set_slots_defaults
    class Deco:
        f1 = 1
        f2 = '2'
        f3 = empty_func
    assert Deco() == deco()() == deco('f1')() == deco(('f1', 'f2'), lambda k, v: False)()

    # Decorator repr validity
    assert Deco() == eval(repr(Deco()))

    # Decorated class init error
    raises(init_error('*args', "Extra value: 'x3'. Must be 2 values long, but received 3"),
           Deco, 'x1', 'x2', 'x3')
    err_msg = ". Must be not more than expected ('f1', 'f2'), but received: 'f1', 'f2', 'f3'"
    raises(init_error('**kwargs', "Extra item: 'f3'" + err_msg), Deco, f1='x1', f2='x2', f3='x3')

    err_msg = 'Already provided item in args: '
    raises(init_error(('*args', '**kwargs'), err_msg + 'f2'), Deco, 'x1', 'x2', f2='x2')
    raises(init_error(('*args', '**kwargs'), err_msg + 'f1'), Deco, 'x1', f1='x1')

    raises(init_error('*args', "'x1' (str) at pos 0 must be int type"), deco(fields_t=int), 'x1')
    raises(init_error('**kwargs', "'f1'='x1' (str) must be int type"), deco(fields_t=int), f1='x1')


# Getters


def test_get_cls_obj():
    assert get_cls_obj(None) == (None, None)
    assert get_cls_obj(int) == (int, None)
    assert (x := get_cls_obj(5)) == (int, 5) == (x.cls, x.obj)


def test_get_cls_attr():
    class Something:
        pass

    assert get_cls_attr(None, '__qualname__') is None
    assert get_cls_attr(Something, '__qualname__') == Something.__qualname__
    assert get_cls_attr(Something(), '__qualname__') == Something.__qualname__
    raises(AttributeError("type object 'Something' has no attribute 'asd'"),
           get_cls_attr, Something, 'asd')


def test_get_attrs():
    # Checked classes
    class C1:
        """Class 1 (base)"""
        x1: int                                                                      # type: ignore
        x2: int = 12                                                                 # type: ignore
        x3 = 13
        x6: int                                                                      # type: ignore
        _x7: int                                                                     # type: ignore
        _x8 = 18

    class C1S:
        """Class 1 (base, slots)"""
        __slots__ = ('x6', '_x7')
        x1: int                                                                      # type: ignore
        x2: int = 12                                                                 # type: ignore
        x3 = 13
        x6: int                                                                      # type: ignore
        _x7: int                                                                     # type: ignore
        _x8 = 18

    class C2(C1):
        """Class 2 (inherited)"""
        x1 = 21
        x2 = 22
        x4 = 24
        x5: int = 25                                                                 # type: ignore

        def __init__(self, x6=36, x7=37, x9=39):
            self.x6 = x6
            self._x7 = x7
            self.x9 = x9

    class C2S(C1S):
        """Class 2 (inherited, slots)"""
        __slots__ = ('x9',)
        x1 = 21
        x2 = 22
        x4 = 24
        x5: int = 25                                                                 # type: ignore

        def __init__(self, x6=36, x7=37, x9=39):
            self.x6 = x6
            self._x7 = x7
            self.x9 = x9

    # Skip args check
    def skip_recv(total: int, parent: int, child: int):
        return {'must_be': f'less than {total} skipped in total',
                'skipped': f': {total} (skip_parent = {parent}, skip_child = {child})'}

    exc = partial(InputError, 'skip_parent', 'skip_child', func_name='get_attrs()')
    raises(exc(**skip_recv(2, 2, 0)), get_attrs, C2, 2)
    raises(exc(**skip_recv(2, 1, 1)), get_attrs, C2, 1, 1)
    raises(exc(**skip_recv(3, 3, 0)), get_attrs, C2, 3, ignored=())
    raises(exc(**skip_recv(3, 2, 1)), get_attrs, C2, 2, 1, ignored=())

    exc2 = InputError('ignored', func_name='get_attrs()', msg="1 (int) at pos 0 must be type type")
    raises(exc2, get_attrs, C2, ignored=(1,))

    # Helper functions
    def merge_common(x, y, attrs=('__annotations__', '__slots__')) -> dict:
        return {attr: (xa | ya if isinstance(xa or ya, Mapping) else (*xa, *ya)) for attr in attrs
                if (xa := getattr(x, attr, {}), ya := getattr(y, attr, {})) and xa or ya}

    def dict_build(obj) -> dict:
        return {k: getattr(obj, k, None) for k in obj.__dir__()}

    # Helper base objects
    co = object                 # class <object>
    cod = co.__dict__           # class <object> dict

    ct = type                   # class <type>
    ctd = cod | type.__dict__   # class <type> dict (type is inherited from object!)
    cta = {'mro': type.mro}     # class <type> attributes

    oo = co()                   # object <object>
    ood = dict_build(oo)        # object <object> dict

    # Helper exceptions
    __e = partial(InputError, 'obj', must_be='not ignored type', func_name='get_attrs()',
                  ignored_types=': type, object')
    cte = __e(received="type (type)")
    coe = __e(received="object (type)")
    ooe = __e(received=f"{oo!r} (object)")

    # Helper class 1 objects
    c1_____ = {'x2': 12, 'x3': 13}      # class 1 attributes
    c1__h__ = c1_____ | {'_x8': 18}     # class 1 internal
    c1__hd_ = C1.__dict__               # class 1 hidden
    c1___d_ = c1__hd_.copy()            # class 1 dunder
    c1___d_.pop('_x8')                  # [-] remove internal
    c1___di = cod | c1___d_             # class 1 dunder no_ignored
    c1__hdi = cod | c1__hd_             # class 1 hidden no_ignored

    o1 = C1()                           # object 1

    # Helper class 1 slots objects
    c1s____ = c1_____ | {'x6': C1S.x6}              # class 1 slots attributes
    c1s_h__ = c1__h__ | c1s____ | {'_x7': C1S._x7}  # class 1 slots internal
    c1s_hd_ = C1S.__dict__                          # class 1 slots hidden
    c1s__d_ = c1s_hd_.copy()                        # class 1 slots dunder
    c1s__d_.pop('_x7')                              # [-] remove internal
    c1s__d_.pop('_x8')                              # [-] remove internal
    c1s__di = cod | c1s__d_                         # class 1 slots dunder no_ignored
    c1s_hdi = cod | c1s_hd_                         # class 1 slots hidden no_ignored

    o1s = C1S()                                     # object 1 slots
    o1s_hd_ = dict_build(o1s) | c1s_hd_             # object 1 slots hidden
    o1s__d_ = o1s_hd_.copy()                        # object 1 slots dunder
    o1s__d_.pop('_x7')                              # [-] remove internal
    o1s__d_.pop('_x8')                              # [-] remove internal
    o1s__di = cod | o1s__d_                         # object 1 slots dunder no_ignored
    o1s_hdi = cod | o1s_hd_                         # object 1 slots hidden no_ignored

    # Helper class 2 objects
    c2_____ = c1_____ | {'x1': 21, 'x2': 22, 'x4': 24, 'x5': 25}    # class 2 attributes
    c2__h__ = c1__h__ | c2_____                                     # class 2 internal
    c2__hd_ = c1__hd_ | C2.__dict__ | merge_common(C1, C2)          # class 2 hidden
    c2___d_ = c2__hd_.copy()                                        # class 2 dunder
    c2___d_.pop('_x8')                                              # [-] remove internal
    c2___di = cod | c2___d_                                         # class 2 dunder no_ignored
    c2__hdi = cod | c2__hd_                                         # class 2 hidden no_ignored

    o2 = C2()                                                       # object 2
    o2_____ = c2_____ | {'x6': 36, 'x9': 39}                        # object 2 attributes
    o2__h__ = c1__h__ | o2_____ | {'_x7': 37}                       # object 2 internal
    o2___d_ = c1___d_ | c2___d_ | o2_____                           # object 2 dunder
    o2__hd_ = o2__h__ | o2___d_                                     # object 2 hidden
    o2___di = cod | o2___d_                                         # object 2 dunder no_ignored
    o2__hdi = cod | o2__hd_                                         # object 2 hidden no_ignored

    # Helper class 2 slots objects
    c2s____ = c1s____ | c2_____ | {'x9': C2S.x9}                # class 2 slots attributes
    c2s_h__ = c1s_h__ | c2s____                                 # class 2 slots internal
    c2s_hd_ = c1s_hd_ | C2S.__dict__ | merge_common(C1S, C2S)   # class 2 slots hidden
    c2s__d_ = c2s_hd_.copy()                                    # class 2 slots dunder
    c2s__d_.pop('_x7')                                          # [-] remove internal
    c2s__d_.pop('_x8')                                          # [-] remove internal
    c2s__di = cod | c2s__d_                                     # class 2 dunder no_ignored
    c2s_hdi = cod | c2s_hd_                                     # class 2 hidden no_ignored

    o2s = C2S()
    o2s_hd_ = dict_build(o2s) | merge_common(C1S, C2S)          # object 2 slots hidden
    o2s__d_ = o2s_hd_.copy()                                    # object 2 slots dunder
    o2s__d_.pop('_x7')                                          # [-] remove internal
    o2s__d_.pop('_x8')                                          # [-] remove internal
    o2s__di = cod | o2s__d_                                     # object 2 slots dunder no_ignored
    o2s_hdi = cod | o2s_hd_                                     # object 2 slots hidden no_ignored

    # Helper func kwargs
    h__ = {'internal': True}
    _d_ = {'dunder': True}
    __i = {'ignored': ()}
    hd_ = h__ | _d_
    h_i = h__ | __i
    _di = _d_ | __i
    hdi = hd_ | __i

    # All others checks, values: 0:empty, 1:internal, 2:dunder, 3:internal|dunder,
    # 4:no_ignored, 5:no_ignored|internal, 6:no_ignored|dunder, 7:no_ignored|internal|dunder
    for func, results in (
            (None,  [InputError('obj', must_be='not None', received='None',
                                func_name='get_attrs()')] * 8),
            (ct,    [cte, cte, cte, cte, cta, cta, ctd, ctd]),
            (co,    [coe, coe, coe, coe, {},  {},  cod, cod]),
            (oo,    [ooe, ooe, ooe, ooe, {},  {},  ood, ood]),
            (C1,    [c1_____, c1__h__, c1___d_, c1__hd_, c1_____, c1__h__, c1___di, c1__hdi]),
            (o1,    [c1_____, c1__h__, c1___d_, c1__hd_, c1_____, c1__h__, c1___di, c1__hdi]),
            (C1S,   [c1s____, c1s_h__, c1s__d_, c1s_hd_, c1s____, c1s_h__, c1s__di, c1s_hdi]),
            (o1s,   [c1s____, c1s_h__, o1s__d_, o1s_hd_, c1s____, c1s_h__, o1s__di, o1s_hdi]),
            (C2,    [c2_____, c2__h__, c2___d_, c2__hd_, c2_____, c2__h__, c2___di, c2__hdi]),
            (o2,    [o2_____, o2__h__, o2___d_, o2__hd_, o2_____, o2__h__, o2___di, o2__hdi]),
            (C2S,   [c2s____, c2s_h__, c2s__d_, c2s_hd_, c2s____, c2s_h__, c2s__di, c2s_hdi]),
            (o2s,   [o2_____, o2__h__, o2s__d_, o2s_hd_, o2_____, o2__h__, o2s__di, o2s_hdi])):
        for kwargs, result in zip(({}, h__, _d_, hd_, __i, h_i, _di, hdi), results, strict=True):
            if isinstance(result, Exception) or result == InputError:
                raises(result, get_attrs, func, **kwargs)
            else:
                assert get_attrs(func, **kwargs) == result


def test_get_name():    # noqa C901
    test_funcs = (GetName, partial(GetName, full=True))

    # Check wrong input
    wrong_names = ("attr", "attr_cls", "attrs_", "attrs_cos")
    order = ('some_obj', 'code_obj', 'not_exists')
    possible_parameters = ("Possible parameters: doc_obj, code_obj, attrs_obj, doc_cls, "
                           "attrs_cls, str_obj, str_cls, repr_cls, repr_obj")
    details = f"Received: 'some_obj', 'code_obj', 'not_exists'. {possible_parameters}"
    for kwargs, exc_kwargs in [
        ({'doc': ()}, {"msg": "() (tuple) must be bool type"}),
        ({'doc_cls': ()}, {"msg": "() (tuple) must be bool type"}),
        ({'attrs': []}, {"msg": "[] (list) must be bool or tuple types"}),
        ({'attrs_obj': []}, {"msg": "[] (list) must be bool or tuple types"}),
        ({'order': order}, {"msg": f"Not exists methods: 'some_obj', 'not_exists'. {details}"}),
        ({}.fromkeys(wrong_names), {"msg": possible_parameters})
    ]:
        for func in test_funcs:
            raises(InputError(*kwargs, **exc_kwargs, func_name='GetName()'), func, '', **kwargs)

    # Check method wrong input
    msg = ("Provided wrong parameter to GetName.attrs(): attrs. Must be 1 (same for both) "
           "or 2 (separately) provided for cls and obj, but received 3: 'some', 1, 2")
    raises(InputError(msg=msg), GetName.attrs, 'obj', 'some', 1, 2)
    msg = ("Provided wrong parameter(s) to GetName.doc(). "
           "Must be no arguments, but received 1: 'some'")
    raises(InputError(msg=msg), GetName.doc, 'obj', 'some')

    # Check for None target
    for func in test_funcs:
        assert func(None, none=None) is None
        assert (name_obj := func(None)) == ""
        assert isinstance(name_obj, GetName)

    # Check for unknown target
    for func in test_funcs:
        assert func('', unknown=None, attrs=False, repr=False) is None
        assert (name_obj := func('', attrs=False, repr=False)) == ""
        assert isinstance(name_obj, GetName)

    # Prepare data for positive full=True check
    def code_obj():
        pass

    class Non:
        pass

    class Cls:
        """doc_cls"""
        name = 'attrs_cls'
        custom_name = 'attrs_custom_cls'

        @classmethod
        def __repr__(cls):
            return 'repr_cls'

        @classmethod
        def __str__(cls):
            return 'str_cls'

    class Obj:
        def __init__(self):
            self.__doc__ = 'doc_obj'
            self.__code__ = code_obj.__code__
            self.name = 'attrs_obj'
            self.__name__ = 'attrs_dunder_obj'
            self.custom_name = 'attrs_custom_obj'
            self.__repr__ = lambda: 'repr_obj'
            self.__str__ = lambda: 'str_obj'

    class COb(Cls, Obj):
        pass

    class All:
        """doc_cls"""
        name = 'attrs_cls'
        custom_name = 'attrs_custom_cls'

        @classmethod
        def __repr__(cls):
            return 'repr_cls'

        @classmethod
        def __str__(cls):
            return 'str_cls'

        def __init__(self):
            self.__doc__ = 'doc_obj'
            self.__code__ = code_obj.__code__
            self.name = 'attrs_obj'
            self.__name__ = 'attrs_dunder_obj'
            self.custom_name = 'attrs_custom_obj'
            self.__repr__ = lambda: 'repr_obj'
            self.__str__ = lambda: 'str_obj'

    def prepare_name(*prefixes):
        def make_name(root=None):
            if callable(root):  # set prefixes as fixed name if func provided
                return root()
            return join(*prefixes, root, sep='_') if root != '' else ''
        return make_name

    empty = ''
    cls_s = 'cls'
    obj_s = 'obj'
    non_f = prepare_name('Non')         # fixed Non.__name__
    cls_f = prepare_name('Cls')         # fixed Cls.__name__
    obj_f = prepare_name('Obj')         # fixed Obj.__name__
    cob_f = prepare_name('COb')         # fixed COb.__name__
    all_f = prepare_name('All')         # fixed All.__name__

    extension = (
        ['default', '', ()],
        ['empty', '', ([],)],
        ['simple', '', (['name'],)],
        ['dunder', 'dunder', (['__name__'],)],
        ['custom', 'custom', (['custom_name'],)]
    )

    # [(attrs_default), (attrs_empty), (attrs_simple), (attrs_dunder), (attrs_custom)],
    # [(doc)], [(code)], [(str)], [(repr)]
    data = [
        ([(non_f, empty), (empty, empty), (empty, empty), (non_f, empty), (empty, empty)],  # Non
         [(empty, empty)], [(empty, empty)], [(empty, empty)], [(empty, empty)]),
        ([(cls_s, cls_s), (empty, empty), (cls_s, cls_s), (cls_f, empty), (cls_s, cls_s)],  # Cls
         [(cls_s, cls_s)], [(empty, empty)], [(cls_s, cls_s)], [(cls_s, cls_s)]),
        ([(obj_f, obj_s), (empty, empty), (empty, obj_s), (obj_f, obj_s), (empty, obj_s)],  # Obj
         [(empty, obj_s)], [(empty, obj_s)], [(empty, obj_s)], [(empty, obj_s)]),
        ([(cls_s, obj_s), (empty, empty), (cls_s, obj_s), (cob_f, obj_s), (cls_s, obj_s)],  # COb
         [(empty, obj_s)], [(empty, obj_s)], [(cls_s, obj_s)], [(cls_s, obj_s)]),
        ([(cls_s, obj_s), (empty, empty), (cls_s, obj_s), (all_f, obj_s), (cls_s, obj_s)],  # All
         [(cls_s, obj_s)], [(empty, obj_s)], [(cls_s, obj_s)], [(cls_s, obj_s)])
    ]

    # GetName.method(target, *args) + GetName(target, *args, full=True).method tests
    errors = []
    calls = ('GetName.{0}({1}{2}, {3})', 'GetName({1}{2}, full=True, {3}).{0}')
    postfix = ('', '.cls', '.obj')
    for cls, results in zip((Non, Cls, Obj, COb, All), data, strict=True):
        for method, result in zip('attrs doc code str repr'.split(), results, strict=True):
            cm = getattr(GetName, method)
            args_str = ' || args set: ' if len(result) == len(extension) else ''
            for (args_name, suffix, args), (val_cls, val_obj) in zip(extension, result):

                # Must be
                name = prepare_name(method, suffix)
                name_cls, name_obj = name(val_cls), name(val_obj)
                name_first = (name_obj or name_cls)
                must_be_data = ((name_cls, name_cls, empty), (name_first, name_cls, name_obj))

                # Received
                kwargs = {method: args} if args else {method: True}
                received_data = tuple((x, x.cls, x.obj) for x in (
                    cm(cls, *args),
                    cm(cls(), *args),
                    getattr(GetName(cls, full=True, **kwargs), method),
                    getattr(GetName(cls(), full=True, **kwargs), method)))

                # Compare
                if must_be_data * 2 != received_data:
                    for i, (r, m) in enumerate(zip(received_data, must_be_data, strict=True)):
                        for received, must_be, p in zip(r, m, postfix, strict=True):
                            if received != must_be:
                                obj_str = '()' if i % 2 else ''
                                kw_str = ', '.join(fmt_dict(kwargs))
                                sig = calls[i // 2].format(method, cls.__name__, obj_str, kw_str)
                                add = args_str + args_name if args_str else ''
                                msg = f'{sig}{p} == {received!r} || must be: {must_be!r}{add}'
                                errors.append(msg)
    if errors:
        raise ValueError('\n\t'.join(('Test failed, errors:', *errors)))


# Uncategorized


def test_uid():
    id1 = UID('1')
    id2 = UID('2')
    raises(TypeError, UID)
    raises(ValueError("'1' unique ID cannot be created, it already exists"), UID, 1)
    assert repr(id1) == "UID('1')"
    assert str(id1) == "1 ID"
    assert id1 == id1
    assert id1 != id2


def test_locker():  # noqa C901
    class All(Locker):
        def __init__(self):
            self.a = 1
            super().__init__('b')
            self.b = 2
            with self:
                self.c = 3

    class Add(Locker):
        def __init__(self):
            self.a = 1
            super().__init__('b', del_attr=False)
            self.b = 2
            with self:
                self.c = 3

    class Del(Locker):
        def __init__(self):
            self.a = 1
            super().__init__('b', set_attr=False)
            exceptions = ''
            try:
                self.b = 2
            except TypeError:
                exceptions += 'b'
            try:
                with self:
                    self.c = 3
            except TypeError:
                exceptions += 'c'

            assert exceptions == 'bc'
            object.__setattr__(self, 'b', 2)
            object.__setattr__(self, 'c', 3)

    class Non(Locker):
        def __init__(self):
            self.a = 1
            super().__init__('b', set_attr=False, del_attr=False)
            exceptions = ''
            try:
                self.b = 2
            except TypeError:
                exceptions += 'b'
            try:
                with self:
                    self.c = 3
            except TypeError:
                exceptions += 'c'

            assert exceptions == 'bc'
            object.__setattr__(self, 'b', 2)
            object.__setattr__(self, 'c', 3)

    class AllSlot(Locker):
        __slots__ = tuple('abcd')

        def __init__(self):
            self.a = 1
            super().__init__('b')
            self.b = 2
            with self:
                self.c = 3

    class AddSlot(Locker):
        __slots__ = tuple('abcd')

        def __init__(self):
            self.a = 1
            super().__init__('b', del_attr=False)
            self.b = 2
            with self:
                self.c = 3

    class DelSlot(Locker):
        __slots__ = tuple('abcd')

        def __init__(self):
            self.a = 1
            super().__init__('b', set_attr=False)
            exceptions = ''
            try:
                self.b = 2
            except TypeError:
                exceptions += 'b'
            try:
                with self:
                    self.c = 3
            except TypeError:
                exceptions += 'c'

            assert exceptions == 'bc'
            object.__setattr__(self, 'b', 2)
            object.__setattr__(self, 'c', 3)

    class NonSlot(Locker):
        __slots__ = tuple('abcd')

        def __init__(self):
            self.a = 1
            super().__init__('b', set_attr=False, del_attr=False)
            exceptions = ''
            try:
                self.b = 2
            except TypeError:
                exceptions += 'b'
            try:
                with self:
                    self.c = 3
            except TypeError:
                exceptions += 'c'

            assert exceptions == 'bc'
            object.__setattr__(self, 'b', 2)
            object.__setattr__(self, 'c', 3)

    for data in (All, Add, Del, Non, AllSlot, AddSlot, DelSlot, NonSlot):
        # Prepare message templates for set and del parts test
        data = data()
        obj = GetName(data)
        name = f'{obj!r} object'
        can_set = name + " is locked for changes (self.__setattr__('{}', {}))"
        can_del = name + " is locked for changes (self.__delattr__('{}'))"
        cant_set = name + " does not support setting attributes (self.__setattr__('{}', {}))"
        cant_del = name + " does not support deleting attributes (self.__delattr__('{}'))"
        not_exists = name + " has no attribute '{}'"
        forbid = name + " Locker attrs deletion is forbidden (self.__delattr__('{}'))"

        # [0. Init] Check locked object condition after init
        assert data._locker_state is True
        assert data._locker_ignored == ('b',)
        assert data.a == 1
        assert data.b == 2
        assert data.c == 3
        assert not hasattr(data, 'd')

        # [1. Set] 1. Check object attrs changes without unlocking
        msg = can_set if data._locker_set_attr else cant_set
        for attr, prev_value in zip('acd', (1, 3, 4), strict=True):
            raises(TypeError(msg.format(attr, 5)), setattr, data, attr, 5)
            if attr != 'd':
                assert getattr(data, attr) == prev_value
            else:
                assert not hasattr(data, attr)

        # [1. Set] 2. Check object attrs changes in ignored attr and unlocked attrs
        if data._locker_set_attr:
            data.b = 5
            assert data.b == 5

            with data:
                data.a = 5
                assert data.a == 5

                data.c = 5
                assert data.c == 5

                data.d = 5
                assert data.d == 5
        else:
            raises(TypeError(cant_set.format('b', 5)), setattr, data, 'b', 5)
            assert data.b == 2

            with data:
                raises(TypeError(cant_set.format('a', 5)), setattr, data, 'a', 5)
                assert data.a == 1

                raises(TypeError(cant_set.format('c', 5)), setattr, data, 'c', 5)
                assert data.c == 3

                raises(TypeError(cant_set.format('d', 5)), setattr, data, 'd', 5)
                assert not hasattr(data, 'd')

        # [1. Set] 3. Check object new attrs creation
        with data:
            if obj == 'All' or obj == 'Add':  # Has __dict__ and set allowed
                data.e = 5
                assert data.e == 5
            elif obj == 'AllSlot' or obj == 'AddSlot':
                raises(AttributeError(not_exists.format('e')), setattr, data, 'e', 5)
            elif not data._locker_set_attr:
                raises(TypeError(cant_set.format('e', 5)), setattr, data, 'e', 5)
            else:
                raise AssertionError(f'{obj!r} set new attrs check missing!')

        # [2. Del] 1. Check object attrs deletion without unlocking
        exists_d = 'd' if hasattr(data, 'd') else ''
        msg = can_del if data._locker_del_attr else cant_del

        for attr in 'ac' + exists_d:
            raises(TypeError(msg.format(attr)), delattr, data, attr)
            assert hasattr(data, attr)
        if not exists_d:
            raises(AttributeError(not_exists.format('d')), delattr, data, 'd')

        # [2. Del] 2. Check object attrs deletion
        if data._locker_del_attr:
            del data.b
            assert not hasattr(data, 'b')

            with data:
                del data.a
                assert not hasattr(data, 'a')

                del data.c
                assert not hasattr(data, 'c')

                if hasattr(data, 'd'):
                    del data.d
                    assert not hasattr(data, 'd')
        else:
            raises(TypeError(cant_del.format('b')), delattr, data, 'b')
            assert hasattr(data, 'b')

            with data:
                raises(TypeError(cant_del.format('a')), delattr, data, 'a')
                assert hasattr(data, 'a')

                raises(TypeError(cant_del.format('c')), delattr, data, 'c')
                assert hasattr(data, 'c')

                if hasattr(data, 'd'):
                    raises(TypeError(cant_del.format('d')), delattr, data, 'd')
                    assert hasattr(data, 'd')

        # [2. Del] 3. Check Locker attrs deletion
        [raises(TypeError(forbid.format(attr)), delattr, data, attr) for attr in Locker.__slots__]
