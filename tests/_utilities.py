from itertools import zip_longest
from collections import defaultdict

from configlayer.exceptions import InitError, InputError
from configlayer.types import mb_holder_t
from configlayer.utils import safe, GetName, as_holder, fmt_dict


_SUBTEST_DETAILS = False


def raises(exceptions: mb_holder_t[Exception | type[Exception]], func, /, *args, **kwargs):
    """Executed callable should raise specified exception
    Arg 'exception_s' - single exception or exceptions (stored as causes of previous exception)"""
    try:
        result, exception = func(*args, **kwargs), None
    except Exception as e:
        result, exception = None, e

    # Prepare expected and received exception descriptors with ignoring args if not checking it
    # bug mypy: Exception instances has args attribute. And there is Exception, not object
    expected_list = [(exc, None) if isinstance(exc, type) else (type(exc), exc.args)                # type: ignore[attr-defined]
                     for exc in as_holder(exceptions)]
    received_list = []
    if exception:
        iterator = iter(expected_list)
        while exception:
            e_exc, e_args = next(iterator, (None, None))

            # hide raised exception message, only type checked on that level
            r_exc = type(exception)
            r_args: tuple | None = exception.args
            if e_exc is not None and e_args is None:
                r_args = None

            received_list.append((r_exc, r_args))
            # bug mypy: There is no BaseException, only Exception
            exception = exception.__cause__                                                         # type: ignore[assignment]

    # Prepare information on error
    if expected_list == received_list:
        return

    # List errors
    errors = []
    for i, sub in enumerate(zip_longest(expected_list, received_list, fillvalue=(None, None)), 1):
        for name, expected, received in zip(('exceptions', 'arguments '), *sub):
            if expected != received:
                if name == 'exceptions':
                    expected = None if expected is None else expected.__name__
                    # bug mypy: Did not understand from where it comes..
                    received = None if received is None else received.__name__                      # type: ignore[assignment, union-attr]
                errors.append(f'[Level {i}] Incorrect {name}: {expected=}, {received=}')
    errors = [f'\t\t{i}. {error}' for i, error in enumerate(errors, 1)]

    # Format error string with exceptions structures
    messages = ['Expected and received results differ:']
    for info, struct in ('\tExpected:', expected_list), ('\tReceived:', received_list):
        messages.append(info)
        for i, (exc, args) in enumerate(struct, 2):
            msgs = '' if args is None else f'({args[0]})' if len(args) == 1 else str(args)
            messages.append('\t' * i + exc.__name__ + ('\n' + '\t' * i).join(msgs.splitlines()))
    if not received_list:
        messages.append(f'\t\tNo exception! ({result=}, {func=}, {args=}, {kwargs=})')
        exception = None
    raise AssertionError('\n'.join(messages + ['\tErrors:'] + errors)) from exception


def init(name, exceptions: mb_holder_t[Exception], func, /, *args, **kwargs):
    """utils.init_reraise decorator output at raising exception"""
    view = ", ".join((*map(repr, args), *(fmt_dict(kwargs))))
    return (InitError(f"Cannot init {name} '{GetName(func, True)}' (self.__init__({view}))"),
            *as_holder(exceptions))


def raises_init(exceptions: mb_holder_t[Exception], func, /, *args, **kwargs):
    """ConfigBase class __init__ exception message handler"""
    raises(init('config', exceptions, func, *args, **kwargs), func, *args, **kwargs)


def subtest(name, count, cases, div_groups: dict[str, int] | None = None, div='-', out=print,
            names=()):
    i, case, errors = 1, None, []
    results: dict[str, dict[str, int]] = defaultdict(dict[str, int])
    for i, case in enumerate(cases, i):
        while res := (yield i, *case):
            key, received, must_be, *more = res  # noqa
            if hashed := repr(received) if _SUBTEST_DETAILS and key else '':
                if not (values := results[key]) or hashed not in values:
                    values[hashed] = i
            if (not all(received == x for x in (must_be, *more))) if more else received != must_be:
                hashed = hashed or repr(received)
                vals = tuple(map(repr, (safe(repr, x) for x in case)))
                info = ', '.join(fmt_dict(dict(zip(names, vals, strict=True)))) if names else vals
                errors.append((i, key, hashed, tuple(map(repr, (must_be, *more))), info))

    if errors:
        places = len(str(i))
        str_errors = [f'Subtest{f" {name!r}" if name else ""} fails:']
        for i, key, received, expected, params in errors:
            str_errors.append(f'Case {i:0{places}}{f" [{key}]" if key else key}:')
            str_errors.append(f'\tReceived: {received}')
            str_errors.extend(f'\tExpected: {exp}' for exp in expected)
            str_errors.append(f'\tSubtest params: {params}')
        raise AssertionError('\n\t'.join(str_errors))

    if results:
        out(f"\n{name or 'Sub-tests'} ({len(results)}):")
        places = len(str(i))
        for k, v in results.items():
            out(f'\t{k} ({len(v)}):')
            if div_groups and (group := div_groups.get(k)):
                group_i = group
                for result, j in v.items():
                    if j > group_i:
                        group_i = ((j - 1) // group + 1) * group
                        out(f'\t\t{div * places}')
                    out(f'\t\t{j:0{places}}: {result}')
            else:
                [out(f'\t\t{j:0{places}}: {result}') for result, j in v.items()]

    if i != count:
        raise InputError('count', func_name=f'{name} subtest', must_be=count, received=i)


if __name__ == '__main__':
    def link_4_exceptions_correct():
        try:
            try:
                try:
                    int('asd')
                except Exception as e:
                    raise TypeError('3rd level exception') from e
            except Exception as e:
                raise KeyError('2nd level exception', '2nd arg', '3rd arg') from e
        except Exception as e:
            raise ValueError() from e


    raises(AssertionError, raises, TypeError, str, '123')
    text = "No exception! (result = '123', func = <class 'str'>, args = ('123',), kwargs = {})"
    raises(AssertionError(text), raises, TypeError, str, '123')

    raises(AssertionError, raises, TypeError, int, 'asd')
    text = ("Expected and received exceptions differ:\n"
            "\tExpected:\n\t\tTypeError\n"
            "\tReceived:\n\t\tValueError\n"
            "\tErrors:\n\t\t1. [Level 1] Incorrect exceptions: "
            "expected = <class 'TypeError'>, received = <class 'ValueError'>")
    raises(AssertionError(text), raises, TypeError, int, 'asd')

    raises(AssertionError, raises, TypeError(), int, 'asd')
    text = ("Expected and received exceptions differ:\n"
            "\tExpected:\n\t\tTypeError()\n"
            "\tReceived:\n\t\tValueError(invalid literal for int() with base 10: 'asd')\n"
            "\tErrors:\n"
            "\t\t1. [Level 1] Incorrect exceptions: "
            "expected = <class 'TypeError'>, received = <class 'ValueError'>\n"
            "\t\t2. [Level 1] Incorrect arguments: "
            "expected = (), received = (\"invalid literal for int() with base 10: 'asd'\",)")
    raises(AssertionError(text), raises, TypeError(), int, 'asd')

    text = ("Expected and received exceptions differ:\n"
            "\tExpected:\n\t\tTypeError\n"
            "\tReceived:\n"
            "\t\tValueError\n"
            "\t\t\tKeyError('2nd level exception', '2nd arg', '3rd arg')\n"
            "\t\t\t\tTypeError(3rd level exception)\n"
            "\t\t\t\t\tValueError(invalid literal for int() with base 10: 'asd')\n"
            "\tErrors:\n"
            "\t\t1. [Level 1] Incorrect exceptions: "
            "expected = <class 'TypeError'>, received = <class 'ValueError'>\n"
            "\t\t2. [Level 2] Incorrect exceptions: "
            "expected = None, received = <class 'KeyError'>\n"
            "\t\t3. [Level 2] Incorrect arguments: "
            "expected = None, received = ('2nd level exception', '2nd arg', '3rd arg')\n"
            "\t\t4. [Level 3] Incorrect exceptions: "
            "expected = None, received = <class 'TypeError'>\n"
            "\t\t5. [Level 3] Incorrect arguments: "
            "expected = None, received = ('3rd level exception',)\n"
            "\t\t6. [Level 4] Incorrect exceptions: "
            "expected = None, received = <class 'ValueError'>\n"
            "\t\t7. [Level 4] Incorrect arguments: "
            "expected = None, received = (\"invalid literal for int() with base 10: 'asd'\",)")
    raises(AssertionError(text), raises, TypeError, link_4_exceptions_correct)
