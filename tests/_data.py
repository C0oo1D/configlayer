"""Data for tests"""
from ast import literal_eval
from pathlib import Path

from configlayer import Field, ConfigBase, LanguageBase


TEMP_PATH = Path('tests/_file_data/temp_config.ini')


def empty_func(x):
    return x


class OwnInt(int):
    def __eq__(self, other):
        if isinstance(other, type(self)):
            return int(self) == int(other)
        return False


class Config1(ConfigBase):
    v_bool: bool = False
    v_str: str = 'Some string'
    v_int: int = 65535
    v_float: float = 3.1415
    v_bytes: bytes = b'Some bytes'
    v_tuple: tuple = (1, 2, 3, None)
    v_list: list = [-1, 0, 1, 'repeat €₽']
    v_set: set = {'first'}
    v_dict: dict = {1: 'one', 2: 'two'}
    v_cust1: OwnInt = OwnInt(5)
    v_cust2: str = Field('something')                                                # type: ignore
    v_cust3: int = Field(2, lambda x: f'{x}custom', lambda x: literal_eval(x[:-6]))  # type: ignore
    v_path: Path = Path('some_path')
    _internal: int = 8


exp_strict = {
    'v_bool': 'False',
    'v_str': "'Some string'",
    'v_int': '65535',
    'v_float': '3.1415',
    'v_bytes': "b'Some bytes'",
    'v_tuple': '(1, 2, 3, None)',
    'v_list': "[-1, 0, 1, 'repeat €₽']",
    'v_set': "{'first'}",
    'v_dict': "{1: 'one', 2: 'two'}",
    'v_cust1': '5',
    'v_cust2': "'something'",
    'v_cust3': '2custom',
    'v_path': 'some_path',
    '_internal': '8'}


imp_strict = {
    'v_bool': False,
    'v_str': 'Some string',
    'v_int': 65535,
    'v_float': 3.1415,
    'v_bytes': b'Some bytes',
    'v_tuple': (1, 2, 3, None),
    'v_list': [-1, 0, 1, 'repeat €₽'],
    'v_set': {'first'},
    'v_dict': {1: 'one', 2: 'two'},
    'v_cust1': OwnInt(5),
    'v_cust2': 'something',
    'v_cust3': 2,
    'v_path': Path('some_path'),
    '_internal': 8}


class Config1Alias(Config1):
    """Alias"""


class Config2(Config1):
    """Valid fields"""
    c2: str = 'c2'


class Config3(Config2):
    """Gotcha
    With additional info"""
    c3: str = 'c3'


class Config4(Config1):
    """IO"""
    C4: int = Field(4, lambda x: x, lambda x: x)                                     # type: ignore


class EmptyConfig(ConfigBase):
    pass


class NoType(ConfigBase):
    test = None


class NoDefaults(ConfigBase):
    test: str


class NoBoth(ConfigBase):
    test_no_t = None
    test_no_d: str
    test_ok: str = None                                                              # type: ignore


class CfgInConfig(ConfigBase):
    cfg: str = 'text'                                                                # type: ignore


class DunderInConfig(Config1):
    __dunder__: str = 'here'


class WrongType1(ConfigBase):
    str: str = 'text'


class WrongType2(ConfigBase):
    str: 'str' = 'text'


class WrongType3(ConfigBase):
    some: int = b'1'                                                                 # type: ignore


class WrongType4(ConfigBase):
    test: int = Field(b'1')                                                          # type: ignore


class WrongCast:
    def __new__(cls, *args, **kwargs):
        return int(*args, **kwargs)


def wrong_func(data):    # noqa
    raise TypeError('Wrong func!')


def wrong_func_2(*args):
    raise ValueError(f'Wrong func 2! {args}')


def wrong_func_3(*args, **kwargs):
    if args[-1] != 'Some string':
        raise ValueError(f'Cannot change value {args}{f", {kwargs}" if kwargs else ""}')


def increment_str(data: str):
    return int(data) + 1


class ReprError(int):
    def __repr__(self):
        raise TypeError('Wrong repr!')


class WrongReprType(int):
    def __repr__(self):
        return self


class WrongReprStr(int):
    def __repr__(self):
        return 'Eval it!'


class WrongExportRepr(ConfigBase):
    test: int = ReprError(5)


class WrongExportFunc(ConfigBase):
    test: int = Field(5, export_func=wrong_func)                                     # type: ignore


class WrongExportType(ConfigBase):
    test: int = WrongReprType(5)


class WrongImportEval(ConfigBase):
    test: int = WrongReprStr(5)


class WrongImportFunc(ConfigBase):
    test: int = Field(5, import_func=wrong_func)                                     # type: ignore


class WrongImportResult(ConfigBase):
    test: int = Field(5, import_func=increment_str)                                  # type: ignore


class ExportSensitive(ConfigBase):
    f1: int = Field(2, lambda x: repr(x) if isinstance(x, int) else x)               # type: ignore
    f2: dict = Field({2: 2}, lambda x: repr(x) if isinstance(x, dict) else x)        # type: ignore


class Lang1(LanguageBase):
    """Random"""
    some1 = 'First some'
    some2 = 'Second some'
    another_one = 'Another'


class ProvidedType(LanguageBase):
    some: str = '1'


class WrongTypeLang(LanguageBase):
    wrong_attr = 1
