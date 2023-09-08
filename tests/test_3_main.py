from configlayer.exceptions import InputError, CheckTypeError, FieldError
from configlayer.types import mb_holder_t

from _utilities import raises_init, raises, init
from _data import ConfigBase, CfgInConfig, DunderInConfig, EmptyConfig, NoType, NoDefaults, NoBoth
from _data import LanguageBase, ProvidedType, Lang1
from _data import Config1, Config1Alias, Config2, Config3, Config4, OwnInt
from _data import WrongType1, WrongType2, WrongType3, WrongType4, WrongTypeLang
from _data import exp_strict, Path


def raises_init_lang(exceptions: mb_holder_t[Exception], func, *args, **kwargs):
    raises(init('language', exceptions, func, *args, **kwargs), func, *args, **kwargs)


def raises_init_lang_config(exceptions: mb_holder_t[Exception], func, *args, **kwargs):
    config_exception = init('config', exceptions, func, *args,
                            group='Language', type_name='language', **kwargs)
    lang_exception = init('language', config_exception, func, *args, **kwargs)
    raises(lang_exception, func, *args, **kwargs)


def test_config_init():
    # Check for call without config and options correctness
    raises_init(InputError(must_be="inherited"), ConfigBase)
    raises_init(InputError("options", must_be="Options type", received="(True, True) (tuple)"),
                Config1, options=(True, True))

    # Check bound settings
    raises_init(InputError("profiles", must_be="True or unfilled when group='group1' provided"),
                Config1, group='group1', profiles=False)
    raises_init(InputError("io", must_be="True or unfilled when path='some path' provided"),
                Config1, 'some path', io=False)

    # Check for empty config, reserved field name and that all values and types was provided
    msg = "Must be at least one field, but received empty config"
    raises_init(InputError(msg=msg), EmptyConfig)
    msg = "Provided wrong field: cfg. Reserved for ConfigSupport structure, use another field name"
    raises_init(InputError(msg=msg), CfgInConfig)
    msg = "Provided wrong field: __dunder__. Dunder names are forbidden"
    raises_init(InputError(msg=msg), DunderInConfig)
    msg = "Field without type: test. Fields: {'test': None}. Types: {}"
    raises_init(InputError(msg=msg), NoType)
    msg = "Field without factory default: test. Fields: {}. Types: {'test': <class 'str'>}"
    raises_init(InputError(msg=msg), NoDefaults)
    msg = ("Field without type: test_no_t. Field without factory default: test_no_d. "
           "Fields: {'test_no_t': None, 'test_ok': None}. "
           "Types: {'test_no_d': <class 'str'>, 'test_ok': <class 'str'>}")
    raises_init(InputError(msg=msg), NoBoth)

    # Prepare and check data
    msg = "Field 'str' type 'text' (str) - is not a type, and is equal to a value. "
    msg_shadow = "If shadowing - regular scoping rules applied (cpython issue #98876)"
    raises_init(InputError(msg=msg + msg_shadow), WrongType1)
    raises_init(InputError(msg="Field 'str' type 'str' (str) - is not a type"), WrongType2)
    raises_init(InputError(msg="Field 'some'=b'1' (bytes) must be int type"), WrongType3)
    raises_init(InputError(msg="Field 'test'=b'1' (bytes) must be int type"), WrongType4)
    raises_init_lang_config(InputError(msg="Field 'wrong_attr'=1 (int) must be str type"),
                            WrongTypeLang)


def test_config_repr_str():
    def fmt(name: str, *add_fields: str):
        fields = ("v_bool: bool = False",
                  "v_str: str = 'Some string'",
                  "v_int: int = 65535",
                  "v_float: float = 3.1415",
                  "v_bytes: bytes = b'Some bytes'",
                  "v_tuple: tuple = (1, 2, 3, None)",
                  "v_list: list = [-1, 0, 1, 'repeat €₽']",
                  "v_set: set = {'first'}",
                  "v_dict: dict = {1: 'one', 2: 'two'}",
                  "v_cust1: OwnInt = 5",
                  "v_cust2: str = 'something'",
                  "v_cust3: int = 2",
                  "v_path: Path = WindowsPath('some_path')",
                  "_internal: int = 8")
        return '\n\t'.join((f'{name!r} config:', *fields, *add_fields))

    for cls, str1, str2 in (
            [Config1, "Config1", fmt('Config1')],
            [Config2, "Config2", fmt('Valid fields', "c2: str = 'c2'")],
            [Config3, "Config3", fmt('Gotcha', "c2: str = 'c2'", "c3: str = 'c3'")],
            [Config4, "Config4", fmt('IO', "C4: int = 4")]):
        obj = cls()
        assert repr(obj) == str1
        assert str(obj) == str2


def test_config_data():
    data = Config1()
    assert tuple(data.cfg.get_fields) == tuple(exp_strict)
    assert data.v_bool is False
    assert data.v_str == 'Some string'
    assert data.v_int == 65535
    assert data.v_float == 3.1415
    assert data.v_bytes == b'Some bytes'
    assert data.v_tuple == (1, 2, 3, None)
    assert data.v_list == [-1, 0, 1, 'repeat €₽']
    assert data.v_set == {'first'}
    assert data.v_dict == {1: 'one', 2: 'two'}
    assert data.v_cust1 == OwnInt(5)
    assert data.v_cust2 == 'something'
    assert data.v_cust3 == 2
    assert data.v_path == Path('some_path')
    assert data._internal == 8


def test_config_eq():
    config1 = Config1()
    config1a = Config1Alias()
    assert config1 == config1a
    config1a.v_int = 2
    assert config1 != config1a


def test_config_field():
    data = Config1()

    # Set field
    reason = f"it is not field. Available: {', '.join(exp_strict)}"
    raises(FieldError('Set', 'Config1', 'cfg', 1, reason=reason), setattr, data, 'cfg', 1)
    raises(FieldError('Set', 'Config1', 'x', 2, reason=reason), setattr, data, 'x', 2)

    data.v_str = 2

    data.cfg.options.typecast = False
    raises(CheckTypeError("2 (int) must be str type"), setattr, data, 'v_str', 2)

    data.cfg.options.typecheck = False
    data.v_str = 2
    assert data.v_str == 2

    # Delete field
    del data.v_str
    assert data.v_str == data.cfg.get_defaults['v_str']

    assert not data.v_bool
    data.v_bool = True
    assert data.v_bool

    raises(FieldError('Delete', 'Config1', 'x',
                      reason="it is not field. Attributes cannot be deleted"),
           delattr, data, 'x')

    # Profiles part in set
    data = Config1(profiles=True)
    cfg = data.cfg
    profiles = cfg.profiles

    # Set defaults too if default profile active
    def_v_str = data.v_str
    new_v_str = 'new_str'
    assert cfg.get_defaults['v_str'] == def_v_str

    data.v_str = new_v_str
    assert data.v_str == new_v_str
    assert cfg.get_defaults['v_str'] == new_v_str

    # Set in profile with fixed fields
    profiles.set('1', {'v_str': def_v_str, 'v_bool': True}, defaults=False)
    profiles.switch('1')
    assert data.v_str == def_v_str

    data.v_str = new_v_str
    assert data.v_str == new_v_str

    raises(FieldError('Set', 'Config1', 'v_int', 5, 65535,
                      reason="it is fixed by '1' profile. Available fields: v_str, v_bool"),
           setattr, data, 'v_int', 5)


def test_language_init():
    raises_init_lang(InputError(must_be='inherited'), LanguageBase)

    msg = 'No need to annotate language fields, only str type allowed'
    raises_init_lang(InputError('some', item_name='field', msg=msg), ProvidedType)

    msg = "Reserved for LanguageBase ('SomeGroup' will be 'Language')"
    raises_init_lang(InputError('group', msg=msg), Lang1, group='SomeGroup')


def test_language_repr_str():
    assert repr(Lang1()) == 'Lang1'
    assert str(Lang1()) == '\n\t'.join(("'Random' language:", "some1: 'First some'",
                                        "some2: 'Second some'", "another_one: 'Another'"))

    Lang1().cfg.profiles.del_group('Language')


def test_language_data():
    text = Lang1()
    assert text.some1 == 'First some'
    assert text.some2 == 'Second some'
    assert text.another_one == 'Another'
    text.cfg.profiles._groups.clear()
