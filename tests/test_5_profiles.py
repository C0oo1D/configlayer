from types import MappingProxyType
from functools import partial

from configlayer.constants import DEFAULT_SECTION
from configlayer.exceptions import InputError, ProfilesError

from _utilities import raises
from _data import Config1, Config1Alias, Config2, Config3, Config4, Lang1, exp_strict


def test_init():
    cfg = Config1(profiles=True).cfg
    profiles = cfg.profiles
    assert not profiles._groups

    profiles1 = Config1(profiles=True, group='1').cfg.profiles
    assert profiles._groups == {'1': [profiles1]}

    profiles2 = Config1(profiles=True, group='2').cfg.profiles
    assert profiles._groups == {'1': [profiles1], '2': [profiles2]}

    profiles3 = Config1(profiles=True, group='1').cfg.profiles
    assert profiles._groups == {'1': [profiles1, profiles3], '2': [profiles2]}

    profile_name = 'some profile'
    profiles_dict = {profile_name: tuple(cfg.get_defaults.values())}
    profiles3.switch(profile_name, True)
    assert profiles1.active == profiles3.active == profile_name
    assert dict(profiles1.get) == dict(profiles3.get) == profiles_dict
    assert profiles2.active == DEFAULT_SECTION
    assert dict(profiles2.get) == {}

    profiles4 = Config1(profiles=True, group='1').cfg.profiles
    assert profiles1.active == profiles3.active == profiles4.active == profile_name
    assert dict(profiles1.get) == dict(profiles3.get) == dict(profiles4.get) == profiles_dict

    profiles._groups.clear()


def test_repr_str():
    for cls, str1, str2 in (
            [Config1, "Config1.cfg.profiles", "'Config1' config profiles support structure"],
            [Config2, "Config2.cfg.profiles", "'Valid fields' config profiles support structure"],
            [Config3, "Config3.cfg.profiles", "'Gotcha' config profiles support structure"],
            [Config4, "Config4.cfg.profiles", "'IO' config profiles support structure"],
            [Lang1, "Lang1.cfg.profiles", "'Random' language profiles support structure"]):
        obj = cls(profiles=True).cfg.profiles
        assert repr(obj) == str1
        assert str(obj) == str2

    Lang1().cfg.profiles.del_group('Language')


def test_contains():
    profiles = Config1(profiles=True).cfg.profiles
    profiles.set('name1')
    assert '1' not in profiles
    assert 'name1' in profiles


def test_getitem():
    cfg = Config1(profiles=True).cfg
    profiles = cfg.profiles
    name = 'some profile'
    default_values = tuple(cfg.get_defaults.values())

    assert profiles[DEFAULT_SECTION] == default_values
    raises(KeyError(name), profiles.__getitem__, name)
    profiles.set(name)
    assert profiles[name] == default_values


def test_delitem():
    def delete(key):
        del profiles[key]

    profiles = Config1(profiles=True).cfg.profiles

    raises(KeyError(DEFAULT_SECTION), delete, DEFAULT_SECTION)

    name1, name2, name3, name4 = 'name1', 'name2', 'name3', 'name4'
    for name in name1, name2, name3, name4:
        profiles.set(name)
    assert profiles.active == DEFAULT_SECTION

    del profiles[name4]
    assert profiles.active == DEFAULT_SECTION

    profiles.switch(name2)
    del profiles[name2]
    assert profiles.active == name1

    del profiles[name1]
    assert profiles.active == name3

    del profiles[name3]
    assert profiles.active == DEFAULT_SECTION


def test_clear():
    cfg = Config1(profiles=True).cfg
    profiles = cfg.profiles
    assert not profiles.get
    assert profiles.active == cfg.def_sect

    # Clear at default profile
    profiles.set('')
    assert profiles.get
    assert profiles.active == cfg.def_sect

    profiles.clear()
    assert not profiles.get
    assert profiles.active == cfg.def_sect

    # Clear at custom profile
    profiles.switch('', add=True)
    assert profiles.get
    assert profiles.active == '' != cfg.def_sect

    profiles.clear()
    assert not profiles.get
    assert profiles.active == cfg.def_sect


def test_get():
    cfg = Config1(profiles=True).cfg
    profiles = cfg.profiles
    assert isinstance(profiles.get, MappingProxyType)
    assert dict(profiles.get) == {}

    profiles.set('name1', {'v_str': 'some'}, defaults=False)
    assert dict(profiles.get) == {'name1': {'v_str': 'some'}}

    profiles.set('name2')
    assert dict(profiles.get) == {'name1': {'v_str': 'some'},
                                  'name2': tuple(cfg.get_defaults.values())}


def test_set():
    def build(p_name, exc):
        if isinstance(exc, InputError):
            return exc
        return ProfilesError(f"Cannot set '{p_name}' profile to 'Config1' config"), exc

    p_cnt = len(exp_strict)

    cfg = Config1(profiles=True).cfg
    profiles = cfg.profiles
    def_d = cfg.get_defaults
    def_t = tuple(def_d.values())

    def fmt(value, default=None, ret_val_t: type = tuple):
        if isinstance(value, dict):
            ret_val = (def_d if default is None else default) | value
            return tuple(ret_val.values()) if ret_val_t == tuple else ret_val
        else:
            return (*value, *def_t[len(value):]) if default is None else default

    dft = DEFAULT_SECTION
    exp = ', '.join(def_d)

    ie = partial(InputError, 'data', func_name='Config1.cfg.profiles.set()')
    exc1 = ie(msg="Cannot overwrite profile defaults with empty data")
    exc2 = ie(msg="Cannot set profile with empty data and disabled defaults")
    exc3 = ie(msg="Several objects has a wrong type:\n"
                  "\tv_bool: 1 (int) must be bool type\n"
                  "\tv_str: 2 (int) must be str type")
    exc4 = ie(msg="'v_int'='6' (str) must be int type")
    exc5 = ie(msg="Several objects has a wrong type:\n"
                  "\tv_bool: 0 (int) must be bool type\n"
                  "\tv_str: 1 (int) must be str type\n"
                  "\tv_float: 3 (int) must be float type\n"
                  "\tv_bytes: 4 (int) must be bytes type\n"
                  "\tv_tuple: 5 (int) must be tuple type\n"
                  "\tv_list: 6 (int) must be list type\n"
                  "\tv_set: 7 (int) must be set type\n"
                  "\tv_dict: 8 (int) must be dict type\n"
                  "\tv_cust1: 9 (int) must be OwnInt type\n"
                  "\tv_cust2: 10 (int) must be str type\n"
                  "\tv_path: 12 (int) must be Path type")
    exc6 = ie(msg=f"Absent fields: {', '.join(tuple(exp_strict)[3:])}. Must be equal to expected "
                  f"({exp}), but received: v_bool, v_str, v_int")
    exc7 = ie(msg=f"Extra value: None. Must be {p_cnt} values long, but received {p_cnt + 1}")
    exc8 = ie(msg=f"Extra field: v_cust4. Must be not more than expected ({exp}), "
                  "but received: v_cust4")

    empty_v = ((), (None,), ((),), ({},))
    err_p_v = (((1, 2, 3),), ({'v_int': '6'},))
    err_f_v = ((tuple(range(p_cnt)),), (dict(zip(def_d, range(p_cnt))),))
    error_v = (*err_p_v, *err_f_v)
    extra_v = (((*def_t, None),), ({'v_cust4': None},))
    valid_v = (((True,),), ({'v_str': 'good'},))

    dc_ = {}
    _c_ = {'defaults': False}
    d__ = {'typecheck': False}
    dcc = {'typecast': True}
    ___ = {'defaults': False, 'typecheck': False}
    _cc = {'defaults': False, 'typecast': True}

    for name, args_set, kwargs, result_set in (
        [dft, empty_v, dc_, (exc1,) * 4],
        ['0', empty_v, _c_, (exc2,) * 4],
        ['1', empty_v, dc_, (def_t,) * 4],
        ['2', error_v, dc_, (exc3, exc4, exc5, exc5)],
        ['3', error_v, d__, tuple(fmt(x[0]) for x in error_v)],
        ['4', err_p_v, dcc, (fmt((True, '2', 3)), fmt({'v_int': 6}))],
        ['5', error_v, _c_, (exc6, exc4, exc5, exc5)],
        ['6', error_v, ___, (exc6, error_v[1][0], *(fmt(x[0]) for x in err_f_v))],
        ['7', err_p_v, _cc, (exc6, {'v_int': 6})],
        ['8', extra_v, d__, (exc7, exc8)],
        ['9', extra_v, ___, (exc7, exc8)],
        ['A', valid_v, dc_, tuple(fmt(x[0]) for x in valid_v)],
        [dft, err_p_v, dcc, (fmt((True, '2', 3)), fmt({'v_bool': True, 'v_str': '2', 'v_int': 6}))]
    ):
        for args, result in zip(args_set, result_set, strict=True):
            if isinstance(result, Exception):
                raises(build(name, result), profiles.set, name, *args, **kwargs)
            else:
                profiles.set(name, *args, **kwargs)
                assert profiles[name] == result

    raises(build('name', TypeError("'int' object is not iterable")), profiles.set, 'name', 1)


def test_update():
    data = Config1(profiles=True)
    cfg = data.cfg
    profiles = cfg.profiles

    def_v_str = data.v_str
    new_v_str = 'new_str'
    def_part = {'v_str': def_v_str}
    mod_part = {'v_str': new_v_str}
    def_data = cfg.get_defaults
    mod_data = def_data | mod_part

    # Default section
    assert cfg.get_defaults['v_str'] == def_v_str

    data.v_str = new_v_str
    assert cfg.get_defaults['v_str'] == new_v_str

    profiles.update()
    assert cfg.get_defaults['v_str'] == new_v_str

    # Profile tuple
    profiles.switch('1', True)
    assert cfg.get_defaults == mod_data
    assert cfg.get_data == mod_data

    data.v_str = def_v_str
    assert cfg.get_defaults == mod_data
    assert cfg.get_data == def_data
    assert profiles._profiles['1'] == tuple(mod_data.values())
    assert profiles['1'] == tuple(def_data.values())

    profiles.update()
    assert cfg.get_defaults == mod_data
    assert cfg.get_data == def_data
    assert profiles._profiles['1'] == tuple(def_data.values())
    assert profiles['1'] == tuple(def_data.values())

    # Profile dict
    profiles.set('2', {'v_str': new_v_str}, defaults=False)
    profiles.switch('2')
    assert cfg.get_defaults == mod_data
    assert cfg.get_data == mod_data

    data.v_str = def_v_str
    assert cfg.get_defaults == mod_data
    assert cfg.get_data == def_data
    assert profiles._profiles['2'] == mod_part
    assert profiles['2'] == def_part

    profiles.update()
    assert cfg.get_defaults == mod_data
    assert cfg.get_data == def_data
    assert profiles._profiles['2'] == def_part
    assert profiles['2'] == def_part


def test_rename():
    groups = (None, *'xyx')
    profiles0 = {'1': {'v_str': '1'}, '2': {'v_str': '2'}, '3': {'v_str': '3'}}
    profiles5 = {'1': {'v_str': '1'}, '5': {'v_str': '2'}, '3': {'v_str': '3'}}
    profiles6 = {'1': {'v_str': '1'}, '6': {'v_str': '2'}, '3': {'v_str': '3'}}
    profiles7 = {'1': {'v_str': '1'}, '7': {'v_str': '2'}, '3': {'v_str': '3'}}
    profiles8 = {'1': {'v_str': '1'}, '8': {'v_str': '2'}, '3': {'v_str': '3'}}
    name = '2'
    final_names = '5878'

    # Prepare configs
    cfgs = [Config1(profiles=True, group=g).cfg for g in groups]

    # Check defaults renaming
    func_name = "Config1.cfg.profiles.rename()"
    raises(InputError(func_name=func_name, msg="Cannot rename default profile to '0'"),
           cfgs[0].profiles.rename, '0')

    # Prepare configs profiles
    [cfg.profiles.set(k, v, defaults=False) for cfg in cfgs for k, v in profiles0.items()]

    def get_active():
        return ''.join(cfg.profiles.active for cfg in cfgs)

    def get_states():
        return str([cfg.profiles._profiles for cfg in cfgs])

    def get_data():
        return str([cfg.get_data for cfg in cfgs])

    # Default values
    defaults = cfgs[0].get_defaults
    state0 = (DEFAULT_SECTION, profiles0, defaults)
    assert get_active() == DEFAULT_SECTION * 4
    assert get_states() == str([state0[1]] * 4)
    assert get_data() == str([state0[2]] * 4)

    # Select profiles and try to rename it
    defaults_mod = defaults | profiles0[name]
    state5 = ('5', profiles5, defaults_mod)
    state6 = ('6', profiles6, defaults_mod)
    state7 = ('7', profiles7, defaults_mod)
    state8 = ('8', profiles8, defaults_mod)

    states_set = ([state5, state0, state0, state0],
                  [state5, state6, state0, state6],
                  [state5, state6, state7, state6],
                  [state5, state8, state7, state8])
    for i, (cfg, states) in enumerate(zip(cfgs, states_set, strict=True), 5):
        cfg.profiles.switch(name if i != 8 else '6')
        cfg.profiles.rename(str(i))
        assert get_active() == ''.join(x[0] for x in states)
        assert get_states() == str([x[1] for x in states])      # str preserves dict items position
        assert get_data() == str([x[2] for x in states])        # str preserves dict items position
    assert get_active() == final_names

    # Check no group profiles error handling
    cfg = cfgs[0]
    msg = "'2' profile in 'Config1' config is not exists. Available: ('1', '5', '3')"
    raises(InputError('old_name', func_name=func_name, msg=msg), cfg.profiles.rename, '', '2')
    assert get_active() == final_names

    # Check single in group profiles error handling
    cfg = cfgs[2]
    msg = ("Some profiles in group 'y' failed rename from '2' to '0':\n"
           f'\tConfig1: InputError("Provided wrong parameter to {func_name}: old_name. '
           "'2' profile in 'Config1' config is not exists. Available: ('1', '7', '3')\")\n"
           "Revert successful")
    raises(ProfilesError(msg), cfg.profiles.rename, '0', '2')
    assert get_active() == final_names

    # Check multiple in group profiles error handling
    cfg = cfgs[1]
    cfg.profiles.set('0')
    msg = ("Some profiles in group 'x' failed rename from '2' to '0':\n"
           f'\tConfig1: InputError("Provided wrong parameter to {func_name}: old_name. '
           "'2' profile in 'Config1' config is not exists. Available: ('1', '8', '3', '0')\")\n"
           f'\tConfig1: InputError("Provided wrong parameter to {func_name}: old_name. '
           "'2' profile in 'Config1' config is not exists. Available: ('1', '8', '3')\")\n"
           "Revert successful")
    raises(ProfilesError(msg), cfg.profiles.rename, '0', '2')
    assert get_active() == final_names


def test_switch():
    result = []

    def before():
        result.append('Before')

    def after():
        result.append('After')

    def fail():
        raise ValueError('Fail')

    data = Config1(profiles=True)
    profiles = data.cfg.profiles
    assert not data.v_bool

    name1 = 'name1'
    msg = ("'Config1' config profiles support structure is locked for changes "
           "(self.__setattr__('active', 'name1'))")
    raises(TypeError(msg), setattr, profiles, 'active', name1)

    profiles.set(name1, {'v_bool': True})
    assert profiles.active == DEFAULT_SECTION
    assert not data.v_bool

    profiles.switch(name1)
    config1a = Config1Alias()
    assert profiles.active == name1
    assert data.v_bool
    assert not result
    assert data != config1a

    name2 = 'name2'
    profiles.switch(name2, add=True, add_current=True)
    assert profiles.active == name2
    assert profiles[name1] == profiles[name2]
    assert tuple(data.cfg.get_defaults.values()) != profiles[name2]
    assert data.v_bool
    assert data != config1a

    name3 = 'name3'
    profiles.switch(name3, add=True)
    assert profiles.active == name3
    assert tuple(data.cfg.get_defaults.values()) == profiles[name3]
    assert data == config1a

    profiles.switch(name1)
    data.v_int = 1
    profiles.switch(name2)
    profiles.switch(name1)
    assert data.v_int == 1

    profiles.before_switch = before
    profiles.after_switch = after
    profiles.switch(DEFAULT_SECTION)
    assert not data.v_bool
    assert result == ['Before', 'After']
    result.clear()

    profiles.after_switch = fail
    raises(ValueError('Fail'), profiles.switch, name1)
    assert profiles.active == DEFAULT_SECTION
    assert not data.v_bool
    assert result == ['Before', 'Before']
    result.clear()

    profiles.before_switch = fail
    profiles.after_switch = after
    raises(ValueError('Fail'), profiles.switch, name1)
    assert profiles.active == DEFAULT_SECTION
    assert not data.v_bool
    assert not result

    # Group switch
    d1g1 = Config1(group='First')
    d2g1 = Config2(group='First')
    d3g2 = Config3(group='Second')
    d4 = Config1(profiles=True)
    d5g1 = Config3(group='First')
    data_configs = d1g1, d2g1, d3g2, d4, d5g1

    ds = DEFAULT_SECTION
    n1, n2, n3 = 'name1', 'name2', 'name3'
    for name, i_start in zip((n1, n2, n3), (11, 21, 31)):
        for i, data in enumerate(data_configs, i_start):
            next(data.cfg.profiles._switch(name, True, False))
            data.v_int = i

    assert [data.v_int for data in data_configs] == [31, 32, 33, 34, 35]
    assert [data.cfg.profiles.active for data in data_configs] == [n3] * 5

    n4, n5 = 'name4', 'name5'
    params = (
        (d1g1, n1, False, False, [11, 12, 33, 34, 15], [n1, n1, n3, n3, n1]),
        (d3g2, ds, False, False, [11, 12, 65535, 34, 15], [n1, n1, ds, n3, n1]),
        (d3g2, n2, False, False, [11, 12, 23, 34, 15], [n1, n1, n2, n3, n1]),
        (d5g1, n3, False, False, [31, 32, 23, 34, 35], [n3, n3, n2, n3, n3]),
        (d2g1, n4, True, True, [31, 32, 23, 34, 35], [n4, n4, n2, n3, n4]),
        (d1g1, n5, True, False, [65535, 65535, 23, 34, 65535], [n5, n5, n2, n3, n5]),
    )
    for data, name, add, add_current, v_ints, names in params:
        data.cfg.profiles.switch(name, add, add_current)
        assert [data.v_int for data in data_configs] == v_ints
        assert [data.cfg.profiles.active for data in data_configs] == names

    msg = ("Provided wrong parameters: add, add_current. "
           "Param 'add' must be True, when 'add_current' is True")
    raises(InputError(msg=msg), d1g1.cfg.profiles.switch, n5, False, True)

    n6 = 'name6'
    d2g1.cfg.profiles.set(n6)

    msg = ("Provided wrong parameter to Config1.cfg.profiles.switch(): name. "
           "'name6' profile in 'Config1' config is not exists. "
           "Available: ('name1', 'name2', 'name3', 'name4', 'name5')")
    raises(InputError(msg=msg), d1g1.cfg.profiles.switch, n6)

    msg = ("Some profiles in group 'First' failed switch to 'name6':\n"  # noqa
           f"\tConfig1: InputError(\"Provided wrong parameter to Config1.cfg.profiles.switch():"
           f" name. 'name6' profile in 'Config1' config is not exists. "
           "Available: ('name1', 'name2', 'name3', 'name4', 'name5')\")\n"
           f"\tGotcha: InputError(\"Provided wrong parameter to Config3.cfg.profiles.switch():"
           f" name. 'name6' profile in 'Gotcha' config is not exists. "
           "Available: ('name1', 'name2', 'name3', 'name4', 'name5')\")\n"
           "Revert successful")
    raises(ProfilesError(msg), d2g1.cfg.profiles.switch, n6)

    profiles._groups.clear()


def test_get_groups():
    profiles = Config1(profiles=True).cfg.profiles
    profiles._groups.clear()
    assert isinstance(profiles.get_groups, MappingProxyType)
    assert dict(profiles.get_groups) == {}

    profiles1 = Config1(profiles=True, group='1').cfg.profiles
    assert dict(profiles.get_groups) == {'1': [profiles1]}

    profiles2 = Config1(profiles=True, group='2').cfg.profiles
    assert dict(profiles.get_groups) == {'1': [profiles1], '2': [profiles2]}

    profiles3 = Config1(profiles=True, group='1').cfg.profiles
    assert dict(profiles.get_groups) == {'1': [profiles1, profiles3], '2': [profiles2]}


def test_del_group():
    profiles = Config1(profiles=True).cfg.profiles
    groups = profiles._groups.copy()
    assert profiles.del_group('1') == groups['1']
    assert profiles.del_group('2') == groups['2']
    assert dict(profiles.get_groups) == {}
    raises(KeyError('X'), profiles.del_group, 'X')
