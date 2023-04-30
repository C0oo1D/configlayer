"""Internal config layer profiles support structure"""
from __future__ import annotations

from copy import deepcopy
from types import MappingProxyType
from typing import Any, Optional, Callable, Iterable

from .types import fields_t
from .utils import Locker, check_items, check_types, as_dict_stated, check_lengths, fmt_exc
from .exceptions import InputError, ProfilesError


class Profiles(Locker):
    """Profiles optional structure
    Used in config support structure if enabled, for config profiles operations"""
    __slots__ = ('_cfg', '_data', '_profiles', '_group', 'active', 'active_fields',
                 'before_switch', 'after_switch')
    _groups: dict[str, list[Profiles]] = dict()  # Common fixed class variable (dict methods only)
    _cfg: Any
    _data: Any
    _profiles: dict[str, tuple | dict]
    _group: str | None
    active: str
    active_fields: tuple
    before_switch: Optional[Callable]
    after_switch: Optional[Callable]

    def __init__(self, cfg, data, group: str | None = None):
        self._cfg = cfg
        self._data = data
        self._profiles = {}
        self._group = group
        self.before_switch = self.after_switch = None
        self.active = cfg.def_sect
        self.active_fields = tuple(cfg.get_fields)
        if group is not None:
            if group in self._groups:
                curr_group = self._groups[group]
                if (curr_active := curr_group[0].active) != self.active:
                    next(self._switch(curr_active, True, False))
                curr_group.append(self)
            else:
                self._groups[group] = [self]

        # Locks structure for changes with disabling attribute deletion and unlocked switch funcs
        super().__init__('before_switch', 'after_switch', del_attr=False, name=str(self))

    def __repr__(self):
        return f'{self._cfg!r}.profiles'

    def __str__(self):
        return f'{self._cfg.name!r} {self._cfg.type_name} profiles support structure'

    def __contains__(self, key):
        return self._profiles.__contains__(key)

    def __getitem__(self, key):
        cfg = self._cfg
        if key == cfg.def_sect:
            return tuple(cfg.get_defaults.values())
        if key == self.active:
            self.update()
        return self._profiles[key]

    def __delitem__(self, key):
        if key == self.active:
            if len(self._profiles) > 1:
                indexed = tuple(self._profiles)
                new_key = indexed[1 if (new := indexed.index(key)) == 0 else (new - 1)]  # -> or <-
            else:
                new_key = self._cfg.def_sect
            self.switch(new_key)
        del self._profiles[key]

    def clear(self):
        """Delete all profiles"""
        if self.active != (default := self._cfg.def_sect):
            self.switch(default)
        self._profiles.clear()

    @property
    def get(self) -> MappingProxyType[str, Any]:
        """Get profiles dict view"""
        self.update()
        return MappingProxyType(self._profiles)

    def set(self, name: str, data: fields_t | Iterable = (), *,
            defaults=True, typecheck=True, typecast=False):
        """Set profile data by name, with optional defaults filling, type checking and casting
        :arg name:              Target profile name
        :arg data:              Target profile data
        :arg defaults:          Fill missing fields by defaults and store strictly as tuple
        :arg typecheck:         Data types check
        :arg typecast:          Data types cast (if check failed)
        :raise InputError:      If wrong arguments provided
        :raise ProfilesError:   Any other error"""
        cfg = self._cfg
        fields = cfg.get_fields
        default_profile = name == cfg.def_sect
        func_name = f'{self!r}.set()'
        try:
            if data:
                mapping, items = as_dict_stated(data, fields)
                if not mapping:
                    check_lengths(tuple(data), fields, absent=False, input_exc=(func_name, 'data'))
                check_items(items, fields, 'field', str, absent=not (defaults or mapping),
                            input_exc=(func_name, 'data'))
                if typecheck:
                    items = check_types(items, {k: fields[k].type for k in items}, typecast,
                                        input_exc=(func_name, 'data'))
                if defaults:
                    items = cfg.get_defaults | items
            elif default_profile:
                raise InputError('data', func_name=func_name,
                                 msg='Cannot overwrite profile defaults with empty data')
            elif not defaults:
                raise InputError('data', func_name=func_name,
                                 msg='Cannot set profile with empty data and disabled defaults')
            else:
                items = cfg.get_defaults

            if default_profile:
                cfg.set_defaults(items)
            else:
                result = tuple(items.values()) if len(fields) == len(items) else items
                # bug mypy: no Sequence type, tuple or fields_t in previous line
                self._profiles[name] = deepcopy(result)                                             # type: ignore[assignment]
                if name == self.active:
                    with self:
                        self.active_fields = tuple(items)
                    cfg.set_fields(items)

        except InputError:
            raise
        except Exception as e:
            raise ProfilesError(f'Cannot set {name!r} profile to {cfg.name!r} config') from e

    def update(self):
        """Copy current config values to active profile. Used in self.switch() or manually"""
        cfg = self._cfg
        if self.active == cfg.def_sect:
            return  # Realized faster and automatically in ConfigBase.__set_field__

        data = cfg.get_data
        if len(profile := self._profiles[self.active]) != len(cfg.get_fields):
            self._profiles[self.active] = {k: data[k] for k in profile}
        else:
            self._profiles[self.active] = tuple(data.values())

    def _name_error(self, input_exc, name):
        return fmt_exc(input_exc, f'{name!r} profile in {self._cfg.name!r} config is not exists',
                       available=tuple(self._profiles))

    def _group_call(self, func_name: str, *args, revert=True):
        processed, errors = [], []
        # note mypy: self._group is not None if _group_call called
        for profile in self._groups[self._group]:                                                   # type: ignore[index]
            try:
                next(gen := getattr(profile, func_name)(*args))
                processed.append((profile._cfg.name, gen))
            except StopIteration:
                continue
            except Exception as e:
                errors.append(f'{profile._cfg.name}: {e!r}')
        if not errors:
            return

        # Prepare error message
        msg = '\n\t'.join((f'Some profiles in group {self._group!r} failed ' + '{}:', *errors))
        if not revert:
            return msg + '\nRevert disabled'

        # Revert processed profiles
        errors = []
        for profile_name, yielded in processed:
            try:
                next(yielded)
            except StopIteration:
                continue
            except Exception as e:
                errors.append(f'{profile_name}: {e!r}')
        return msg + '\nRevert ' + ('\n\t'.join(('failed:', *errors)) if errors else 'successful')

    def _rename_raw(self, new_name, old_name):
        if old_name == self.active:
            self.active = new_name
        self._profiles = {new_name if k == old_name else k: v for k, v in self._profiles.items()}

    def _rename(self, new_name, old_name):
        if old_name not in self._profiles:
            raise self._name_error((f'{self!r}.rename()', 'old_name'), old_name)
        with self:
            try:
                self._rename_raw(new_name, old_name)
            except Exception:
                self._rename_raw(old_name, new_name)
                raise
            yield
            return self._rename_raw(old_name, new_name)

    def rename(self, new_name: str, old_name: str | None = None):
        """Rename active or selected profile. Profiles in groups will also be renamed
        :arg new_name:          New profile name
        :arg old_name:          Target, or active (if not provided) profile name
        :raise InputError:      If wrong arguments provided
        :raise ProfilesError:   If any error at group operations"""
        # Check input
        if old_name is None:
            old_name = self.active
        if old_name == self._cfg.def_sect:
            raise InputError(msg=f'Cannot rename default profile to {new_name!r}',
                             func_name=f'{self!r}.rename()')

        # Single config profile rename
        if self._group is None:
            return next(self._rename(new_name, old_name))

        # Group configs profile rename
        if error := self._group_call('_rename', new_name, old_name):
            raise ProfilesError(error.format(f'rename from {old_name!r} to {new_name!r}'))

    def _switch_raw(self, name, cfg, data):
        if self.before_switch is not None:
            self.before_switch()

        fields = cfg.get_fields
        mapping, data_dict = as_dict_stated(self[name], fields, strict=True)
        with self:
            self.active = name
            self.active_fields = tuple(data_dict if mapping else fields)
        [setattr(data, *kv) for kv in data_dict.items()]

        if self.after_switch is not None:
            self.after_switch()

    def _switch_check(self, name, add, cfg):
        if (absent := name not in self and name != cfg.def_sect) and not add:
            raise self._name_error((f'{self!r}.switch()', 'name'), name)
        return absent

    def _switch(self, name, add, add_current, absent=None):
        cfg = self._cfg
        if (prev_name := self.active) == name:
            yield
            return

        # Check input and add data from default or current profile if enabled and profile is absent
        if absent is None:
            absent = self._switch_check(name, add, cfg)
        if absent and add:
            self.set(name, self.get[prev_name] if add_current else None, typecheck=False)

        # Save current profile values and switch with revert at fail
        self.update()
        try:
            self._switch_raw(name, cfg, self._data)
        except Exception:
            self._switch_raw(prev_name, cfg, self._data)
            raise
        yield
        return self._switch_raw(prev_name, cfg, self._data)

    def switch(self, name: str, add=False, add_current=False):
        """Switch active profile. Profiles in groups will also be switched
        :arg name:              Exists or new profile name (if :arg add: enabled)
        :arg add:               Adds profile with provided :arg name: if it not exists
        :arg add_current:       Replaces defaults with the active profile values, when it is added
        :raise InputError:      If wrong arguments provided
        :raise ProfilesError:   If any error at group operations"""
        # Check input
        if add_current and not add:
            raise InputError('add', 'add_current',
                             msg="Param 'add' must be True, when 'add_current' is True")
        absent = self._switch_check(name, add, self._cfg)

        # Single config profile switch
        if self._group is None:
            return next(self._switch(name, add, add_current, absent))

        # Group configs profile switch
        if error := self._group_call('_switch', name, add, add_current):
            raise ProfilesError(error.format(f'switch to {name!r}'))

    @property
    def get_groups(self) -> MappingProxyType[str, Any]:
        """Get groups dict view"""
        return MappingProxyType(self._groups)

    def del_group(self, name: str) -> list | None:
        """Delete provided group name
        :arg name:          Deleting group name
        :return:            List of deleted group config profiles
        :raise KeyError:    If :arg name: is not exists"""
        return self._groups.pop(name)
