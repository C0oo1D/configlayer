from typing import Iterable
from functools import partial
from itertools import product

from configlayer import Field, Options
from configlayer.exceptions import CheckTypeError, OptionsCheckError, FieldError, InputError

from _utilities import raises, init
from _data import (TEMP_PATH, Config1, Config2, Config3, Config4, Lang1,
                   wrong_func, wrong_func_2, wrong_func_3, exp_strict, imp_strict)


def raises_init_lang(exceptions: Exception | Iterable[Exception], func, *args, **kwargs):
    raises((*init('language', (), func, *args, **kwargs),
            *init('config', exceptions, func, *args, **kwargs, group='Language')),
           func, *args, **kwargs)


def test_init():
    cust_opt = Options(revert_fails=True)
    TEMP_PATH.unlink(missing_ok=True)
    for data, field_keys, name, type_name, def_sect, opt, profiles, io, file in [
        (Config3(default_section='x', options=cust_opt), (*exp_strict, 'c2', 'c3'),
         'Gotcha', 'config', 'x', cust_opt, False, False, False),
        (Lang1(TEMP_PATH, profiles=True), ('some1', 'some2', 'another_one'),
         'Random', 'language', 'DEFAULT', Options(), True, True, True)
    ]:
        cfg = data.cfg
        assert cfg._data == data
        assert tuple(cfg._fields) == field_keys
        assert all(isinstance(x, Field) for x in cfg._fields.values())
        assert cfg._on_set == {}
        assert cfg.name == name
        assert cfg.type_name == type_name
        assert cfg.def_sect == def_sect
        assert cfg.options == opt
        assert cfg.version is None
        assert bool(cfg.profiles) == profiles
        assert bool(cfg.io) == io
        assert bool(cfg.file) == file


def test_repr_str():
    for cls, str1, str2 in (
            [Config1, "Config1.cfg", "'Config1' config support structure"],
            [Config2, "Config2.cfg", "'Valid fields' config support structure"],
            [Config3, "Config3.cfg", "'Gotcha' config support structure"],
            [Config4, "Config4.cfg", "'IO' config support structure"],
            [Lang1, "Lang1.cfg", "'Random' language support structure"]):
        obj = cls().cfg
        assert repr(obj) == str1
        assert str(obj) == str2

    Lang1().cfg.profiles.del_group('Language')


def test_change_attr():
    cfg = Config1().cfg
    obj_name = "'Config1' config support structure"
    raises(TypeError(f"{obj_name} is locked for changes (self.__setattr__('x', 1))"),
           setattr, cfg, 'x', 1)
    raises(TypeError(f"{obj_name} is locked for changes (self.__setattr__('fields', 2))"),
           setattr, cfg, 'fields', 2)

    assert cfg._locker_state
    with cfg:
        cfg.file = None
        raises(AttributeError("'ConfigSupport' object has no attribute 'some'"),
               setattr, cfg, 'some', 5)
    assert cfg._locker_state
    cfg._locker_state = False
    cfg.file = None
    with cfg:
        cfg.file = None
    assert not cfg._locker_state

    raises(AttributeError(f"{obj_name} has no attribute 'x'"), delattr, cfg, 'x')

    msg = f"{obj_name} does not support deleting attributes (self.__delattr__('_fields'))"
    raises(TypeError(msg), delattr, cfg, '_fields')

    msg = f"{obj_name} Locker attrs deletion is forbidden (self.__delattr__('_locker_state'))"
    raises(TypeError(msg), delattr, cfg, '_locker_state')


def test_on_set():
    result = []

    def log_arg(event, param, prev_value, curr_value):
        result.append(f'{event} {param}: {prev_value!r} -> {curr_value!r}')

    def log_kwarg(param, prev_value, curr_value, event=None):
        event = '' if event is None else str(event) + ' '
        result.append(f'{event}{param}: {prev_value!r} -> {curr_value!r}')

    data = Config1()
    data.cfg.add_on_set('1', None, True, log_arg, 'Global1')
    data.cfg.add_on_set('2', 'v_bool', True, log_arg, 'Single')
    data.cfg.add_on_set('3', 'v_str', True, log_kwarg)
    data.cfg.add_on_set('4', None, True, log_kwarg, event='Global2')
    data.cfg.add_on_set('5', 'v_bool', False, log_kwarg)
    data.cfg.add_on_set('6', 'v_str', False, log_kwarg, event='Single')

    data.v_int = 5
    assert result == ['Global1 v_int: 65535 -> 5', 'Global2 v_int: 65535 -> 5']

    result.clear()
    data.v_bool = True
    assert result == ['Global1 v_bool: False -> True', 'Single v_bool: False -> True',
                      'Global2 v_bool: False -> True', 'v_bool: False -> True']

    result.clear()
    data.v_str = '123'
    assert result == ['Global1 v_str: \'Some string\' -> \'123\'',
                      'v_str: \'Some string\' -> \'123\'',
                      'Global2 v_str: \'Some string\' -> \'123\'',
                      'Single v_str: \'Some string\' -> \'123\'']

    result.clear()
    data.v_int = 5
    assert result == ['Global1 v_int: 5 -> 5', 'Global2 v_int: 5 -> 5']

    result.clear()
    data.v_bool = True
    assert result == ['Global1 v_bool: True -> True', 'Single v_bool: True -> True',
                      'Global2 v_bool: True -> True']

    result.clear()
    data.v_str = '123'
    assert result == ['Global1 v_str: \'123\' -> \'123\'',
                      'v_str: \'123\' -> \'123\'',
                      'Global2 v_str: \'123\' -> \'123\'']

    msg = ("Provided wrong parameter to Config1.cfg.add_on_set(): field_name. "
           "Cannot add '7' handler, not exists field_name = 'not_exists'")
    raises(InputError(msg=msg), data.cfg.add_on_set, '7', 'not_exists', True, log_kwarg)

    msg = ("Provided wrong parameter to Config1.cfg.add_on_set(): name. "
           "Cannot add '6' handler, it already exists")
    raises(InputError(msg=msg), data.cfg.add_on_set, '6', None, True, log_kwarg)

    data.cfg.add_on_set('7', 'v_int', True, wrong_func)
    r_msg = "\nRevert option is disabled - field value is left changed"
    msg = ("on_set handlers errors:\n"
           "\t'7' handler (wrong_func): wrong_func() takes 1 positional argument but 3 were given")
    raises(FieldError('Set', 'Config1', 'v_int', 3, 5, reason=msg + r_msg, failed=False),
           setattr, data, 'v_int', 3)

    data.cfg.add_on_set('8', None, True, wrong_func_2)
    msg = ("on_set handlers errors:\n"
           "\t'7' handler (wrong_func): wrong_func() takes 1 positional argument but 3 were given"
           "\n\t'8' handler (wrong_func_2): Wrong func 2! ('v_int', 3, 5)")
    raises(FieldError('Set', 'Config1', 'v_int', 5, 3, reason=msg + r_msg, failed=False),
           setattr, data, 'v_int', 5)

    msg = ("on_set handlers errors:\n"
           "\t'8' handler (wrong_func_2): Wrong func 2! ('v_float', 3.1415, 0.0)")
    raises(FieldError('Set', 'Config1', 'v_float', 0.0, 3.1415, reason=msg + r_msg, failed=False),
           setattr, data, 'v_float', 0.0)

    raises(KeyError('9'), data.cfg.del_on_set, '9')

    assert tuple(data.cfg.get_on_set) == tuple('12345678')

    data.cfg.del_on_set('8')
    data.v_float = 3.1415

    data.cfg.del_on_set('7')
    data.v_int = 6

    [data.cfg.del_on_set(repr(i)) for i in range(6, 0, -1)]
    assert not data.cfg.get_on_set


def test_get_set():
    default_data = imp_strict | {'c2': 'c2', 'c3': 'c3'}
    data_s, data_p = Config3(), Config3(profiles=True)
    cfg_s, cfg_p = data_s.cfg, data_p.cfg

    def check(cfg, current, default, changed):
        assert cfg.get_data == default_data | current
        assert cfg.get_defaults == default_data | default
        assert cfg.get_factory_defaults == default_data

        assert {k: v.default for k, v in cfg.get_fields.items()} == default_data | default
        assert [k for k, v in cfg.get_changed.items() if v] == changed

        for (k, t), v in zip(cfg.get_types.items(), cfg.get_data.values(), strict=True):
            if t != (tv := type(v)):
                assert issubclass(tv, t)

    data_s.v_int = data_p.v_int = 255
    cfg_s.get_fields['v_int'].default = cfg_p.get_fields['v_int'].default = 32767
    check(cfg_s, {'v_int': 255}, {'v_int': 32767}, ['v_int'])
    check(cfg_p, {'v_int': 255}, {'v_int': 32767}, ['v_int'])

    data_s.v_int = data_p.v_int = 1024
    check(cfg_s, {'v_int': 1024}, {'v_int': 32767}, ['v_int'])
    check(cfg_p, {'v_int': 1024}, {'v_int': 1024}, [])

    cfg_s.set_fields({'v_int': 512, 'v_str': 's1'})
    cfg_p.set_fields({'v_int': 512, 'v_str': 's1'})
    cfg_s.set_defaults({'v_int': 127, 'v_str': 's2'})
    cfg_p.set_defaults({'v_int': 127, 'v_str': 's2'})
    check(cfg_s, {'v_int': 512, 'v_str': 's1'}, {'v_int': 127, 'v_str': 's2'}, ['v_str', 'v_int'])
    check(cfg_p, {'v_int': 127, 'v_str': 's2'}, {'v_int': 127, 'v_str': 's2'}, [])

    cfg_p.profiles.set('p1', {'v_bool': True})
    cfg_p.profiles.switch('p1')

    data_p.v_str = 'Some string'
    data_p.v_int = 8
    cfg_p.get_fields['v_int'].default = 65535
    check(cfg_p, {'v_bool': True, 'v_int': 8}, {'v_str': 's2'}, ['v_bool', 'v_str', 'v_int'])

    cfg_p.set_fields({'v_int': 32})
    cfg_p.set_defaults({'v_int': 64, 'v_str': 'Some string'})
    check(cfg_p, {'v_bool': True, 'v_int': 32}, {'v_int': 64}, ['v_bool', 'v_int'])

    exc_part = partial(InputError, 'fields', msg='Empty fields provided')
    raises(exc_part(func_name="Config3.cfg.set_fields()"), cfg_p.set_fields, {})
    raises(exc_part(func_name="Config3.cfg.set_defaults()"), cfg_p.set_defaults, {})


def test_options():
    options1 = Options()
    options2 = Options(True, typecast=True)
    options3 = Options(typecast=True, typecheck=True)
    assert options1 == options2 == options3

    msg_cast = "Type checking is disabled, type casting cannot be enabled"

    for args in product((True, False), repeat=3):
        check, cast, *_ = args

        errors = []
        if cast and not check:
            errors.append(msg_cast)

        if errors:
            raises(OptionsCheckError('. '.join(errors)), Options, *args)
        else:
            Config1(options=Options(*args))

    option = 'typecheck'
    msg = f"Set option {option!r} to False failed: {msg_cast}. Reverted to True successfully"
    raises(OptionsCheckError(msg), setattr, options1, option, False)
    assert options1.typecheck is True

    object.__setattr__(options1, option, False)
    option = 'revert_fails'
    msg2 = f"Some options changed in wrong way, check failed: {msg_cast}"
    msg = f"Set option {option!r} to True failed: {msg_cast}. Revert to False also failed: {msg2}"
    raises(OptionsCheckError(msg), setattr, options1, option, True)

    msg = 'Options accepting only booleans'
    raises(OptionsCheckError(msg), setattr, options1, option, 1)

    # No type check and cast
    config = Config1(options=Options(False, False))
    config.v_int = '5'
    assert config.v_int == '5'

    # Type check
    config = Config1(options=Options(True, False))
    raises(CheckTypeError("'5' (str) must be int type"), setattr, config, 'v_int', '5')

    # Type check and cast
    config = Config1()
    config.v_int = '5'
    assert config.v_int == 5

    # Clear at default
    config = Config1()
    config.v_int = 32767
    assert config.v_int == 32767
    assert [k for k, v in config.cfg.get_changed.items() if v] == ['v_int']
    config.v_int = 65535
    assert config.v_int == 65535
    assert [k for k, v in config.cfg.get_changed.items() if v] == []

    # Revert at on_set error and not
    revert_disabled = "\nRevert option is disabled - field value is left changed"
    revert_details = ("\nRevert completed, but on_set handlers errors:\n"
                      "\t'2' handler (wrong_func_2): Wrong func 2! ('v_int', 32767, 65535)")
    for state, result1, result2 in (True, 65535, 'Some string'), (False, 32767, 'other'):
        config = Config1(options=Options(revert_fails=state))
        config.cfg.add_on_set('2', 'v_int', True, wrong_func_2)
        config.cfg.add_on_set('3', 'v_str', True, wrong_func_3)

        msg = ("on_set handlers errors:\n"
               "\t'2' handler (wrong_func_2): Wrong func 2! ('v_int', 65535, 32767)")
        msg += revert_details if state else revert_disabled
        raises(FieldError('Set', 'Config1', 'v_int', 32767, 65535, reason=msg, failed=False),
               setattr, config, 'v_int', 32767)
        assert config.v_int == result1

        msg = ("on_set handlers errors:\n"
               "\t'3' handler (wrong_func_3): Cannot change value ('v_str', 'Some string', "
               "'other')")
        msg += "\nRevert completed" if state else revert_disabled
        raises(FieldError('Set', 'Config1', 'v_str', 'other', 'Some string', reason=msg,
                          failed=False),
               setattr, config, 'v_str', 'other')
        assert config.v_str == result2
