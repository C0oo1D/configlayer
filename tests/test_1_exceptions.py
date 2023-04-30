from typing import Callable
from itertools import product
from collections import ChainMap

from configlayer.exceptions import InputError, FieldError
from configlayer.utils import fmt_name, safe

from _utilities import subtest
from _data import ReprError


def test_input_error():
    # Args
    exc_set = ((KeyError('1'),), (ValueError('2', 3),), (KeyError(4, 5, '6'), ValueError('7', 8)))
    items_set = ((), ('item',), ('item1', 'item2'))
    msg_set = ('', 'message')
    item_name_set = ('parameter', 'item')
    func_name_set = ('', 'func()')
    args_set = ((), (0,), (1, 2))
    bools = (False, True)

    # Kwarg: sentences
    sentences_values = ((), ('sentence0',), ('sentence1', 'sentence2'))
    sentences_set = ({}, *({'sentences': v} for v in sentences_values))

    # Kwargs: must_be, received
    must_kw = {'must_be': 'there'}
    recv_kw = {'received': 'here'}
    must_recv_set = ({}, must_kw, recv_kw, must_kw | recv_kw, recv_kw | must_kw)

    # Kwarg type: str, Mapping, tuple, other
    simple_kw_set = ({}, {'str': 'here'}, {'func': lambda: ': there'}, {'tuple': ('e', 6)})

    # All kwargs
    kw_params = (sentences_set, must_recv_set, simple_kw_set)
    kw_set = tuple(dict(ChainMap(*dicts)) for dicts in product(*kw_params[::-1]))

    common_set = (msg_set, item_name_set, func_name_set, args_set, bools, kw_set)

    # Test provided exception
    st = subtest('Exceptions test', 11520, product(exc_set, *common_set), {'repr': 3840})
    for i, exc, msg, item_name, func_name, args, force_header, kwargs in st:
        recv = InputError(*exc, msg=msg, item_name=item_name, func_name=func_name, args=args,
                          force_header=force_header, **kwargs)
        st.send(('', recv.items, exc))
        st.send(('', recv.msg, msg))
        st.send(('', recv.item_name, item_name))
        st.send(('', recv.func_name, func_name))
        st.send(('', recv.kwargs, kwargs))
        st.send(('', recv.must_be, recv.received, recv.header, ''))
        st.send(('', recv.sentences, ()))

        ie_args = ("; ".join(map(repr, exc)), *args)
        result = f'InputError({repr(ie_args)[1:-1 if len(ie_args) > 1 else -2]})'
        st.send(('repr', repr(recv), result))

    # Test InputError exception
    st = subtest('InputError test', 11520, product(items_set, *common_set),
                 {'header': 3840, 'kwargs sentences': 20, 'repr': 80})
    for i, items, msg, item_name, func_name, args, force_header, kwargs in st:
        recv = InputError(*items, msg=msg, item_name=item_name, func_name=func_name, args=args,
                          force_header=force_header, **kwargs)
        st.send(('', recv.items, items))
        st.send(('', recv.msg, msg))
        st.send(('', recv.item_name, item_name))
        st.send(('', recv.func_name, func_name))
        st.send(('', recv.kwargs, kwargs))

        # Check header
        h_func_name = f' to {func_name}' if func_name else ''
        header = f'Provided wrong {fmt_name(items, item_name, item_name + "(s)")}{h_func_name}'
        if items:
            header = f'{header}: {items[0] if len(items) == 1 else ", ".join(items)}'
        elif force_header or h_func_name or not (msg or kwargs):
            pass
        else:
            header = ''
        st.send(('header', recv.header, header))

        # Check received, must_be and sentences
        received = must_be = ''
        must_recv, sentences = [], []
        for k, v in kwargs.items():
            if k == 'sentences':
                sentences.extend(v)
                continue

            v_str = v if isinstance(v, str) else v() if isinstance(v, Callable) else f': {v!r}'
            if not v_str:
                continue

            sentence = f'{k.replace("_", " ")}{"" if v_str[0] in ":,." else " "}{v_str}'

            if k == 'must_be':
                must_be = v
                must_recv.append(sentence)
            elif k == 'received':
                received = v
                must_recv.append(sentence)
            else:
                sentences.append(sentence)

        mr = ', but '.join(must_recv)
        st.send(('', recv.received, received))
        st.send(('', recv.must_be, must_be))
        st.send(('received, must_be', mr, mr))  # Show only

        st.send(('kwargs sentences', ' | '.join(recv.sentences), ' | '.join(sentences)))

        # Check repr
        res_msg = '. '.join(f'{x[0].upper()}{x[1:]}' for x in (header, msg, mr, *sentences) if x)
        result = f'InputError({repr((res_msg, *args))[1:-1 if args else -2]})'
        st.send(('', repr(recv), result))


def test_field_error():
    def show(x):
        return safe(repr, x, _exc_=repr)

    # Constants
    op, cfg, field = 'change amazing used'.split()
    defaults = ('', '', '', '', ' failed', 'config')
    kw_names = ('to_value', 'from_value', 'by_func', 'reason', 'failed', 'type_name')
    kw_funcs = (lambda x: f' to {show(x)!r}', lambda x: f' from {show(x)!r}', lambda x: f' by {x}',
                lambda x: ',{} ' + x, lambda x: ' failed' if x else ' completed', lambda x: x)

    # Cases dicts
    to_values = [{'to_value': ReprError(4)}, {}, {'to_value': 'value 4'}, ]
    from_values = [{}, {'from_value': 3}, {'from_value': ReprError(3)}]
    by_funcs = [{}, {'by_func': 'some func'}]
    reasons = [{}, {'reason': 'some reason'}]
    fails = [{}, {'failed': False}]
    type_names = [{}, {'type_name': 'language'}]

    # Check
    cases = tuple(product(to_values, from_values, by_funcs, reasons, fails, type_names))
    for i, kwargs in (st := subtest('', 144, ([dict(ChainMap(*dicts))] for dicts in cases))):
        # Prepare
        data = [f(safe(kwargs.get, k)) if k in kwargs else d
                for k, f, d in zip(kw_names, kw_funcs, defaults, strict=True)]
        to_value, from_value, by_func, reason, failed, type_name = data
        reason_but = "" if failed else " but"
        msg = f"Change 'amazing' {type_name} field 'used'{from_value}{to_value}{by_func}{failed}"

        # Compare
        st.send(('', str(FieldError(op, cfg, field, **kwargs)), msg + reason.format(reason_but)))
