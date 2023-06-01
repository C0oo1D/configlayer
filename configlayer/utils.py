"""Config layer support classes and functions"""
from types import MappingProxyType
from typing import TypeVar, Iterable, Any, Callable, Sized, Union, get_origin, Sequence
from itertools import chain
from functools import partial
from dataclasses import dataclass
from collections import ChainMap
from collections.abc import Mapping

from .types import state_t, holder_t, mb_holder_t, ClsObj, ItemError, ValidWrong
from .exceptions import InternalError, InputError, InitError, CheckValueError, CheckTypeError


_T = TypeVar('_T')

_TEMPL_INPUT = '{} is{} needed, but{} provided'
_TEMPL_ABSENT = 'Absent {}: '
_TEMPL_EXTRA = 'Extra {}: '

_IE_CE__T = ('check_extra()', 'template')
_IE_CA__T = ('check_absent()', 'template')
_IE_CI_ET = ('check_items()', 'extra_template')
_IE_CI_AT = ('check_items()', 'absent_template')
_IE_CL__T = ('check_lengths()', 'template')

_CE = 'not more than'
_CA = 'not less than'
_CI = 'equal to'

_GN_ATTRS = ('name', '__name__')
_GN_ORDER = ('doc_obj', 'code_obj', 'attrs_obj', 'doc_cls', 'attrs_cls',
             'str_obj', 'str_cls', 'repr_cls', 'repr_obj')
_GN_INTERNAL = ('cls', 'obj', 'full', 'order', 'none', 'unknown', 'kwargs')

_CLS_OBJ = ('cls', 'obj')
_UNIQUE = object()
_FORCE_SET = object.__setattr__

_LOCKER_IGNORED = ('_locker_state', '_locker_enter_state')


# Internal


def _field_func_default(k, v):  # noqa
    return not callable(v)


def _types(obj_t: mb_holder_t[type], func_name='', param_name='obj_t') -> holder_t[type]:
    if isinstance(obj_t, type):
        return obj_t,  # holder_t
    if origin := get_origin(obj_t):
        if origin is Union:
            # bug mypy: Union origin is always has __args__
            return obj_t.__args__                                                                  # type: ignore[attr-defined]
        obj_t = origin

    errors = []
    holder, obj_types = as_holder_stated(obj_t)
    mapping, items = as_dict_stated(obj_types)
    if obj_types:
        if not (errors := [ItemError(k, v) for k, v in items.items() if not isinstance(v, type)]):
            return obj_types
    received = ', '.join(fmt_obj_errors(obj_t, errors, bool(obj_types), holder, mapping))
    raise InputError(param_name, must_be="type or types", received=received, func_name=func_name)


# Bool checks


def is_dunder(name: str) -> bool:
    """Returns True only if a '__dunder__' name provided (double underscored from both sides)
    :arg name:  Target name for check
    :return:    bool"""
    return len(name) > 4 and name[:2] == name[-2:] == '__' and name[2] != '_' and name[-3] != '_'


def is_internal(name: str) -> bool:
    """Returns True only if name is '_internal', excepting '__dunder__' name ('magic' methods)
    :arg name:  Target name for check
    :return:    bool"""
    return name.startswith('_') and not is_dunder(name)


def is_hidden(name: str) -> bool:
    """Returns True if name is hidden - '_internal' or '__dunder__' name
    :arg name:  Target name for check
    :return:    bool"""
    return name.startswith('_')


def is_exception(obj, exc_t: type[Exception] = Exception) -> bool:
    """Returns True only if obj is instance or subclass of provided exception type
    :arg obj:   Target object for check
    :arg exc_t: Exception type for instance or subclass check
    :return:    bool"""
    return isinstance(obj, exc_t) or issubclass(get_cls_obj(obj).cls or object, exc_t)


def is_holder(obj, exclude: mb_holder_t[type] = ()) -> state_t:
    """Returns True only if obj can hold objects of any possible type
    :arg obj:       Target object for check
    :arg exclude:   Type or types that must not be detected as holders
    :return:        bool | None (if :arg obj: is None)"""
    exclude = _types(exclude, 'is_holder()', 'exclude') if exclude else ()  # no RecursionError
    if obj is None:
        return None
    if isinstance(obj, (str, bytes, bytearray) + tuple(exclude)):
        return False
    try:
        iter(obj)  # Check iteration possibility through __iter__ or __getitem__ methods
    except TypeError:
        return False
    return True


# Type casting


def as_holder(obj: mb_holder_t[_T], default=(), exclude: mb_holder_t[type] = ()) -> holder_t[_T]:
    """Returns obj if it is holder type, or make holder from obj, or pass default if obj is None
    :arg obj:       Target object or objects for cast
    :arg default:   Any object that will be returned if :arg obj: is None
    :arg exclude:   Type or types that must not be detected as holders
    :return:        :arg obj: | (:arg obj:,) | :arg default:"""
    # bug mypy: obj is always returned as holder_t, except default, that can be anything
    return obj if (state := is_holder(obj, exclude)) else default if state is None else (obj,)     # type: ignore[return-value]


def as_holder_stated(obj: mb_holder_t[_T], default=(), exclude: mb_holder_t[type] = ()
                     ) -> tuple[bool, holder_t[_T]]:
    """Returns obj if it is holder type, or make holder from obj, or pass default if obj is None.
    Return is_holder() state before result
    :arg obj:       Target object or objects for cast
    :arg default:   Any object that will be returned if :arg obj: is None
    :arg exclude:   Type or types that must not be detected as holders
    :return:        bool, :arg obj: | (:arg obj:,) | :arg default:"""
    # bug mypy: obj is always returned as holder_t, except default, that can be anything
    return (st := is_holder(obj, exclude)), obj if st else default if st is None else (obj,)       # type: ignore[return-value]


def as_dict(objs: holder_t, keys: holder_t | Callable = enumerate, strict=False) -> dict:
    """Returns dict from objs if it is Mapping type or process by keys func or zip keys with objs
    :arg objs:      Target objects for cast
    :arg keys:      Used only if :arg objs: is not Mapping, as func(:arg objs:) or as dict keys
    :arg strict:    Used only if :arg keys: used, and it is not Callable, as zip keyword
    :return:        dict(:arg objs: | :arg keys:(:arg objs:) | zip(:arg keys:, :arg objs:,
                    strict=:arg strict:))"""
    s = isinstance(objs, Mapping)
    return dict(objs if s else keys(objs) if callable(keys) else zip(keys, objs, strict=strict))


def as_dict_stated(objs: holder_t, keys: holder_t | Callable = enumerate, strict=False
                   ) -> tuple[bool, dict]:
    """Returns dict from objs if it is Mapping type or process by keys func or zip keys with objs
    Return isinstance(objs, Mapping) state before result
    :arg objs:      Target objects for cast
    :arg keys:      Used only if :arg objs: is not Mapping, as func(:arg objs:) or as dict keys
    :arg strict:    Used only if :arg keys: used, and it is not Callable, as zip keyword
    :return:        bool, dict(:arg objs: | :arg keys:(:arg objs:) | zip(:arg keys:,
                    :arg objs:, strict=:arg strict:))"""
    s = isinstance(objs, Mapping)
    return s, dict(objs if s else keys(objs) if callable(keys) else zip(keys, objs, strict=strict))


# Common


def safe(func: Callable, /, *args, _res_: Any = _UNIQUE, _exc_: Any = _UNIQUE, **kwargs):
    """Safe function execution, return result or exception object, if it raised.
    Optional result and exception handlers or fillers could be provided (repr, 'some str', etc.)
    :arg func:      Target function for safe call
    :arg args:      Positional arguments for :arg func:
    :arg _res_:     Used on :arg func: result if Callable provided, or returned instead of result
    :arg _exc_:     Used on exception if Callable provided, or returned instead of exception
    :arg kwargs:    Keyword arguments for :arg func:
    :return:        Handled or unhandled :arg func: result or exception"""
    try:
        result = func(*args, **kwargs)
        return result if _res_ is _UNIQUE else _res_(result) if callable(_res_) else _res_
    except Exception as exc:
        return exc if _exc_ is _UNIQUE else _exc_(exc) if callable(_exc_) else _exc_


def with_type(obj, **kwargs) -> str:
    """Adds type name to object representation with additional information, if needed
    :arg obj:       Target for type and optional details
    :arg kwargs:    Keyword arguments for optional details about :arg obj:
    :return:        Formatted string with :arg obj: name or repr, type, and optional details"""
    obj_t = type(obj).__name__
    obj = obj.__name__ if isinstance(obj, type) else repr(obj)
    if not kwargs:
        return f'{obj} ({obj_t})'
    kwargs = {k: repr(v) for k, v in kwargs.items()}
    kwargs = kwargs | {'type': obj_t} if 'type' in kwargs else {'type': obj_t} | kwargs
    return f"{obj} ({', '.join(fmt_dict(kwargs, value_func=str))})"


# Formatters


def fmt_dict(obj: Mapping, key_func=str, sep='=', value_func=repr) -> tuple[str, ...]:
    """Format dict data to tuple of str per item by customizable formatting
    :arg obj:           Target mapping for formatting
    :arg key_func:      Function for keys handling
    :arg sep:           String separator between key and value
    :arg value_func:    Function for values handling
    :return:            Formatted strings tuple of each element"""
    return tuple(f'{key_func(k)}{sep}{value_func(v)}' for k, v in obj.items())


def fmt_obj_errors(obj, errors: holder_t[ItemError], exists: bool, holder: bool, mapping: bool,
                   result=False, result_name='result', key_handler=repr, kv_sep='='
                   ) -> tuple[str, ...]:
    """Format obj errors (ItemError objects) if they exist, or add obj details only
    :arg obj:           Target object for formatting, if no :arg errors: provided
    :arg errors:        Target errors list for formatting
    :arg exists:        [Formatter switch] Errors list handling
    :arg holder:        [Formatter switch] is_holder(:arg obj:) result
    :arg mapping:       [Formatter switch] isinstance(:arg obj:, Mapping) result
    :arg result:        Add error(s) result to formatted info
    :arg result_name:   :arg result: key name for not holder or mapping formatters
    :arg key_handler:   Key formatting function for mapping formatter
    :arg kv_sep:        Key-value separator for mapping formatter
    :return:            Formatted strings tuple from :arg errors: or :arg obj:"""
    if exists and errors:
        rn = result_name
        if not holder:
            error = next(x for x in errors)
            return with_type(error.value, **({rn: error.result} if result else {})),
        if mapping:
            return tuple(f'{key_handler(k)}{kv_sep}{with_type(v, **({rn: r} if result else {}))}'
                         for k, v, r in errors)
        return tuple(f'{with_type(v)} at pos {i}' + (f' ({r})' if result else '')
                     for i, v, r in errors)
    return with_type(obj),


def fmt_name(obj: Sized, item_name='item', default=_UNIQUE) -> str:
    """Format name depending only on the obj size - singular or plural
    :arg obj:       Target sized object for name formatting
    :arg item_name: Base item name (without 's' postfix)
    :arg default:   Override item name if no objects provided (by default :arg item_name: + 's')
    :return:        Formatted name"""
    if cnt := len(obj):
        return f'{item_name}{"s" if item_name and cnt > 1 else ""}'
    elif default == _UNIQUE:
        return f'{item_name}s'
    else:
        return str(default)


def fmt_exc(input_exc: tuple, msg='', default_exc_t: type[Exception] = Exception, *args, **kwargs
            ) -> InputError | Exception:
    """Format InputError (if input_exc provided) or default exception
    :arg input_exc:     InputError args tuple: (func_name: str, *items: str, kwargs: dict)
    :arg msg:           Exception message
    :arg default_exc_t: Exception type, used if :arg input_exc: is empty
    :arg args:          InputError or default exception positional arguments
    :arg kwargs:        InputError keyword arguments used as InputError result in default exception
    :return:            Formatted InputError or :arg default_exc_t: exception"""
    if input_exc:
        name, *params, in_kw = (input_exc if isinstance(input_exc[-1], dict) else (*input_exc, {}))
        return InputError(*params, msg=msg, func_name=name, args=args, **in_kw | kwargs | in_kw)

    if kwargs:
        msg = InputError(msg=msg, **kwargs).args[0]
    return default_exc_t(msg, *args) if msg else default_exc_t(*args)


# Split


def split(items: Iterable, condition: Callable = bool, func: Callable | None = None, *,  # noqa
          unpack=False, safely=False, modify=False, as_dicts=False,
          cond_key: bool | None = None, cond_value: bool | None = None, cond_invert=False
          ) -> ValidWrong:
    """Split items to valid and wrong iterables by condition
    Each item can be unpacked, safely called and/or modified by provided func
    Key (or index) and/or value can be provided as condition parameter(s) (default: value only)
    If provided only cond_key or only cond_value - another parameter will be in inverted state
    If unpack enabled, but item is not iterable - unpack will be skipped!
    :arg items:         Target objects for split
    :arg condition:     Split function, bool (default) means that True - Valid, False - Wrong
    :arg func:          Modify function that called with each item as positional argument
    :arg unpack:        Unpack item for :arg func: call with multiple positional arguments
    :arg safely:        Safe call :arg func:, at exception - item placed in Wrong
    :arg modify:        :arg func: call results used in ValidWrong, instead of :arg items:
    :arg as_dicts:      Fill ValidWrong by dicts, even if not dict provided (indexes used as keys)
    :arg cond_key:      Add item key (or index) to condition positional arguments
    :arg cond_value:    Add item value to condition positional arguments (default: True)
    :arg cond_invert:   Invert :arg condition: bool result to swap Valid and Wrong
    :return:            ValidWrong instance with filled valid, wrong and errors attributes
    :raise InputError:  When input parameters has wrong data or used not correct"""
    if not cond_key and cond_value is None:
        cond_value = True
    elif not cond_value and cond_key is None:
        cond_key = True
    elif not cond_key and not cond_value:
        raise fmt_exc(('split()', 'cond_key', 'cond_value'),
                      must_be='at least one True or not filled',
                      received=f'{cond_key = }, {cond_value = }')

    valid, wrong, errors = {}, {}, []
    mapping, named = as_dict_stated(items)
    for k, raw_item in named.items():
        args = as_holder(raw_item, default=(None,)) if unpack else (raw_item,)
        item = raw_item if func is None else safe(func, *args) if safely else func(*args)
        cond_args = [x for x, state in ((k, cond_key), (item, cond_value)) if state]
        result = item if modify else raw_item
        if safely and is_exception(item) or bool(item := condition(*cond_args)) == cond_invert:
            wrong[k] = result
            errors.append(ItemError(k, raw_item, item))
        else:
            valid[k] = result

    # Return result items depending on the source items type
    if as_dicts or mapping:
        return ValidWrong(valid, wrong, errors)
    return ValidWrong(tuple(valid.values()), tuple(wrong.values()), errors)


# Joins


def join(*items, sep=', ', typecast=True, skip_false=True) -> str:
    """Advanced str.join() method with str typecast and skip false-values possibilities
    :arg items:         Target items to join
    :arg sep:           Items separator
    :arg typecast:      Cast each item from :arg items: to str
    :arg skip_false:    Skip each item from :arg items: if it False at bool check
    :return:            Joined string"""
    if skip_false:
        items = tuple(filter(bool, items))
    if typecast:
        items = tuple(map(str, items))
    return sep.join(items)


def sentence(*items, sep=' ', typecast=True, skip_false=True) -> str:
    """Make a single sentence from provided items (capitalize first letter in result)
    :arg items:         Target items to join (mostly words or phrases)
    :arg sep:           Items separator
    :arg typecast:      Cast each item from :arg args: to str
    :arg skip_false:    Skip each item from :arg args: if it False at bool check
    :return:            Joined sentence"""
    phrase = join(*items, sep=sep, typecast=typecast, skip_false=skip_false)
    return f'{phrase[0].upper()}{phrase[1:]}' if phrase else ''


def sentences(*items, sep='. ', typecast=True, skip_false=True) -> str:
    """Make a multiple sentences from provided items (capitalize first letter in each item)
    :arg items:         Target items to join (mostly finished sentences)
    :arg sep:           Items separator
    :arg typecast:      Cast each item from :arg args: to str
    :arg skip_false:    Skip each item from :arg args: if it False at bool check
    :return:            Joined sentences"""
    phrases = tuple(sentence(x, typecast=typecast, skip_false=skip_false) for x in items)
    return join(*phrases, sep=sep, typecast=typecast, skip_false=skip_false)


# Data checks


def check_input(provided: Any | None, needed: Any | None, item_name='Item', template=_TEMPL_INPUT,
                input_exc=()) -> bool:
    """Check provided input correctness. Error if provided XOR needed (None == False, Any == True)
    :arg provided:  Target object to check
    :arg needed:    Target object to check with
    :arg item_name: Object name for error message
    :arg template:  String with 3 placeholders: :arg item_name:, 'not' provided, 'not' needed
    :arg input_exc: InputError args tuple: (func_name: str, *items: str, kwargs: dict)
    :return:        False if provided is None else True"""
    if (is_provided := (provided is not None)) != (needed is not None):
        args = (' not', '') if is_provided else ('', ' not')
        msg = sentence(template.format(item_name, *args).lstrip())
        raise fmt_exc(input_exc, msg, CheckValueError)
    return is_provided


def _fmt_template(template, items, item_name, item_func, sep, input_exc=()) -> str:
    msg = sep.join(map(item_func, items))
    match template.count('{'):
        case 0: return template + msg
        case 1: return template.format(fmt_name(items, item_name)) + msg
        case 2: return template.format(fmt_name(items, item_name), msg)
        case _: raise fmt_exc(input_exc, must_be='not more than 2 data places',
                              received=repr(template))


def _items_out(msg1, msg2, provided, as_text, input_exc, sep='. ', **kwargs) -> holder_t | str:
    if msg := sentences(msg1, msg2, sep=sep, typecast=False) if msg2 else msg1:
        exc = fmt_exc(input_exc, msg, CheckValueError, **kwargs)
        if as_text:
            return str(exc)
        raise exc
    return msg if as_text else provided


def _add_info(msg, provided, expected, item_func):
    return {'must_be': f"{msg} expected ({', '.join(map(item_func, expected))})",
            'received': f": {', '.join(map(item_func, provided))}"}


def check_extra(provided: holder_t, expected: holder_t, item_name='item', item_func=repr, *,
                item_sep=', ', as_text=False, template=_TEMPL_EXTRA, input_exc=(), **kwargs
                ) -> holder_t | str:
    """Check for not exists items provided (if all provided is expected)
    :arg provided:  Target objects to check
    :arg expected:  Target objects to check with
    :arg item_name: Object name for error message
    :arg item_func: Function to show item information for error message
    :arg item_sep:  Items separator for error message
    :arg as_text:   Not raise exception, return formatted str
    :arg template:  String with 0-2 placeholders: formatted item_name, wrong items message
    :arg input_exc: InputError args tuple: (func_name: str, *items: str, kwargs: dict)
    :arg kwargs:    InputError additional keyword arguments
    :return:        :arg provided: | str (if :arg as_text:)"""
    if msg := [x for x in provided if x not in expected] or '':
        msg = _fmt_template(template, msg, item_name, item_func, item_sep, _IE_CE__T)
        kwargs = _add_info(_CE, provided, expected, item_func) | kwargs
    return _items_out(msg, '', provided, as_text, input_exc, **kwargs)


def check_absent(provided: holder_t, expected: holder_t, item_name='item', item_func=repr, *,
                 item_sep=', ', as_text=False, template=_TEMPL_ABSENT, input_exc=(), **kwargs
                 ) -> holder_t | str:
    """Check for not enough items provided (if all expected is provided)
    :arg provided:  Target objects to check
    :arg expected:  Target objects to check with
    :arg item_name: Object name for error message
    :arg item_func: Function to show item information for error message
    :arg item_sep:  Items separator for error message
    :arg as_text:   Not raise exception, return formatted str
    :arg template:  String with 0-2 placeholders: formatted item_name, wrong items message
    :arg input_exc: InputError args tuple: (func_name: str, *items: str, kwargs: dict)
    :arg kwargs:    InputError additional keyword arguments
    :return:        :arg provided: | str (if :arg as_text:)"""
    if msg := [x for x in expected if x not in provided] or '':
        msg = _fmt_template(template, msg, item_name, item_func, item_sep, _IE_CA__T)
        kwargs = _add_info(_CA, provided, expected, item_func) | kwargs
    return _items_out(msg, '', provided, as_text, input_exc, **kwargs)


def check_items(provided: holder_t, expected: holder_t, item_name='item', item_func=repr, *,
                item_sep=', ', check_sep='. ', as_text=False, input_exc=(),
                extra=True, extra_template=_TEMPL_EXTRA,
                absent=True, absent_template=_TEMPL_ABSENT, **kwargs) -> holder_t | str:
    """Check for not enough and not exists items provided with customizable output
    Both checks can be disabled by absent and extra keywords and each can have custom header
    :arg provided:          Target objects to check
    :arg expected:          Target objects to check with
    :arg item_name:         Object name for error message
    :arg item_func:         Function to show item information for error message
    :arg item_sep:          Items separator for error message
    :arg check_sep:         Checks separator for error message
    :arg as_text:           Not raise exception, return formatted str
    :arg input_exc:         InputError args tuple: (func_name: str, *items: str, kwargs: dict)
    :arg extra:             Extra check state
    :arg extra_template:    String with 0-2 placeholders: formatted item_name, wrong items message
    :arg absent:            Absent check state
    :arg absent_template:   String with 0-2 placeholders: formatted item_name, wrong items message
    :arg kwargs:            InputError additional keyword arguments
    :return:                :arg provided: | str (if :arg as_text:)"""
    msg1, msg2 = ('', '')
    if extra and (items := [x for x in provided if x not in expected]):
        msg1 = _fmt_template(extra_template, items, item_name, item_func, item_sep, _IE_CI_ET)
    if absent and (items := [x for x in expected if x not in provided]):
        msg2 = _fmt_template(absent_template, items, item_name, item_func, item_sep, _IE_CI_AT)
    if msg1 or msg2:
        msg_part = _CI if extra and absent else _CE if extra else _CA
        kwargs = _add_info(msg_part, provided, expected, item_func) | kwargs
    return _items_out(msg1, msg2, provided, as_text, input_exc, check_sep, **kwargs)


def check_lengths(provided: Sequence, expected: Sequence, item_name='value', item_func=repr, *,
                  item_sep=', ', as_text=False, input_exc=(),
                  extra=True, extra_template=_TEMPL_EXTRA,
                  absent=True, absent_template=_TEMPL_ABSENT, **kwargs):
    """Check for length equality of provided and expected with customizable output
    Both checks can be disabled by absent and extra keywords and each can have custom header
    :arg provided:          Target objects sequence to check
    :arg expected:          Target objects sequence to check with
    :arg item_name:         Object name for error message
    :arg item_func:         Function to show item information for error message
    :arg item_sep:          Items separator for error message
    :arg as_text:           Not raise exception, return formatted str
    :arg input_exc:         InputError args tuple: (func_name: str, *items: str, kwargs: dict)
    :arg extra:             Extra check state
    :arg extra_template:    String with 0-2 placeholders: formatted item_name, wrong items message
    :arg absent:            Absent check state
    :arg absent_template:   String with 0-2 placeholders: formatted item_name, wrong items message
    :arg kwargs:            InputError additional keyword arguments
    :return:                :arg provided: | str (if :arg as_text:)"""
    msg = ''
    if (pl := len(provided)) != (nl := len(expected)):
        state, template, obj, i = ((extra, extra_template, provided, nl) if pl > nl else
                                   (absent, absent_template, expected, pl))
        if state:
            msg = _fmt_template(template, obj[i:], item_name, item_func, item_sep, _IE_CL__T)
            kwargs = {'must_be': f'{nl} {fmt_name(expected, item_name, f"{item_name}s")} long',
                      'received': str(pl)} | kwargs
    return _items_out(msg, '', provided, as_text, input_exc, **kwargs)


def check_type(obj: object, obj_t: mb_holder_t[type], typecast=False, name='', obj_t_check=True,
               input_exc=(), raw=False, *raw_args):
    """Check object type(s), with optional typecast if other type provided, dicts NOT supported
    :arg obj:               Target object to check
    :arg obj_t:             Target object type or types to check with
    :arg typecast:          :arg obj: type casting to :arg obj_t: (if wrong type)
    :arg name:              :arg obj: name ('object', 'item', etc.) for error message
    :arg obj_t_check:       Check :arg obj_t: that types provided
    :arg input_exc:         InputError args tuple: (func_name: str, *items: str, kwargs: dict)
    :arg raw:               Return not raised exception at error, with not formatted parts in args
    :arg raw_args:          Additional args before not formatted parts in args (if :arg raw:)
    :return:                :arg obj: | typecast-ed :arg obj: (if :arg typecast:) | CheckTypeError
    :raise InputError:      If wrong arguments provided
    :raise InputError:      If check failed and filled :arg input_exc: provided (upper-level error)
    :raise CheckTypeError:  If check failed and :arg input_exc: not (or empty) provided"""
    # Check simple
    # bug mypy: valid type or types for isinstance
    if isinstance(obj, obj_types := _types(obj_t, 'check_type()') if obj_t_check else obj_t):       # type: ignore[arg-type]
        return obj

    # Check with typecast if enabled
    error = ''
    obj_types = as_holder(obj_types)
    if typecast:
        for obj_type in obj_types:
            if isinstance(result := safe(obj_type, obj), obj_type):
                return result

            error += f', typecast to {obj_type.__name__}: {result!r}'
            if not isinstance(result, Exception):
                error += f' ({type(obj).__name__})'

    # Format error
    name = sentence(f'{name} ') if name else ''
    must_be = f'{" or ".join(x.__name__ for x in obj_types)} {fmt_name(tuple(obj_types), "type")}'
    msg = f"{name}{with_type(obj)} must be {must_be}{error}"
    if raw:
        return CheckTypeError(*raw_args, obj, obj_t, msg, name, must_be, error)
    raise fmt_exc(input_exc, msg, CheckTypeError)


def _build_ct_ie_kw(no_info):
    return {
        'input_exc': ('check_types()', 'obj', {'must_be': '', 'received': ''} if no_info else {}),
        'extra_template': "Extra {} (without type): ",
        'absent_template': "Absent {} (type provided): "}


_CT_IE_MAPS = _build_ct_ie_kw(True)
_CT_IE_PAIRS = _build_ct_ie_kw(False)


def check_types(obj: mb_holder_t[object], obj_t: mb_holder_t[type], typecast=False, item_name='',
                *, one_obj=False, pairs=False, strict=True, obj_t_check=True, input_exc=()):
    """Check object(s) type(s), with optional typecast if other type provided, dicts supported
    :arg obj:               Target object or objects to check
    :arg obj_t:             Target object type or types to check with
    :arg typecast:          :arg obj: type casting to :arg obj_t: (if wrong type)
    :arg item_name:         Common item name ('object', 'item', etc.) for error message
    :arg one_obj:           Check :arg obj: as single object, even if any holder type provided
    :arg pairs:             Zip :arg obj: and :arg obj_t: for pairs check (must be strict lengths)
    :arg strict:            At :arg pairs: or both mappings detect :arg obj: absent keys/values
    :arg obj_t_check:       Check :arg obj_t: that types provided
    :arg input_exc:         InputError args tuple: (func_name: str, *items: str, kwargs: dict)
    :return:                :arg obj: | typecast-ed :arg obj: (if :arg typecast:) | CheckTypeError
    :raise InputError:      If wrong arguments provided
    :raise InputError:      If check failed and filled :arg input_exc: provided (upper-level error)
    :raise CheckTypeError:  If check failed and :arg input_exc: not (or empty) provided"""
    # Check mutually exclusive input parameters
    if one_obj and pairs:
        raise fmt_exc(('check_types()', 'one_obj', 'pairs'),
                      must_be='not more than one True', received='both')

    # Check input obj
    obj_is_holder, objects = (False, (obj,)) if one_obj else as_holder_stated(obj)
    if not objects or any(x is None for x in objects):
        raise fmt_exc(('check_types()', 'obj'), must_be='one or more objects without None',
                      received=f"{obj = !r}{'' if obj == objects else f' ({objects = !r})'}")

    # Check single object
    if not obj_is_holder:
        if obj_t_check:
            _types(obj_t, 'check_types()')
        return check_type(obj, obj_t, typecast, item_name, False, input_exc)

    # Prepare common part for datasets
    obj_types = _types(obj_t, 'check_types()') if obj_t_check else as_holder(obj_t)
    obj_t_mapping = isinstance(obj_t, Mapping)
    obj_mapping, named = as_dict_stated(objects)
    maps = obj_mapping and obj_t_mapping

    # Add args to check_type: typecast, name, obj_t_check, input_exc, raw
    add_args = (typecast, item_name, False, (), True)

    # Build dataset
    if maps:        # Value-type pairs by its names if both are mappings
        check_items(named, obj_types, absent=strict, item_name='key', **_CT_IE_MAPS)
        # bug mypy: obj_types is Mapping in that case, so it has get method
        dataset = [(v, obj_types.get(k), *add_args, k) for k, v in named.items()]                  # type: ignore[attr-defined]

    elif pairs:     # Value-type pairs by lengths if enabled
        # bug mypy: obj_types is Mapping in that case, so it has values method
        obj_t_vals = obj_types.values() if obj_t_mapping else obj_types                            # type: ignore[attr-defined]
        check_lengths(tuple(objects), obj_t_vals, absent=strict, item_name='value', **_CT_IE_PAIRS)
        dataset = [(v, t, *add_args, ki) for (ki, v), t in zip(named.items(), obj_t_vals)]

    else:           # Common type(s) for all values
        dataset = [(v, obj_types, *add_args, ki) for ki, v in named.items()]

    # Check multiple objects
    exceptions, valid = split(dataset, is_exception, check_type, unpack=True, modify=True)

    # Raise formatted error message if errors exists
    if exceptions:
        msg = f'Several {item_name or "object"}s'
        errors = [ItemError(*x.args[:2]) for x in exceptions]
        raw = exceptions[0].args

        # Format error(s)
        if len(exceptions) == 1:    # Single error - as single
            info = fmt_obj_errors(obj, errors, True, True, obj_mapping)
            msg = f'{raw[-3]}{info[0]} must be {raw[-2]}{raw[-1]}'

        elif maps or pairs:         # Several errors, separate type - as newline
            info = fmt_obj_errors(obj, errors, True, True, obj_mapping, False, '', str, ': ')
            msg += '\n\t'.join((' has a wrong type:',
                                *[f'{raw[-3]}{x} must be {e.args[-2]}{e.args[-1]}'
                                  for x, e in zip(info, exceptions, strict=True)]))

        else:                       # Several errors, common type(s) - as inline
            info = fmt_obj_errors(obj, errors, True, True, obj_mapping, False, '', repr, '=')
            result = ", ".join(f"{x}{e.args[-1]}" for x, e in zip(info, exceptions, strict=True))
            msg += f' are not {raw[-2]}: {result}'

        raise fmt_exc(input_exc, msg, CheckTypeError)

    # Return input (or typecast-ed) value
    if not typecast:
        return obj
    # note mypy: typecast is user selectable, so if an error occurs - it is considered as scheduled
    return type(obj)(zip((x[-1] for x in dataset), valid, strict=True) if obj_mapping else valid)   # type: ignore[call-arg]


# Decorators


def decorate_methods(decorator: Callable, exclude: mb_holder_t[str] | Callable = is_hidden):
    """Class decorator to apply provided decorator to non-excluded methods
    :arg decorator: Target decorator for methods
    :arg exclude:   Excluded from decoration class methods (default: hidden methods are excluded)
    :return:        Class with decorated methods"""
    if callable(exclude):
        excluded = exclude
    else:
        exclude = as_holder(exclude)

        def excluded(x):
            return x in exclude

    def decorate(cls):
        for name, attr in cls.__dict__.items():
            if not excluded(name) and callable(attr):
                setattr(cls, name, decorator(attr))
        return cls

    # Decorator is called only (usage without calling is useless and wrong)
    return decorate


def init_reraise(entity_name: str, *get_name_args, **get_name_kwargs):
    """Decorator for __init__ method (reraise basic error info at exception with InitError)
    :arg entity_name:       Class objects common name, for error message
    :arg get_name_args:     Class object GetName args, for error message
    :arg get_name_kwargs:   Class object GetName kwargs, for error message
    :return:                Decorated __init__ method
    :raise InitError:       If error in __init__ method occurred"""
    def init_decorator(__init__):
        def init_wrapper(self, *args, **kwargs):
            try:
                __init__(self, *args, **kwargs)
            except Exception as e:
                target_name = GetName(self, *get_name_args, **get_name_kwargs)
                view = ", ".join((*map(repr, args), *fmt_dict(kwargs)))
                msg = f'Cannot init {entity_name} {target_name!r} (self.__init__({view}))'
                raise InitError(msg) from e
        return init_wrapper

    # Decorator is not called - entity_name is class
    if not isinstance(entity_name, str) and not get_name_args and not get_name_kwargs:
        cls, entity_name = entity_name, 'class'
        return init_decorator(cls)

    # Decorator is called
    return init_decorator


def set_slots_defaults(field_names: mb_holder_t[str] = (),
                       field_func: Callable = _field_func_default,
                       fields_t: type | None = None):
    """@dataclass(slots=True) alternative, that allows set slots with provided default values
    :arg field_names:   Strict field name or names (if needed)
    :arg field_func:    Condition for getting fields from class attributes
    :arg fields_t:      Common fields type
    :return:            Decorated class with slots defaults
    :raise InputError:  If wrong arguments provided"""
    def decorator(cls: type):
        name = cls.__name__
        # bug mypy: mapping proxy is support '|' operand with dict
        base = type.__dict__ | {'__weakref__': None}                                                # type: ignore[operator]
        differ = {k: v for k, v in cls.__dict__.items() if k not in base or base[k] != v}
        condition = lambda k, v: k in field_names or k not in base and field_func(k, v)  # noqa
        fields, attrs = split(differ, cond_key=True, cond_value=True, condition=condition)

        types = {k: fields_t for k in fields} if fields_t else getattr(cls, '__annotations__', {})
        type_kw = {'__slots__': tuple(fields)} | ({'__annotations__': types} if types else {})

        def __repr__(self):
            return f'{name}({", ".join(f"{k}={getattr(self, k, None)}" for k in fields)})'

        def __eq__(self, other):
            return repr(self) == repr(other)

        def __init__(self, *args, **kwargs):
            # Input checks
            check_lengths(args, fields, absent=False, input_exc=(f'{name}()', '*args'))
            if kwargs:
                check_extra(kwargs, fields, input_exc=(f'{name}()', '**kwargs'))

            if args and kwargs:
                unfilled = tuple(fields)[len(args):]
                if left := [x for x in kwargs if x not in unfilled]:
                    raise fmt_exc((f'{name}()', '*args', '**kwargs'),
                                  f'Already provided item in args: {", ".join(left)}')

            if fields_t:
                if args:
                    check_types(args, fields_t, input_exc=(f'{name}()', '*args'))
                if kwargs:
                    check_types(kwargs, fields_t, input_exc=(f'{name}()', '**kwargs'))

            # Fill fields by defaults | args | kwargs
            if args:
                kwargs = dict(zip(fields, args)) | kwargs
            [_FORCE_SET(self, k, v) for k, v in (fields | kwargs).items()]

            # Call post init as in dataclass
            if post_init := attrs.get('__post_init__'):
                post_init(self)

        new_cls = type(cls.__name__, (), attrs | type_kw)
        # note mypy: skip static checks
        new_cls.__repr__ = __repr__                                                 # type: ignore[method-assign, assignment]
        new_cls.__init__ = __init__                                                 # type: ignore[misc]
        new_cls.__eq__ = __eq__                                                     # type: ignore[method-assign, assignment]
        return new_cls

    # Decorator is not called
    if isinstance(field_names, type) and field_func == _field_func_default and fields_t is None:
        _cls, field_names = field_names, ()
        return decorator(_cls)

    # Decorator is called with or without parameters
    if field_names:
        check_types(field_names, str, input_exc=('@set_slots_defaults()', 'field_names'))
        field_names = as_holder(field_names)
    if field_func != _field_func_default:
        # bug mypy: Special forms is not supported yet (https://github.com/python/mypy/issues/9773)
        check_type(field_func, Callable, input_exc=('@set_slots_defaults()', 'field_func'))         # type: ignore[arg-type]
    if fields_t:
        check_type(fields_t, type, input_exc=('@set_slots_defaults()', 'fields_t'))
    return decorator


# Getters


def get_cls_obj(obj: object | type) -> ClsObj:
    """Get class and object from target class or object, as NamedTuple with cls and obj attrs
    :arg obj:   Target object for getting
    :return:    NamedTuple with cls and obj attrs"""
    if obj is None:
        return ClsObj(None, None)
    elif isinstance(obj, type):
        return ClsObj(obj, None)
    return ClsObj(type(obj), obj)


def get_cls_attr(obj: object | type, attr: str):
    """Get class attribute from target class or object
    :arg obj:   Target object for getting
    :arg attr:  Class attribute name
    :return:    Class attribute value | None (if not exists)"""
    return None if (cls := get_cls_obj(obj).cls) is None else getattr(cls, attr)


def get_attrs(obj: object | type, skip_parent: int = 0, skip_child: int = 0, *,
              internal=False, dunder=False, ignored: Iterable[type] = (type, object),
              merge: Iterable[str] = ('__annotations__', '__slots__')) -> dict[str, Any]:
    """Get attributes by exploring method resolution order, with optional parent coerce
    By default merges __annotations__ dict and __slots__ tuple
    :arg obj:           Target object for getting
    :arg skip_parent:   Classes count starting from parent to skip
    :arg skip_child:    Classes count starting from child to skip
    :arg internal:      Include internal attrs (starting from '_', except __dunder__)
    :arg dunder:        Include __dunder__ attrs
    :arg ignored:       Ignored classes (default: type and object)
    :arg merge:         Merge provided methods values from several classes
    :return:            Dict with attributes
    :raise InputError:  If wrong arguments provided"""
    if obj is None:
        raise fmt_exc(('get_attrs()', 'obj'), must_be='not None', received='None')
    if ignored != (type, object) and ignored:
        check_types(ignored, type, input_exc=('get_attrs()', 'ignored'))

    # Prepare MRO
    obj_t = obj if (is_cls := isinstance(obj, type)) else type(obj)
    mro = [x for x in type.mro(obj_t) if x not in ignored]

    # Check for skip correctness
    if (parents := len(mro)) <= (skip_total := skip_parent + skip_child):
        if not parents:
            raise fmt_exc(('get_attrs()', 'obj'),
                          must_be='not ignored type', received=with_type(obj),
                          ignored_types=f': {", ".join(x.__name__ for x in ignored)}')
        raise fmt_exc(('get_attrs()', 'skip_parent', 'skip_child'),
                      must_be=f'less than {parents} skipped in total',
                      skipped=f': {skip_total} ({skip_parent = }, {skip_child = })')

    # Build filtered MRO from coerced MRO and from object (if not class provided) in first order
    mro_flt = [x.__dict__ for x in mro[skip_child:len(mro) - skip_parent]]
    if not is_cls:
        # bug mypy: Union[Any, Dict[Any, Any]]?..
        mro_flt.insert(0, getattr(obj, '__dict__',                                                  # type: ignore[arg-type]
                                  {k: v for k in obj.__dir__()
                                   if (v := getattr(obj, k, _UNIQUE)) is not _UNIQUE}))
    # bug mypy: Why MutableMapping?..
    coerced: ChainMap[str, Any] = ChainMap(*mro_flt)                                                # type: ignore[arg-type]

    # Filter hidden if needed
    if dunder and internal:
        result = dict(coerced)
    else:
        result = {k: v for k, v in coerced.items()
                  if (dunder or not is_dunder(k)) and (internal or not is_internal(k))}

    # Merge provided dicts or iterables
    for k in merge:
        if k in result and (attrs := [y for x in coerced.maps if is_holder(y := x.get(k))]):
            if isinstance(attrs[-1], Mapping):
                # bug mypy: Why MutableMapping?..
                result[k] = dict(ChainMap(*attrs))                                                  # type: ignore[arg-type]
            else:
                # bug mypy: Optional? Type[None]?..
                result[k] = type(attrs[-1])(dict.fromkeys(chain(*attrs[::-1])))                  # type: ignore[arg-type, misc]
    return result


class _GNMethod(str):
    # bug mypy: MappingProxyType as default dict arg
    def __new__(cls, first_or_cls, obj=_UNIQUE, attrs: dict = MappingProxyType({})):                # type: ignore[assignment]
        inst = str.__new__(cls, obj or first_or_cls if (pair := obj != _UNIQUE) else first_or_cls)
        inst.__dict__ |= attrs | (dict(zip(_CLS_OBJ, (first_or_cls, obj))) if pair else {})
        return inst


class _GNClassMethod:
    def __init__(self, decorated):
        self.func = decorated
        self.args = decorated.__code__.co_argcount - 1

    def __call__(self, target, *args):
        cls_args, obj_args = args, args
        if (received := len(args)) and received != self.args:
            if received != self.args * 2:
                args_names = self.func.__code__.co_varnames[1:self.args + 1]
                must_be = (f'{self.args} (same for both) or {self.args * 2} (separately) '
                           'provided for cls and obj') if self.args else 'no arguments'
                raise fmt_exc((f'GetName.{self.func.__code__.co_name}()', *args_names),
                              force_header=True, must_be=must_be,
                              received=f'{received}: {", ".join(map(repr, args))}')
            cls_args, obj_args = args[:self.args], args[self.args:]

        cls, obj = get_cls_obj(target)
        return _GNMethod('' if cls is None else self.func(cls, *cls_args),
                         '' if obj is None else self.func(obj, *obj_args))

    def __repr__(self):
        return f'GetName.{self.func.__code__.co_name}'


def _flt_std_name(target: object | type, name: str) -> str:
    return '' if get_cls_attr(target, '__qualname__') in name else name


@decorate_methods(_GNClassMethod)
class _GNMethods:
    def doc(self: Any) -> str:
        """Get first line in __doc__ attr as name"""
        return doc.split('\n')[0] if (doc := getattr(self, '__doc__', None)) else ''

    def code(self: Any) -> str:
        """Get __code__.co_name attr as name"""
        return getattr(co, 'co_name', '') if (co := getattr(self, '__code__', None)) else ''

    def attrs(self: Any, attrs: Iterable[str] = _GN_ATTRS) -> str:
        """Get first from default or provided attrs as name"""
        if attrs:
            if attrs != _GN_ATTRS:
                check_types(attrs, str)

            for attr in attrs:
                if result := getattr(self, attr, ''):
                    if result := safe(str, result, _exc_=''):
                        return result
        return ''

    def repr(self: Any) -> str:
        """Get __str__ attr as name"""
        return safe(self.__repr__, _res_=partial(_flt_std_name, self), _exc_='')

    def str(self: Any) -> str:
        """Get __repr__ attr as name"""
        return safe(self.__str__, _res_=partial(_flt_std_name, self), _exc_='')


_GN_METHODS = get_attrs(_GNMethods)
_GN_METHODS_EMPTY = {k: _GNMethod('', '') for k in _GN_METHODS}
_GN_POSSIBLE_PARAMS = {'possible_parameters': f': {", ".join(_GN_ORDER)}'}


@dataclass(slots=True)
class _GNMethodHolder:
    value: str
    state: bool
    args: tuple
    method: _GNClassMethod


class GetName(str, _GNMethods):
    """Get first available name from provided target using multiple configurable ways
    By default - only first of cls and obj names will be received (full=False)
    Order of get methods can be changed, set of all get methods names is not required
    Any get method can be enabled/disabled by bool ('{method}', '{method}_cls', '{method}_obj')
    Attrs get method ('attrs', 'attrs_cls', 'attrs_obj') can have names tuple instead of bool
    If None obj provided - 'none' arg value will be returned, as GetName (if str type)
    All get methods failed - 'unknown' arg value will be returned, as GetName (if str type)"""
    cls: _GNMethod
    obj: _GNMethod

    def __new__(cls, obj, doc=False, code=False, attrs: bool | tuple[holder_t[str]] = True,
                str=True, repr=True, *, full=False, order=_GN_ORDER, none='', unknown='',  # noqa
                **kwargs):
        """
        :arg obj:       Target object for getting
        :arg doc:       Enable cls and obj get method, first line in __doc__ attr as name
        :arg code:      Enable cls and obj get method, __code__.co_name attr as name
        :arg attrs:     Enable cls and obj get method, first from default or provided attrs as name
        :arg str:       Enable cls and obj get method, __str__ attr as name
        :arg repr:      Enable cls and obj get method, __repr__ attr as name
        :arg full:      Get all enabled methods and fill (default: only first in cls and obj)
        :arg order:     Get methods order, cls or obj required ('{method}_cls', '{method}_obj')
        :arg none:      Return value if :arg obj: is None, typecast-ed to GetName (if str type)
        :arg unknown:   Return value if all methods failed, typecast-ed to GetName (if str type)
        :arg kwargs:    Enable cls or obj get method separately ('{method}_cls', '{method}_obj')"""

        # Filter only methods states/args from internally used arguments
        left = {k: v for k, v in locals().items() if k not in _GN_INTERNAL}
        holders: dict[str, _GNMethodHolder] = {}
        for k, method in _GN_METHODS.items():
            value = cls._get_method_holder(k, method, left.pop(k))
            value2 = _GNMethodHolder(value.value, value.state, value.args, value.method)  # copy
            holders |= {f'{k}_cls': value, f'{k}_obj': value2}
        if left:
            raise InternalError(f'Found not used args in GetName with {obj=!r}: {left}')

        # Rewrite separately (cls/obj) provided methods states/args
        if kwargs:
            if wrongs := {k: v for k, v in kwargs.items() if k not in holders.keys()}:
                # bug mypy: unpacked keyword arguments is not a positional argument..
                raise fmt_exc(('GetName()', *wrongs.keys()), **_GN_POSSIBLE_PARAMS)                 # type: ignore[arg-type]
            for k, v in kwargs.items():
                holders[k] = cls._get_method_holder(k, holders[k].method, v)

        # Check order
        if order != _GN_ORDER:
            check_extra(order, _GN_ORDER, item_name='method', template='Not exists {}: ',
                        input_exc=('GetName()', 'order', {'must_be': ''} | _GN_POSSIBLE_PARAMS))

        # Return none if None target provided
        if obj is None:
            return cls._try_type_cast(none, full)

        # Get names (all or only first in cls and obj) by enabled methods in provided order
        first, first_cls_obj, left_set = '', dict.fromkeys(_CLS_OBJ, ''), set(_CLS_OBJ)
        targets = get_cls_obj(obj)
        if targets.obj is None:
            left_set.discard('obj')
        for method_name in order:
            if (cls_or_obj := method_name.rsplit('_', 1)[1]) in left_set:
                if (holder := holders[method_name]).state:
                    if name := holder.method.func(getattr(targets, cls_or_obj), *holder.args):
                        holder.value = name
                        if not first:
                            first = name
                        if not first_cls_obj[cls_or_obj]:
                            first_cls_obj[cls_or_obj] = name
                        if not full:
                            left_set.discard(cls_or_obj)
                            if not left_set:
                                break

        # Return unknown if no name found
        if not first:
            return cls._try_type_cast(unknown, full)

        # Fast names receive way (only first in cls and obj methods), without GetName instance fill
        if not full:
            methods = {k: '' for k in _GN_METHODS}
            # note mypy: that's planned
            return _GNMethod.__new__(cls, first, attrs=first_cls_obj | methods)                     # type: ignore[arg-type]

        # GetName instance fill by first cls and obj methods and each method separately
        methods = {k: _GNMethod(holders[f'{k}_cls'].value, holders[f'{k}_obj'].value)
                   for k in _GN_METHODS}
        # note mypy: that's planned
        return _GNMethod.__new__(cls, first, attrs=first_cls_obj | methods)                         # type: ignore[arg-type]

    @staticmethod
    def _get_method_holder(k, method, value) -> _GNMethodHolder:
        check_type(value, (bool, tuple) if method.args else bool, input_exc=('GetName()', k))
        return _GNMethodHolder('', bool(value), value if isinstance(value, tuple) else (), method)

    @classmethod
    def _try_type_cast(cls, value, full):
        if isinstance(value, str):
            attrs = _GN_METHODS_EMPTY if full else {}
            return _GNMethod.__new__(cls, value, attrs=attrs | dict.fromkeys(_CLS_OBJ, ''))  # noqa
        return value


# Uncategorized


class UID:
    """Unique ID instances used as filler for detecting by comparison"""
    __slots__ = ('name',)
    name: str
    exists: list[str] = []

    def __init__(self, name: str):
        """
        :arg name:  Unique name for ID"""
        if (name := str(name)) in self.exists:
            raise ValueError(f'{name!r} unique ID cannot be created, it already exists')
        self.exists.append(name)
        self.name = name

    def __repr__(self):
        return f'UID({self.name!r})'

    def __str__(self):
        return f'{self.name} ID'


class Locker:
    """Lock child class from attributes manipulations with internal unlock possibility
    Can be unlocked during active context manager, as it finished - class will be also locked"""
    __slots__ = ('_locker_state', '_locker_enter_state', '_locker_set_attr', '_locker_del_attr',
                 '_locker_ignored', '_locker_name')
    _locker_state: bool
    _locker_enter_state: bool
    _locker_set_attr: bool
    _locker_del_attr: bool
    _locker_ignored: tuple
    _locker_name: str

    def __new__(cls, *args, **kwargs):
        obj = object.__new__(cls)
        [_FORCE_SET(obj, *x) for x in zip(Locker.__slots__, (False, False, True, True, ()))]
        return obj

    def __init__(self, *ignored_attrs: str, set_attr=True, del_attr=True, name: str | None = None):
        """
        :arg ignored_attrs: Attributes names that will not be locked at all
        :arg set_attr:      Allow __set__ unlocked attributes
        :arg del_attr:      Allow __del__ unlocked attributes
        :arg name:          Set locker name for error message"""
        self._locker_ignored += ignored_attrs
        name = f'{GetName(self)!r} object' if name is None else str(name)
        _FORCE_SET(self, '_locker_name', name)
        _FORCE_SET(self, '_locker_set_attr', set_attr)
        _FORCE_SET(self, '_locker_del_attr', del_attr)
        self._locker_state = True

    @staticmethod
    def _get_exc_msg(is_set, allowed):
        if allowed:
            return is_set, 'is locked for changes'
        else:
            return is_set, f'does not support {"setting" if is_set else "deleting"} attributes'

    def _make_exc(self, is_set, msg, key, value=None):
        op, value = ('set', f', {value!r}') if is_set else ('del', '')
        return TypeError(f'{self._locker_name} {msg} (self.__{op}attr__({key!r}{value}))')

    def is_unlocked(self, key):
        """Get True if provided attribute is unlocked"""
        return not self._locker_state or key in self._locker_ignored

    def __setattr__(self, key, value):
        if key in _LOCKER_IGNORED or self._locker_set_attr and self.is_unlocked(key):
            return _FORCE_SET(self, key, value)
        raise self._make_exc(*self._get_exc_msg(True, self._locker_set_attr), key, value)

    def __delattr__(self, key):
        if not hasattr(self, key):  # msg as at set any new attrs in slotted class
            raise AttributeError(f'{self._locker_name} has no attribute {key!r}')
        if key in Locker.__slots__:
            raise self._make_exc(False, 'Locker attrs deletion is forbidden', key)
        if self._locker_del_attr and self.is_unlocked(key):
            return object.__delattr__(self, key)
        raise self._make_exc(*self._get_exc_msg(False, self._locker_del_attr), key)

    def __enter__(self):
        self._locker_enter_state, self._locker_state = self._locker_state, False
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._locker_enter_state:
            self._locker_state = True
