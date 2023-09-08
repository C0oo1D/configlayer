"""Config layer main
    todo: Remove check_type(s) 'obj_t_check' (annotation provided, himself an evil Pinocchio)
    todo: Rework profiles.active_fields to profiles dict with active fields (and it's set method)
    todo: Add 'name' param to io.import_section (import single section to config possibility)
    todo: Reduce complexity (Flake8 C901 error disabled by changing max-complexity from 10 to 20)

    note: Think about pydantic: seems checks can be delegated, and added more possibilities
    note: Think about fast is_holder - check only __iter__, without __getitem__ iter detection

    note: "type: ignore" (mypy) is better than "typing.cast()", type hinting must stay type hinting
    note: "bug mypy" is not necessarily a bug, but that's what it's supposed to be
    note: "noqa" is mostly for silencing pycharm bugs or corrected side effects"""
from copy import deepcopy
from weakref import ref
from dataclasses import replace

from ._config import ConfigSupport, Options
from ._profiles import Profiles
from ._io import IO
from ._file import File

from .types import path_t, Field
from .utils import (init_reraise, get_attrs, check_type, check_items, check_types, safe, GetName,
                    is_dunder, with_type, is_exception)
from .constants import DEFAULT_SECTION, DEFAULT_ID
from .exceptions import InputError, CheckTypeError, FieldError


__all__ = ['ConfigBase', 'LanguageBase', 'Field', 'Options']
__version__ = "0.1.2"


class ConfigBase:
    """Config base
    Must be inherited with providing configuration fields"""
    cfg: ConfigSupport

    @init_reraise('config', doc=True)
    def __init__(self, path: path_t | None = None, *,
                 profiles: bool | None = None, io: bool | None = None, group: str | None = None,
                 default_section: str = DEFAULT_SECTION, options: Options | None = None,
                 type_name: str = 'config'):
        """
        :arg path:              Current configuration file path to load from or save to
        :arg profiles:          Enable profiles support for current configuration
        :arg io:                Enable input/output operations for current configuration
        :arg group:             Group name for current configuration, if group changes needed
        :arg default_section:   Default section name for current configuration
        :arg options:           More precise behavior options for current configuration
        :arg type_name:         Internal current configuration type name for error message
        :raise InitError:       If something goes wrong"""
        _ = GetName(self, doc=True, full=True)
        _name, name = str(_.attrs.cls), str(_)  # noqa

        # Check that call is inherited
        if type(self) == ConfigBase:
            raise InputError(must_be='inherited')

        # Assign or check options
        if options is None:
            options = Options()
        elif not isinstance(options, Options):
            raise InputError('options', must_be='Options type', received=with_type(options))

        # Assign states of profiles if they are not provided and check bound settings
        profiles = profiles if profiles is not None else group is not None
        if group is not None and not profiles:
            raise InputError('profiles', must_be=f"True or unfilled when {group=!r} provided")

        # Assign states of io if they are not provided and check bound settings
        io = io if io is not None else path is not None
        if path is not None and not io:
            raise InputError('io', must_be=f'True or unfilled when {path=!r} provided')

        # Get fields names with declared types and values, including multiple inherited configs
        attrs = get_attrs(self, 1, internal=True, dunder=True)  # dunder for merged __annotations__
        cfg_values = {k: v for k, v in attrs.items() if not is_dunder(k)}
        cfg_types = attrs.get('__annotations__', {})

        # Check for empty config, reserved 'cfg' field name and that all values/types was provided
        if not cfg_types and not cfg_values:
            raise InputError(must_be='at least one field', received='empty config')
        if 'cfg' in cfg_types | cfg_values:
            raise InputError('cfg', item_name='field',
                             reserved="for ConfigSupport structure, use another field name")
        if cfg_values.keys() != cfg_types.keys():
            if wrong_names := [x for x in cfg_types if x not in cfg_values and is_dunder(x)]:
                raise InputError(*wrong_names, item_name='field', dunder='names are forbidden')
            check_items(cfg_values, cfg_types, 'field', str, input_exc=('',),
                        extra_template='{} without type: ',
                        absent_template='{} without factory default: ',
                        must_be='', received='', fields=cfg_values, types=cfg_types)

        # Prepare fields and default values
        fields, defaults = {}, {}
        for k, v in cfg_values.items():

            # Check that field types is actually types, and set info if possibly shadowing detected
            if isinstance(check_type(t := cfg_types[k], type, raw=True), CheckTypeError):
                msg = f"Field {k!r} type {with_type(t)} - is not a type"
                if t == v:
                    msg += (", and is equal to a value. "
                            "If shadowing - regular scoping rules applied (cpython issue #98876)")
                raise InputError(msg=msg)

            # Fill default values for type checking and fields for usage
            if isinstance(v, Field):
                defaults[k] = d = deepcopy(v.default)
                fields[k] = replace(v, default=d, type=t)
            else:
                defaults[k] = d = deepcopy(v)
                fields[k] = Field(d, type=t)

        # Check and set default values
        self.__dict__ |= check_types(defaults, cfg_types, item_name='field', obj_t_check=False,
                                     input_exc=('',))

        # Init config support structure with additional functionality (with - unlocks structure)
        data = ref(self)()
        with ConfigSupport(data, fields, _name, name, default_section, options, type_name) as cfg:
            self.cfg, cfg = cfg, ref(cfg)()
            self.cfg.profiles = Profiles(cfg, data, group) if profiles else None
            self.cfg.io = IO(cfg, data, fields) if io else None
            self.cfg.file = File(cfg, path) if path is not None else None

    def __del__(self):
        """Remove path from used at object deletion by garbage collector
        Warning: del keyword deletes only link to object from local area, not object itself!"""
        if (cfg := getattr(self, 'cfg', None)) and (file := getattr(cfg, 'file', None)):
            file.__del__()

    def __repr__(self):
        """Class name in code"""
        return self.cfg._name  # noqa

    def __str__(self):
        """Config name for user + fields names and values"""
        return '\n\t'.join((f'{self.cfg.name!r} {self.cfg.type_name}:',
                            *(f'{k}: {field.type.__name__} = {getattr(self, k)!r}'
                              for k, field in self.cfg.get_fields.items())))

    def __eq__(self, other):
        """Only fields compared! Profiles and any other functionalities are ignored!"""
        if issubclass(type(other), ConfigBase) and self.cfg.get_fields == other.cfg.get_fields:
            return self.cfg.get_data == other.cfg.get_data
        return False

    def __set_field__(self, key, value, cfg, field, options, *, check=True, revert=False):
        if value == DEFAULT_ID:
            value = field.default
        elif not revert and check and options.typecheck:
            value = check_type(value, field.type, options.typecast)

        # Set user default value in default profile if default section is active
        if profiles := cfg.profiles:
            if profiles.active == cfg.def_sect:
                field.default = value
            if key not in profiles.active_fields:
                raise FieldError('Set', cfg.name, key, value, getattr(self, key),
                                 type_name=cfg.type_name,
                                 reason=f'it is fixed by {profiles.active!r} profile. '
                                        f'Available fields: {", ".join(profiles.active_fields)}')

        # Get previous and set current value
        prev_value = getattr(self, key)
        object.__setattr__(self, key, value)

        # Run on_set handlers
        errors = []
        for name, (f_name, run_if_equal, partial_func) in cfg.get_on_set.items():
            if f_name is None or f_name == key:
                if run_if_equal or prev_value != value:
                    if is_exception(error := safe(partial_func, key, prev_value, value)):
                        errors.append(f'{name!r} handler ({GetName(partial_func.func)}): {error}')
        errors = '\n\t'.join(('on_set handlers errors:', *errors)) if errors else ''

        # Return revert if called with it (must be only internal call)
        if revert:
            return f"Revert completed{f', but {errors}' if errors else ''}"

        # Handle on_set errors
        if errors:
            if options.revert_fails:
                add_msg = self.__set_field__(key, prev_value, cfg, field, options, revert=True)
            else:
                add_msg = 'Revert option is disabled - field value is left changed'
            raise FieldError('Set', cfg.name, key, value, prev_value, type_name=cfg.type_name,
                             reason=f'{errors}\n{add_msg}', failed=False)

    def __setattr__(self, key, value):
        """Set field (or attribute if config is not initialized yet)"""
        # RAW write if ConfigSupport is not inited yet
        if (cfg := getattr(self, 'cfg', None)) is None:
            return super().__setattr__(key, value)

        # Check for exists field name
        if key not in (fields := cfg.get_fields):
            raise FieldError('Set', cfg.name, key, value, type_name=cfg.type_name,
                             reason=f"it is not field. Available: {', '.join(fields)}")

        # Set field value
        self.__set_field__(key, value, cfg, fields[key], cfg.options)

    def __delattr__(self, key):
        """Clear field (replaces field value to user default)"""
        cfg = self.cfg
        if key not in cfg.get_fields:
            raise FieldError('Delete', cfg.name, key, type_name=cfg.type_name,
                             reason='it is not field. Attributes cannot be deleted')
        self.__setattr__(key, DEFAULT_ID)


class LanguageBase(ConfigBase):
    """Language base
    Must be inherited with providing language str fields"""
    @init_reraise('language', doc=True)
    def __init__(self, *args, **kwargs):
        if type(self) == LanguageBase:
            raise InputError(must_be='inherited')

        # Get all fields from multiple inherited configs
        attrs = get_attrs(self, 2, internal=True, dunder=True)  # dunder for merged __annotations__

        # Language fields must not have types provided
        if cfg_types := attrs.get('__annotations__', {}):
            msg = 'No need to annotate language fields, only str type allowed'
            raise InputError(*cfg_types, item_name='field', msg=msg)

        # Force all fields to str type
        self.__annotations__ = {k: str for k in attrs if not is_dunder(k)}

        # Group is fixed for language config
        if (group := kwargs.get('group', None)) is not None:
            raise InputError('group', reserved=f"for LanguageBase ({group!r} will be 'Language')")

        # Init config as language group for synchronized translations changing
        super().__init__(*args, **kwargs, group='Language', type_name='language')

    def __str__(self):
        """Language name for user + fields names and values"""
        return '\n\t'.join((f'{self.cfg.name!r} {self.cfg.type_name}:',
                            *(f'{k}: {getattr(self, k)!r}' for k in self.cfg.get_fields)))
