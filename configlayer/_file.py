"""Internal config layer file support structure"""
from pathlib import Path
from configparser import ConfigParser

from .utils import Locker
from .types import path_t, mb_holder_t
from .exceptions import InitError, FileError


class File(Locker):
    """File optional structure
    Used in config support structure if file path provided, for local storage of configs"""
    __slots__ = ('_cfg', 'path')
    _used_paths: dict = dict()    # Common fixed class variable (dict methods only)
    path: Path

    def __init__(self, cfg, path: path_t):
        self._cfg = cfg
        if (path := Path(path)) in self._used_paths:
            raise InitError(f'Path "{path}" is already used in {self._used_paths[path]!r} config')

        self.path = path
        if path.exists():
            self.load()
        else:
            self.save()     # Create "empty" file for path correctness check, folder is not created
            path.unlink()   # Remove "empty" file
        self._used_paths[path] = cfg.name

        # Locks structure for changes with disabling attribute deletion
        super().__init__(del_attr=False)

    def __del__(self):
        """Remove path from used at config deletion"""
        if hasattr(self, 'path'):
            self._used_paths.pop(self.path, None)

    def __repr__(self):
        return f'{self._cfg!r}.file'

    def __str__(self):
        return f'{self._cfg.name!r} {self._cfg.type_name} file support structure'

    @staticmethod
    def _exc(op):
        def init_wrapper(func):
            def method_wrapper(self, *args, **kwargs):
                try:
                    return func(self, *args, **kwargs)
                except FileNotFoundError as e:
                    msg = e.args[1]
                except FileError as e:
                    msg = e
                except Exception as e:
                    raise FileError(f'{op} "{self.path}" failed. {e!r}') from e
                raise FileError(f'{op} "{self.path}" failed. {msg}')
            return method_wrapper
        return init_wrapper

    def _get_config(self):
        config = ConfigParser(default_section=f'_{self._cfg.def_sect}')  # hidden reserved name
        config.optionxform = str
        return config

    @_exc('Save to')
    def save(self, sections: mb_holder_t[str] | None = None, *,
             strict_defaults=False, strict_data=False):
        """Save config to file (or only selected sections, excepting internal)
        :arg sections:          Selected section name(s) or all (if not provided)
        :arg strict_defaults:   Save all fields from default section (not skip equal to factory)
        :arg strict_data:       Save all fields from data sections (not skip equal to default)
        :raise InputError:      If wrong arguments provided
        :raise IOExportError:   If errors during export_config"""
        config = self._get_config()
        config.read_dict(self._cfg.io.export_config(sections, strict_defaults=strict_defaults,
                                                    strict_data=strict_data, typecast=True))
        with self.path.open('w', encoding='utf-8') as file:
            config.write(file)

    @_exc('Load from')
    def load(self, sections: mb_holder_t[str] | None = None):
        """Load config from file (or only selected sections, excepting internal)
        :arg sections:          Selected section name(s) or all (if not provided)
        :raise InputError:      If wrong arguments provided
        :raise IOImportError:   If errors during import_config
        :raise FileError:       If file contains forbidden default section"""
        config = self._get_config()
        hidden_default_sect = f'_{self._cfg.def_sect}'

        # Raw check for provided real default section (not used due to internal section impact)
        error = False
        with self.path.open('r', encoding='utf-8') as file:
            config.read_file(file)
            file.seek(0)
            for line in file.readlines():
                if line.startswith(f'[{hidden_default_sect}]'):
                    error = True
                    break

        # Process data as dicts and raise an error if real default section provided
        data = {k: dict(v) for k, v in config.items()}
        if (wrong := data.pop(hidden_default_sect)) or error:
            details = f'. Data: {wrong}' if wrong else ''
            raise FileError(f'{hidden_default_sect!r} section is forbidden, but provided{details}')
        self._cfg.io.import_config(data, sections)
