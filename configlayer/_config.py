"""Internal config layer support structure"""
from types import MappingProxyType
from typing import Any, Callable
from functools import partial

from ._profiles import Profiles
from ._io import IO
from ._file import File

from .types import fields_t, on_set_t, Field
from .utils import Locker, check_extra, check_types, set_slots_defaults, fmt_exc
from .exceptions import OptionsCheckError, InputError


_get_raw = object.__getattribute__


@set_slots_defaults(fields_t=bool)
class Options:
    """Config options defaults
    There is 2 ways to change it:
        1. Fill instance and provide it at Config init (options keyword)
        2. Change in inited config directly (<config_data>.cfg.options.<option_name>)"""
    typecheck = True        # Check field data for type at each field set
    typecast = True         # Try to cast type if type check enabled and failed
    revert_fails = False    # Field value revert if on_set get some error

    def __post_init__(self):
        if msg := self._check():
            raise OptionsCheckError(msg)

    def __setattr__(self, key, value, revert=False):
        if not isinstance(value, bool):
            raise OptionsCheckError('Options accepting only booleans')
        if value == (prev_value := getattr(self, key, None)):
            return

        object.__setattr__(self, key, value)
        if msg := self._check():
            if revert:
                return f'Some options changed in wrong way, check failed: {msg}'
            msg = f'Set option {key!r} to {value!r} failed: {msg}'
            if msg2 := self.__setattr__(key, prev_value, revert=True):
                raise OptionsCheckError(f'{msg}. Revert to {prev_value!r} also failed: {msg2}')
            raise OptionsCheckError(f'{msg}. Reverted to {prev_value!r} successfully')

    def _check(self):
        if self.typecast and not self.typecheck:
            return 'Type checking is disabled, type casting cannot be enabled'


class ConfigSupport(Locker):
    """Config support structure
    Holds a lot of functionality for config operations"""
    __slots__ = ('__weakref__', '_data', '_fields', '_on_set', '_name',
                 'name', 'type_name', 'def_sect', 'options', 'version', 'profiles', 'io', 'file')
    _data:      Any
    _fields:    dict[str, Field]
    _on_set:    dict[str, on_set_t]
    name:       str
    type_name:  str
    def_sect:   str
    options:    Options
    version:    None | int
    profiles:   None | Profiles
    io:         None | IO
    file:       None | File

    def __init__(self, data, fields, _name, name, default_section, options, type_name):
        self._data = data
        self._fields = fields
        self._on_set = {}
        self._name = _name
        self.name = name
        self.type_name = type_name
        self.def_sect = default_section
        self.options = options
        self.version = self.profiles = self.io = self.file = None

        # Locks structure for changes with disabling attribute deletion
        super().__init__(del_attr=False, name=str(self))

    def __repr__(self):
        return f'{self._name}.cfg'  # noqa

    def __str__(self):
        return f'{self.name!r} {self.type_name} support structure'

    def add_on_set(self, name: str, field_name: str | None, run_if_equal: bool,
                   func: Callable, *args, **kwargs):
        """Add function call on specified or any (if None provided) config field set
        :arg name:          Handler name
        :arg field_name:    Field name or None (if all fields handler provided)
        :arg run_if_equal:  Run handler anyway (if field value is not changed)
        :arg func:          Handler function
        :arg args:          :arg func: positional arguments before: key, prev_value, value
        :arg kwargs:        :arg func: keyword arguments
        :raise InputError:  If wrong arguments provided"""
        if name in self._on_set:
            raise InputError('name', func_name=f'{self!r}.add_on_set()',
                             msg=f'Cannot add {name!r} handler, it already exists')
        if field_name is not None and field_name not in self._fields:
            raise InputError('field_name', func_name=f'{self!r}.add_on_set()',
                             msg=f'Cannot add {name!r} handler, not exists {field_name = }')
        self._on_set.update({name: (field_name, run_if_equal, partial(func, *args, **kwargs))})

    def del_on_set(self, name: str):
        """Delete on_set handler by its name
        :arg name:  Handler name"""
        del self._on_set[name]

    @property
    def get_on_set(self) -> MappingProxyType[str, on_set_t]:
        """Get exists on_set handlers as a dict view"""
        return MappingProxyType(self._on_set)

    @property
    def get_fields(self) -> MappingProxyType[str, Field]:
        """Get fields descriptors as dict"""
        return MappingProxyType(self._fields)

    @property
    def get_data(self) -> fields_t:
        """Get fields data as dict"""
        data = self._data
        return {k: getattr(data, k) for k in self._fields}

    @property
    def get_changed(self) -> fields_t[bool]:
        """Get changed fields states as dict"""
        data = self._data
        return {k: getattr(data, k) != v.default for k, v in self._fields.items()}

    @property
    def get_types(self) -> fields_t[type]:
        """Get fields types as dict"""
        return {k: v.type for k, v in self._fields.items()}

    @property
    def get_defaults(self) -> fields_t:
        """Get fields defaults as dict"""
        return {k: v.default for k, v in self._fields.items()}

    @property
    def get_factory_defaults(self) -> fields_t:
        """Get fields defaults provided at config declaration as dict"""
        c = type(self._data)
        return {k: f.default if isinstance(f := getattr(c, k), Field) else f for k in self._fields}

    def _check_fields(self, input_exc, fields: fields_t, types=True, typecast=False):
        if not fields:
            raise fmt_exc(input_exc, 'Empty fields provided')

        check_extra(fields, self._fields, 'field', input_exc=input_exc)

        if types:
            _types = self.get_types
            # bug mypy: dict[str, type] is type, not str.. and it is also holder_t..
            return check_types(fields, {k: _types[k] for k in fields}, typecast,                    # type: ignore[misc]
                               input_exc=input_exc, obj_t_check=False)
        return fields

    def _set_fields(self, fields: fields_t):
        data = self._data
        # bug mypy: return value is not used
        [setattr(data, k, v) for k, v in fields.items()]                                     # type: ignore[func-returns-value]

    def _set_defaults(self, fields: fields_t):
        _fields = self._fields
        # bug mypy: return value is not used
        [setattr(_fields[k], 'default', v) for k, v in fields.items()]                       # type: ignore[func-returns-value]

    def set_fields(self, fields: fields_t, typecheck=True, typecast=False):
        """Set current fields by dict with type check and cast possibility
        :arg fields:        Dict with data to set fields
        :arg typecheck:     Data types check
        :arg typecast:      Data types cast (if check failed)
        :raise InputError:  If wrong arguments provided"""
        input_exc = (f'{self!r}.set_fields()', 'fields')
        self._set_fields(self._check_fields(input_exc, fields, typecheck, typecast))
        if self.profiles:
            self.profiles.update()

    def set_defaults(self, fields: fields_t, typecheck=True, typecast=False):
        """Set defaults by dict with type check and cast possibility
        :arg fields:        Dict with data to set defaults
        :arg typecheck:     Data types check
        :arg typecast:      Data types cast (if check failed)
        :raise InputError:  If wrong arguments provided"""
        input_exc = (f'{self!r}.set_defaults()', 'fields')
        fields = self._check_fields(input_exc, fields, typecheck, typecast)
        if self.profiles and self.profiles.active == self.def_sect:
            self._set_fields(fields)
        self._set_defaults(fields)
