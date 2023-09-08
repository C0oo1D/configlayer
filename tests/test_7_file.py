from gc import collect
from itertools import product
from pathlib import Path

from configlayer.exceptions import InitError, FileError, IOImportError, InputError

from _utilities import raises_init, subtest
from _data import TEMP_PATH, Config1, Config1Alias, Config2, Config3, Config4, exp_strict


def test_init():
    collect()

    # Create config with wrong file path
    wrong_path = 'not_exists_dir/test_config.ini'
    fe = FileError(f'Save to "{Path(wrong_path)}" failed. No such file or directory')
    raises_init(fe, Config2, wrong_path)

    # Create config, must be no file created
    TEMP_PATH.unlink(missing_ok=True)
    data = Config1(TEMP_PATH)
    assert not TEMP_PATH.exists()

    # Several configs at single file check
    ie = InitError(f"Path \"{TEMP_PATH}\" is already used in 'Config1' config")
    raises_init(ie, Config1, TEMP_PATH)
    raises_init(ie, Config2, TEMP_PATH)

    # Remove config from memory to free temp path for other configs
    data.cfg.file.save()
    del data
    collect()

    # Import file at temp path from other config
    ke = KeyError('Valid fields')
    ie = IOImportError(f"Cannot import 'Valid fields' config. {ke!r}")
    fe = FileError(f"Load from \"{TEMP_PATH}\" failed. {ie!r}")
    raises_init((fe, ie, ke), Config2, TEMP_PATH)


def test_save():
    collect()

    sect_name = 'Config1'
    defaults = {'v_str': "'mod'"}
    def_data = {'v_bool': 'True', 'v_str': "'Some string'"}
    for (profiles, ud), bd, bv in product([(False, True), (True, True), (True, False)],
                                          [False, True],
                                          [False, True]):
        TEMP_PATH.unlink(missing_ok=True)
        data = Config1(TEMP_PATH, profiles=bool(profiles))
        if profiles:
            data.cfg.profiles.set(sect_name, {'v_bool': False}, defaults=ud)
            data.cfg.profiles.switch(sect_name)
        data.v_bool = True
        data.cfg.set_defaults({'v_str': 'mod'})

        data.cfg.file.save(strict_defaults=bd, strict_data=bv)
        result = []

        # Internal section in file
        if profiles:
            result.extend((f'[{data.cfg.io._key_section}]', f'profile = {sect_name!r}'))
            if not ud:
                result.append("fields = {'Config1': ('v_bool',)}")
            result.append('')

        # Default section in file
        result.append('[DEFAULT]')
        result.extend(f'{k} = {v}' for k, v in ((exp_strict if bd else {}) | defaults).items())

        # Data section in file
        result.extend(('', f'[{sect_name}]'))
        if ud:
            result.extend(f'{k} = {v}' for k, v in ((exp_strict if bv else {}) | def_data).items())
        else:
            result.append("v_bool = True")

        assert TEMP_PATH.read_text(encoding='utf-8').rstrip() == '\n'.join(result)

        del data
        collect()


def test_load():
    collect()

    # Get simple and profiles test files paths separately
    sp, pp = [], []
    [(sp if '_s' in x.name else pp).append(x) for x in TEMP_PATH.parent.glob('test_config_*.ini')]

    # Linux and macOS glob output is unsorted
    sp.sort()
    pp.sort()

    # Get all available configs
    cfgs = (Config1, Config1Alias, Config2, Config3, Config4)

    # Wrong files check
    def fmt_exc(fp, exc):
        if isinstance(exc, Exception):
            return FileError(f'Load from "{fp}" failed. {exc!r}'), exc
        return FileError(f'Load from "{fp}" failed. {exc}')

    wsp = TEMP_PATH.with_name('test_wrong_s.ini')
    ds = "'_DEFAULT' section is forbidden, but provided"
    raises_init(fmt_exc(wsp, ds), Config1, wsp, profiles=False)

    wpp = TEMP_PATH.with_name('test_wrong_p.ini')
    dsv = ds + ". Data: {'some key': \"'some value'\"}"
    raises_init(fmt_exc(wpp, dsv), Config1, wpp, profiles=True)

    def fmt_ie(cls, provided=False):
        args = ('', ' not') if provided else (' not', '')
        return InputError('raw_config', func_name=f'{cls.__name__}.cfg.io.import_config()',
                          msg="'_CONFIG_LAYER' section is{} needed, but{} provided".format(*args))

    [raises_init(fmt_exc(p, fmt_ie(c)), c, p, profiles=False) for c, p, in product(cfgs, pp)]
    [raises_init(fmt_exc(p, fmt_ie(c, True)), c, p, profiles=True) for c, p, in product(cfgs, sp)]

    # Check simple
    se = (({}, {}),
          ({'v_bool': True}, {'v_str': 'Some', 'v_int': 5}),
          ({}, {'v_int': 5}),
          ({'v_int': 5}, {'c3': 'c5'}),
          ({'v_str': 'some str', 'C4': 1}, {'C4': 44}))
    dataset = zip(cfgs, sp, se, strict=True)
    for i, cfg_cls, path, (ed, ef) in (st := subtest('Simple', 5, dataset)):
        data = cfg_cls(path)
        defaults = data.cfg.get_factory_defaults | ed
        st.send(('defaults', data.cfg.get_defaults, defaults))
        st.send(('data', data.cfg.get_data, defaults | ef))

    # Check profiles
    pe = (('DEFAULT', {}, {}),
          ('DEFAULT', {}, {'config_2': {}}),
          ('config_3', {'v_bool': True}, {'config_3': {'v_str': 'Some', 'v_int': 5}}),
          ('config_4', {'v_bool': True}, {'config_4': {'v_str': 'Some', 'v_int': 5}}))
    dataset = product(cfgs, zip(pp, pe, strict=True))
    for i, cfg_cls, (path, (active, ed, ep)) in (st := subtest('Profiles', 20, dataset)):
        data = cfg_cls(path, profiles=True)
        dp = data.cfg.profiles

        defaults = data.cfg.get_factory_defaults | ed
        st.send(('defaults', data.cfg.get_defaults, defaults))
        st.send(('data', data.cfg.get_data, defaults | ep.get(dp.active, {})))
        st.send(('active', dp.active, active))
        profiles = {k: v if active == 'config_4' else tuple((defaults | v).values())
                    for k, v in ep.items()}
        st.send(('profiles', dp._profiles, profiles))

        del data
        collect()
