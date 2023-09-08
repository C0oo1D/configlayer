"""Internal config layer IO support structure"""
from ast import literal_eval
from typing import Any, Mapping, Callable
from pathlib import Path

from .exceptions import CheckValueError, InputError, FieldError, IOExportError, IOImportError
from .types import mb_holder_t, fields_t, Field
from .utils import (Locker, GetName, as_holder, check_input, check_extra, check_items, check_type,
                    with_type, fmt_exc, as_dict)


_UNIQUE = object()


# Error templates
_TEMPL_FIELD_DESC = "Field {}={} by {}: {!r}"
_TEMPL_CONFIG = "Cannot {} {!r} config"

# Exceptions holder
_EXC_LIST = {'import': IOImportError, 'export': IOExportError}

# Hooks
_EXPORT_HOOKS: dict[type, Callable] = {Path: str}
_IMPORT_HOOKS: dict[type, Callable] = {Path: Path}


class IO(Locker):
    """IO optional structure
    Used in config support structure if enabled, for any IO operations"""
    __slots__ = ('_cfg', '_data')
    _key_section = '_CONFIG_LAYER'  # Class constant
    _key_version = 'version'        # Class constant
    _key_profile = 'profile'        # Class constant
    _key_fields = 'fields'          # Class constant

    def __init__(self, cfg, data, fields):
        self._cfg = cfg
        self._data = data

        # Config IO check (rewrite to export/import section with all fields)
        errors = []
        for name, field in fields.items():
            exported = self.export_field(name, field.default)
            imported = self.import_field(name, exported)
            if field.default != imported:
                export_func = GetName(field.export_func)
                import_func = GetName(field.import_func)
                errors.append(f'Field {name}={with_type(field.default)} must be equal '
                              f'imported={with_type(imported)}: '
                              f'{export_func = }, {exported = }, {import_func = }')
        if errors:
            raise CheckValueError('\n\t'.join((f'{cfg.name!r} config IO check failed:', *errors)))

        # Locks structure for changes with disabling attribute deletion
        super().__init__(del_attr=False, name=str(self))

    def __repr__(self):
        return f'{self._cfg!r}.io'

    def __str__(self):
        return f'{self._cfg.name!r} {self._cfg.type_name} I/O support structure'

    def _exc(self, op, exc, section=_UNIQUE):
        section = '' if section == _UNIQUE else f' section {section!r}' if section else ' section'
        return _EXC_LIST[op](f"{_TEMPL_CONFIG.format(op, self._cfg.name)}{section}. {exc}")

    @staticmethod
    def _export_field(field: Field, value, typecast: bool) -> str:
        hook = _EXPORT_HOOKS.get(field.type, field.export_func)
        return check_type(hook(value), str, typecast, 'field', False)

    def export_field(self, name: str, value: Any = None, typecast=True) -> str:
        """Export single field to raw str type
        :arg name:          Field name
        :arg value:         Field value (if override needed)
        :arg typecast:      Force str type if field export_func result is not str
        :return:            Field raw value
        :raise FieldError:  Any error"""
        field = None
        try:
            field = self._cfg.get_fields[name]
            value = getattr(self._data, name) if value is None else value
            return self._export_field(field, value, typecast)
        except Exception as e:
            kw = {} if field is None else {'by_func': GetName(field.export_func, code=True)}
            kw |= {} if value is None else {'from_value': value}
            raise FieldError('Export', self._cfg.name, name, **kw, type_name=self._cfg.type_name,
                             reason=repr(e)) from e

    def export_section(self, section: str | fields_t | None = None, strict=False, typecast=True
                       ) -> fields_t[str]:
        """Export single section to dict with raw str type values
        :arg section:           Section name, fields dict, or active section (if not provided)
        :arg strict:            Export all fields (not skip equal to default)
        :arg typecast:          Force str type if field export_func result is not str
        :return:                Fields raw values
        :raise InputError:      If wrong arguments provided
        :raise IOExportError:   Any other error"""
        cfg = self._cfg
        profiles = cfg.profiles
        fields = cfg.get_fields
        active_fields = tuple(fields)
        name, section = (section, None) if isinstance(section, str) else (None, section)
        ie = (f'{self!r}.export_section()', 'section')

        try:
            # Provided section select
            if section is not None:
                check_type(section, Mapping, input_exc=ie)
                check_extra(section, fields, 'field', input_exc=ie)
                items, defaults = section, cfg.get_defaults

            # Internal section direct export
            elif name == self._key_section:
                support = {}
                if cfg.version:
                    support[self._key_version] = repr(cfg.version)
                if profiles:
                    support[self._key_profile] = repr(profiles.active)
                    if fields := {k: tuple(v) for k, v in profiles.get.items()
                                  if isinstance(v, dict)}:
                        support[self._key_fields] = repr(fields)
                return support

            # Default section select
            elif (name == cfg.def_sect or
                  name is None and profiles and profiles.active == cfg.def_sect):
                name, items, defaults = cfg.def_sect, cfg.get_defaults, cfg.get_factory_defaults

            # Profile section select
            elif profiles:
                if name is None:
                    name = profiles.active
                elif name not in profiles:
                    p = ", ".join(map(repr, profiles.get))
                    details = f'available profiles: {p}' if p else 'there is no profiles'
                    raise fmt_exc(ie, f'Profile is not exists, {details}')
                items, defaults = as_dict(profiles[name], fields), cfg.get_defaults
                active_fields = tuple(items)

            # Config section select
            else:
                if name is None or name == cfg.name:
                    name, items, defaults = cfg.name, cfg.get_data, cfg.get_defaults
                else:
                    raise fmt_exc(ie, must_be=repr(cfg.name), received=repr(name))

            # Export section
            _export = self._export_field
            result, errors = {}, []
            for key, field in fields.items():
                default = defaults[key]
                value = items.get(key, default)
                if key in active_fields and strict or value != default:
                    try:
                        result[key] = _export(field, value, typecast)
                    except Exception as e:
                        fn = GetName(field.export_func, code=True)
                        errors.append(_TEMPL_FIELD_DESC.format(key, with_type(value), fn, e))
            if errors:
                raise CheckValueError('\n\t'.join(('Errors:', *errors)))
            return result

        except InputError:
            raise
        except CheckValueError as e:
            raise self._exc('export', str(e), name)
        except Exception as e:
            raise self._exc('export', repr(e), name) from e  # not tested extreme case exception

    def export_config(self, sections: mb_holder_t[str] | None = None, *, strict_defaults=False,
                      strict_data=False, typecast=True) -> dict[str, fields_t[str]]:
        """Export whole config or specified profile(s) (if profiles enabled).
        Also, by defaults, export only changed by user default and data fields
        :arg sections:          Selected section name(s) or all (if not provided)
        :arg strict_defaults:   Export all fields from default section (not skip equal to factory)
        :arg strict_data:       Export all fields from data sections (not skip equal to default)
        :arg typecast:          Force str type if field export_func result is not str
        :return:                Sections with fields raw values
        :raise InputError:      If wrong arguments provided
        :raise IOExportError:   Any other error"""
        cfg = self._cfg
        ie = (f'{self!r}.export_config()', 'profiles')
        try:
            result = {}
            if sections is not None and cfg.profiles is None:
                raise fmt_exc(ie, f'Profiles disabled, but provided: {sections!r}')

            # Export config support fields
            if support := self.export_section(self._key_section):
                result[self._key_section] = support

            # Export config defaults
            cds = cfg.def_sect
            result[cds] = self.export_section(cds, strict=strict_defaults, typecast=typecast)

            # Export config data
            if cfg.profiles:
                exists = cfg.profiles.get
                # bug mypy: profiles cannot be None here
                if (selected := as_holder(sections, exists)) != exists:                             # type: ignore[arg-type]
                    check_extra(selected, exists, 'profile', input_exc=ie)
                # bug mypy: k cannot be None here
                result |= {k: self.export_section(k, strict=strict_data, typecast=typecast)         # type: ignore[misc]
                           for k in selected}
            else:
                result[cfg.name] = self.export_section(strict=strict_data, typecast=typecast)
            return result

        except (InputError, IOExportError):
            raise
        except Exception as e:
            raise self._exc('export', repr(e)) from e  # not tested extreme case exception

    @staticmethod
    def _import_field(field: Field, raw_value: str, typecast: bool) -> Any:
        hook = _IMPORT_HOOKS.get(field.type, field.import_func)
        return check_type(hook(raw_value), field.type, typecast, 'field', False)

    def import_field(self, name: str, raw_value: str, typecast=True) -> Any:
        """Import single field to field type
        :arg name:          Field name
        :arg raw_value:     Field raw value
        :arg typecast:      Force field type if field import_func result has any other type
        :return:            Field value
        :raise FieldError:  Any error"""
        try:
            return self._import_field(self._cfg.get_fields[name], raw_value, typecast)
        except Exception as e:
            field = self._cfg.get_fields.get(name, None)
            kwargs = {} if field is None else {'by_func': GetName(field.import_func, code=True)}
            raise FieldError('Import', self._cfg.name, name, from_value=raw_value, **kwargs,
                             type_name=self._cfg.type_name, reason=repr(e)) from e

    def import_section(self, raw_section: fields_t[str], name: str | None = None, typecast=True
                       ) -> fields_t:
        """Import single section to dict with fields values
        note: Import section directly into the config is not available and may not be!
        :arg raw_section:       Fields raw values
        :arg name:              Section name (only for error message)
        :arg typecast:          Force field type if field import_func result has any other type
        :return:                Fields values
        :raise InputError:      If wrong arguments provided
        :raise IOImportError:   Any other error"""
        cfg = self._cfg
        fields = cfg.get_fields
        ie = (f'{self!r}.import_section()', 'raw_section')
        check_type(raw_section, Mapping, input_exc=ie)
        check_extra(raw_section, fields, 'field', input_exc=ie)
        try:
            result, errors = {}, []
            _import = self._import_field
            for key, raw_value in raw_section.items():
                field = fields[key]
                try:
                    result[key] = _import(field, raw_value, typecast)
                except Exception as e:
                    fn = GetName(field.import_func, code=True)
                    errors.append(_TEMPL_FIELD_DESC.format(key, with_type(raw_value), fn, e))
            if errors:
                raise CheckValueError("\n\t".join(('Errors:', *errors)))
            return result

        except CheckValueError as e:
            raise self._exc('import', str(e), name)
        except Exception as e:
            raise self._exc('import', repr(e), name) from e  # not tested extreme case exception

    def import_config(self, raw_config: Mapping[str, fields_t[str]],
                      sections: mb_holder_t[str] | None = None, typecast=True):
        """Import whole config, or specified section(s) from it
        :arg raw_config:        Sections with fields raw values
        :arg sections:          Selected section name(s) to import or all (if not provided)
        :arg typecast:          Force field type if field import_func result has any other type
        :return:                Sections with fields values
        :raise InputError:      If wrong arguments provided
        :raise IOImportError:   Any other error"""
        cfg = self._cfg
        def_sect = cfg.def_sect
        profiles = cfg.profiles
        fields = tuple(cfg.get_fields)
        ie_func = f'{self!r}.import_config()'
        ie_cfg = (ie_func, 'raw_config')
        ie_sect = (ie_func, 'sections')
        try:
            raw_config = dict(raw_config)

            # Import config support structure fields
            active = None
            active_fields = {}
            support = raw_config.pop(self._key_section, None)
            check_input(support, cfg.version or profiles, f'{self._key_section!r} section',
                        input_exc=ie_cfg)
            if support is not None:
                version = support.get(self._key_version)
                if version:
                    version = str(literal_eval(version))
                if check_input(version, cfg.version, 'version', input_exc=ie_cfg):
                    raise NotImplementedError('Version import is not available yet')

                active = support.get(self._key_profile)
                if active:
                    active = str(literal_eval(active))
                if check_input(active, profiles, 'profile', input_exc=ie_cfg):
                    if active not in raw_config and active != def_sect:
                        raise fmt_exc(ie_cfg, f'Active profile is not provided: {active!r}')

                    if self._key_fields in support:
                        active_fields_raw = support[self._key_fields]
                        try:
                            active_fields = dict(literal_eval(active_fields_raw))
                        except Exception as e:
                            raise fmt_exc(ie_cfg, 'Active fields dict is not parsed: '
                                                  f'{active_fields_raw!r}') from e
                        check_extra(active_fields, raw_config, 'active fields profile',
                                    input_exc=ie_cfg)
                        [check_extra(v, fields, f'{k!r} profile active field', input_exc=ie_cfg)
                         for k, v in active_fields.items()]

            # Check sections
            if sections:
                sections = as_holder(sections)
                if profiles:
                    selected = tuple(raw_config)
                else:
                    selected = ((def_sect,) if def_sect in raw_config else ()) + (cfg.name,)
                check_extra(sections, selected, 'section', input_exc=ie_sect)
                raw_config = {k: raw_config[k] for k in sections}

            # Import defaults
            if defaults := raw_config.pop(def_sect, {}):
                check_extra(defaults, fields, 'default field', input_exc=ie_cfg)
                defaults = self.import_section(defaults, def_sect, typecast)
            defaults = cfg.get_factory_defaults | defaults

            # Import data
            profiles_data = {}
            if profiles:
                for k, v in raw_config.items():
                    p_data = self.import_section(v, k, typecast)
                    if af := active_fields.get(k):
                        check_items(p_data, af, f'{k!r} profile field', input_exc=ie_cfg)
                        profiles_data[k] = {k: v for k, v in p_data.items() if k in af}
                    else:
                        profiles_data[k] = defaults | p_data
            else:
                data = defaults | self.import_section(raw_config[cfg.name], cfg.name, typecast)

            # Apply successfully imported data
            cfg.set_defaults(defaults, typecheck=False)
            if profiles:
                profiles.clear()
                [profiles.set(name, profile, defaults=False, typecheck=False)
                 for name, profile in profiles_data.items()]
                profiles.switch(active)
            else:
                cfg._set_fields(data)   # noqa

        except (InputError, IOImportError):
            raise
        except Exception as e:
            raise self._exc('import', repr(e)) from e
