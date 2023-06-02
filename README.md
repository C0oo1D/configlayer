## Configlayer: an attempt to simplify working with configurations

[![PyPI](https://img.shields.io/pypi/v/configlayer)](https://pypi.org/project/configlayer/)
![PyPI - Python Version](https://img.shields.io/pypi/pyversions/configlayer)
![GitHub License](https://img.shields.io/github/license/C0oo1D/configlayer)
[![Coverage](https://C0oo1D.github.io/configlayer/coverage.svg)](https://C0oo1D.github.io/configlayer/coverage/html/index.html)
[![Flake8](https://C0oo1D.github.io/configlayer/flake8.svg)](https://C0oo1D.github.io/configlayer/flake8/index.html)
![mypy](https://C0oo1D.github.io/configlayer/mypy.svg)
[![mypy-imprecise](https://C0oo1D.github.io/configlayer/mypy-imp.svg)](https://C0oo1D.github.io/configlayer/mypy/index.html)
![CI and CD](https://github.com/C0oo1D/configlayer/actions/workflows/ci_cd.yml/badge.svg)

| Python |                                                                Linux                                                                 |                                                                 Windows                                                                  |                                                                MacOS                                                                 |
|:------:|:------------------------------------------------------------------------------------------------------------------------------------:|:----------------------------------------------------------------------------------------------------------------------------------------:|:------------------------------------------------------------------------------------------------------------------------------------:|
|  3.10  | [![pytest](https://C0oo1D.github.io/configlayer/pytest_Linux_3.10.svg)](https://C0oo1D.github.io/configlayer/pytest/Linux_3.10.html) | [![pytest](https://C0oo1D.github.io/configlayer/pytest_Windows_3.10.svg)](https://C0oo1D.github.io/configlayer/pytest/Windows_3.10.html) | [![pytest](https://C0oo1D.github.io/configlayer/pytest_macOS_3.10.svg)](https://C0oo1D.github.io/configlayer/pytest/macOS_3.10.html) |
|  3.11  | [![pytest](https://C0oo1D.github.io/configlayer/pytest_Linux_3.11.svg)](https://C0oo1D.github.io/configlayer/pytest/Linux_3.11.html) | [![pytest](https://C0oo1D.github.io/configlayer/pytest_Windows_3.11.svg)](https://C0oo1D.github.io/configlayer/pytest/Windows_3.11.html) | [![pytest](https://C0oo1D.github.io/configlayer/pytest_macOS_3.11.svg)](https://C0oo1D.github.io/configlayer/pytest/macOS_3.11.html) |

### Features
Initially positioned as a convenient bridge between `dataclass` and `ConfigParser`,  
but later was split into optional modules and added extra functionality:
- **Profiles** module (cfg.profiles) - a lot of functions for config profiles manipulation:
  - Profiles: get, set, clear, rename and switch 
  - Groups: get and del, set at init only ('group' keyword)
- **I/O** module (cfg.io) - export/import functions, if needed custom save/load
- **File** module (cfg.file) - save/load functions for ini config files (use **I/O**)
- Config groups - simultaneous switch/rename of several configs profiles (use **profiles**)
- On set handlers (cfg.*_on_set) - calling a user-defined function for changed field(s)
- Options (cfg.options) - change defaults in several functions (waits rewrite in future)
- Data validation (implemented in **utils** module, but maybe `pydantic` should be used)
- Batch fields get (cfg.get_\*) - data, defaults, types, changed states, params, on_set handlers
- Batch fields set (cfg.set_\*) - data and defaults only
- Besides ConfigBase, there is also LanguageBase - use fixed 'language' group, and 'str' type

### Todo list

- Add docs..
- Add optional autosave (time interval, at exit)
- Add optional get_value_func and pooling_sec to Field (for environment variables, etc.)
- Add optional history of fields/profiles changes (for undo/redo)
- Add config versions (import from older configs by dev-provided functions)
- Add multiple configs in single file (if profiles disabled)
- Add modules support, for example \_\_init__(modules={'db': DataBaseBridge}) (cfg.db)
- Add several active profiles support (with different active fields, override by last one)
- Add logging..
- Do something with utils module - make a separate library or simplify it
- Rebuilt Options to set default methods params at init and change it during execution

----

### Installing

Recommended way (without '--user' - elevated privileges needed, if a system interpreter is used)

```sh
pip install --user configlayer
```

----

### Minimal usage example

```python
from configlayer import ConfigBase


class Config(ConfigBase):
    param: str = 'Some str'


data = Config('cfg.ini')  # Load from file if exists, else check save file possibility 
data.param = 'Another str'
data.cfg.file.save()
```

----

### Other examples

#### Common part

```python
from ast import literal_eval                # Needed only for custom fields import from str
from configlayer import ConfigBase, Field   # Field is needed only for custom fields I/O


# Configuration fields with types and factory defaults
class Config(ConfigBase):
    """Main"""  # optional verbose config name at first __doc__ line
    auto: bool = False
    tab: int = 0
    param: str = 'factory default'
    items: list = []
    items_custom_io: list = Field([], lambda x: f'{x}custom', lambda x: literal_eval(x[:-6]))
```

#### Simple config file

```python 
# Init config from file, if it exists
data = Config('config simple.ini')

# Set fields ways
data.param = 'field'
data.cfg.set_fields({'auto': True, 'items': ['some']})

# Set user defaults 
data.cfg.set_defaults({'tab': 1, 'items_custom_io': ['default']})

# Save changes to file (no autosave yet, planned)
data.cfg.file.save()
```

#### Profiles config file

```python
# Init config with profiles support (file has additional internal section)
data = Config('config profiles.ini', profiles=True)
profiles = data.cfg.profiles

# Set defaults ways (at this stage - default profile selected, set fields ways change defaults)
data.param = 'default'
data.cfg.set_fields({'auto': True, 'tab': 2})
data.cfg.set_defaults({'items': ['default'], 'items_custom_io': ['default']})

# Add new profiles and switch to it ways
profiles.set('Profile 1', {'auto': False, 'tab': 0})

## 'auto' and 'tab' at factory defaults, 'items' and 'items_custom_io' at user defaults
profiles.switch('Profile 1')

## the same as 'Profile 1', due to copy from currently selected profile
profiles.switch('Profile 2', add=True, add_current=True)

## all fields copied from user defaults
profiles.switch('Profile 3', add=True)

# Rename current profile
profiles.rename('New profile')

# Rename selected profile
profiles.rename('New profile 2', 'Profile 2')

# Save changes to file (no autosave yet, planned)
data.cfg.file.save()
```

#### Simple RAM-only config, with I/O operations

```python
# Init config only in RAM with export/import functions access
data1 = Config(io=True)
data1.param = 'field'
exported = data1.cfg.io.export_config()

data2 = Config(io=True)
data2.cfg.io.import_config(exported)
assert data1 == data2
```
