from functools import partial
from itertools import product

from configlayer.exceptions import (InputError, CheckValueError, CheckTypeError,
                                    FieldError, IOExportError, IOImportError)
from configlayer.utils import safe, as_holder, is_exception

from _utilities import raises_init, raises, subtest
from _data import (WrongExportRepr, WrongExportFunc, WrongExportType, WrongImportEval,
                   WrongImportFunc, WrongImportResult, WrongReprType, ExportSensitive,
                   Config1, Config2, Config3, Config4, Lang1, exp_strict, imp_strict, OwnInt)


def test_init():
    # Correct
    assert Config1(io=True)

    # Error at export fields check
    exc1e = TypeError("Wrong repr!")
    exc1ef = FieldError('Export', 'WrongExportRepr', 'test', from_value=exc1e, by_func='repr',
                        reason=repr(exc1e))
    raises_init((exc1ef, exc1e), WrongExportRepr, io=True)

    exc2e = TypeError("Wrong func!")
    exc2ef = FieldError('Export', 'WrongExportFunc', 'test', from_value=5, by_func='wrong_func',
                        reason=repr(exc2e))
    raises_init((exc2ef, exc2e), WrongExportFunc, io=True)

    exc3e = TypeError("__repr__ returned non-string (type WrongReprType)")
    exc3ef = FieldError('Export', 'WrongExportType', 'test', from_value=exc3e, by_func='repr',
                        reason=repr(exc3e))
    raises_init((exc3ef, exc3e), WrongExportType, io=True)

    # Error at import fields check
    exc1i = SyntaxError('invalid syntax', ('<unknown>', 1, 6, 'Eval it!', 1, 8))
    exc1if = FieldError('Import', 'WrongImportEval', 'test', from_value='Eval it!',
                        by_func='literal_eval', reason=repr(exc1i))
    raises_init((exc1if, exc1i), WrongImportEval, io=True)

    exc2i = TypeError("Wrong func!")
    exc2if = FieldError('Import', 'WrongImportFunc', 'test', from_value='5', by_func='wrong_func',
                        reason=repr(exc2i))
    raises_init((exc2if, exc2i), WrongImportFunc, io=True)

    # Error at compare default fields with imported during check
    msg = ("'WrongImportResult' config IO check failed:\n\tField test=5 (int) must be equal "
           "imported=6 (int): export_func = 'repr', exported = '5', import_func = 'increment_str'")
    raises_init(CheckValueError(msg), WrongImportResult, io=True)


def test_repr_str():
    for cls, str1, str2 in (
            [Config1, "Config1.cfg.io", "'Config1' config I/O support structure"],
            [Config2, "Config2.cfg.io", "'Valid fields' config I/O support structure"],
            [Config3, "Config3.cfg.io", "'Gotcha' config I/O support structure"],
            [Config4, "Config4.cfg.io", "'IO' config I/O support structure"],
            [Lang1, "Lang1.cfg.io", "'Random' language I/O support structure"]):
        obj = cls(io=True).cfg.io
        assert repr(obj) == str1
        assert str(obj) == str2

    Lang1().cfg.profiles.del_group('Language')


def test_export_field():
    wfn = 'v_not_exists'                # Wrong field name
    wrv = WrongReprType()               # Wrong repr value
    cfn = 'v_list'                      # Correct field name
    ccv = [{'s': 4}, 1, 0.7, 'data']    # Correct custom value
    ccr = "[{'s': 4}, 1, 0.7, 'data']"  # Correct custom result

    # Correct
    cfg = Config1(io=True).cfg
    export_field = cfg.io.export_field
    assert export_field(cfn) == "[-1, 0, 1, 'repeat €₽']"
    assert export_field(cfn, ccv) == ccr
    assert export_field(cfn, ccv, True) == ccr
    assert export_field(cfn, ccv, False) == ccr

    exp_fields = list(exp_strict.values())
    assert [export_field(k) for k in cfg.get_fields] == exp_fields
    assert [export_field(k, v.default) for k, v in cfg.get_fields.items()] == exp_fields
    assert [export_field(k, v.default, True) for k, v in cfg.get_fields.items()] == exp_fields
    assert [export_field(k, v.default, False) for k, v in cfg.get_fields.items()] == exp_fields

    # Errors
    exc = partial(FieldError, 'Export', cfg.name)

    exc_key = KeyError(wfn)
    raises((exc(wfn, reason=repr(exc_key)), exc_key), export_field, wfn)
    raises((exc(wfn, reason=repr(exc_key), from_value=ccv), exc_key), export_field, wfn, ccv)

    exc_type = TypeError("__repr__ returned non-string (type WrongReprType)")
    raises((exc(cfn, reason=repr(exc_type), from_value=exc_type, by_func='repr'), exc_type),
           export_field, cfn, wrv)


def test_export_section():
    name1, name2 = 'name1', 'name2'
    i1_, i1m = {'v_bool': False}, {'v_bool': True}
    o1_, o1m = {'v_bool': 'False'}, {'v_bool': 'True'}
    i2_, i2m = {'v_int': 65535}, {'v_int': 32767}
    o2_, o2m = {'v_int': '65535'}, {'v_int': '32767'}
    exp = exp_strict
    imp = imp_strict

    # Init single and profile configs related data
    data_s = Config1(io=True)
    data_p = Config1(io=True, profiles=True)
    cfg_s = data_s.cfg
    cfg_p = data_p.cfg
    profiles = cfg_p.profiles
    key_section = cfg_s.io._key_section
    def_section = cfg_s.def_sect
    ess = cfg_s.io.export_section
    esp = cfg_p.io.export_section

    # Export provided section (single and profile)
    assert ess({}) == esp({}) == ess(i1_) == ess(i1_) == {}
    assert (ess({}, strict=True) == esp({}, strict=True) == ess(i1_, strict=True)
            == esp(i1_, strict=True) == exp)
    assert ess(i1m) == esp(i1m) == o1m
    assert ess(i1m, strict=True) == esp(i1m, strict=True) == exp | o1m

    cfg_s.set_defaults(i1m)
    cfg_p.set_defaults(i1m)
    assert ess({}) == esp({}) == ess(i1m) == ess(i1m) == {}
    assert (ess({}, strict=True) == esp({}, strict=True) == ess(i1m, strict=True)
            == esp(i1m, strict=True) == exp | o1m)
    assert ess(i1_) == esp(i1_) == o1_
    assert ess(i1_, strict=True) == esp(i1_, strict=True) == exp
    cfg_s.set_defaults(i1_)
    cfg_p.set_defaults(i1_)

    # Export internal section (single and profile)
    assert ess(key_section) == ess(key_section, strict=True) == {}
    assert esp(key_section) == esp(key_section, strict=True) == {'profile': repr(def_section)}
    profiles.switch(name1, True)
    assert esp(key_section) == esp(key_section, strict=True) == {'profile': repr(name1)}
    profiles.set(name2, {'v_bool': False, 'v_int': 5}, defaults=False)
    assert (esp(key_section) == esp(key_section, strict=True)
            == {'profile': repr(name1), 'fields': "{'name2': ('v_bool', 'v_int')}"})

    # Export default section (single and profile)
    assert ess(def_section) == esp(def_section) == {}
    assert ess(def_section, strict=True) == esp(def_section, strict=True) == exp

    profiles.switch(def_section)
    cfg_s.set_defaults(i1m)
    cfg_p.set_defaults(i1m)
    assert ess(def_section) == esp() == esp(def_section) == o1m

    # Export section (single)
    assert ess() == ess(cfg_s.name) == o1_
    assert ess(strict=True) == ess(cfg_s.name, strict=True) == exp

    data_s.v_bool = True
    assert ess() == ess(cfg_s.name) == {}
    assert ess(strict=True) == ess(cfg_s.name, strict=True) == exp | o1m

    cfg_s.set_defaults(i1_)
    assert ess() == ess(cfg_s.name) == o1m
    assert ess(strict=True) == ess(cfg_s.name, strict=True) == exp | o1m

    data_s.v_bool = False
    assert ess() == ess(cfg_s.name) == {}
    assert ess(strict=True) == ess(cfg_s.name, strict=True) == exp

    # Export section (profile)
    msg = 'Defaults v_bool state | Profile name {key: value} | short or strict export'
    st = subtest(msg, 8, product([(False, False, i1_, i1m, o1_, o1m),
                                  (False, True,  i2_, i2m, o2_, o2m),
                                  (True,  False, imp | i1_, imp | i1m, exp | o1_, exp | o1m),
                                  (True,  True,  imp | i2_, imp | i2m, exp | o2_, exp | o2m)],
                                 [False, True]))
    for i, (strict, crossing, i_def, i_mod, o_def, o_mod), defaults in st:
        full = strict or defaults
        cfg_p.set_defaults(i1_)
        profiles.set(name1, i_def, defaults=defaults)
        profiles.set(name2, i_mod, defaults=defaults)
        for def_i1m in (False, True):
            if def_i1m:
                cfg_p.set_defaults(i1m)

            # result name1 (default, short)
            rn1d = {} if not def_i1m or crossing and not full else o1_

            # result name2 (modified, short)
            if crossing:
                rn2m = (o1_ | o2m) if def_i1m and full else o2m
            else:
                rn2m = {} if def_i1m else o1m

            # results strict name1 and name2 (default and modified)
            rn1ds, rn2ms = (exp, exp | o_mod) if full else (o_def, o_mod)

            # check
            for name, res, res_strict in ((name1, rn1d, rn1ds), (name2, rn2m, rn2ms)):
                profiles.switch(name)

                val = i_def if name == name1 else i_mod
                if strict:
                    val = (repr({k: v for k, v in val.items() if k in ('v_bool', 'v_int')})[:-1]
                           + ', ...}')
                msg = f'{str(def_i1m):>5} | {name} {str(val):<17} | '

                st.send((msg + ' short', esp(), esp(name), res))
                st.send((msg + 'strict', esp(strict=True), esp(name, strict=True), res_strict))

    # Errors
    def names(target):
        return repr(tuple(target))[1:-1]

    cfg_e = ExportSensitive(io=True).cfg
    exp_sens = cfg_e.io.export_section
    if1 = {'wrong_name': 'wrong_data'}
    if2 = {'some_name': 'some_data'}
    if3 = {'f1': [1]}
    if4 = {'f2': 2}

    ie = "Provided wrong parameter to {}.cfg.io.export_section(): section. "
    add = f"Must be not more than expected ({names(cfg_s.get_fields)}), but received"
    add2 = f"Must be not more than expected ({names(cfg_e.get_fields)}), but received"
    ie1 = "[[]] (list) must be Mapping type"
    ie2 = f"Extra field: 'wrong_name'. {add}: {names(imp | if1)}"
    ie3 = f"Extra fields: 'wrong_name', 'some_name'. {add}: {names(imp | if1 | if2)}"
    ie4 = f"Extra fields: 'wrong_name', 'some_name'. {add2}: {names(if1 | if2 | if3 | if4)}"
    ie5 = "Profile is not exists, there is no profiles"
    ie6 = "Profile is not exists, available profiles: 'name1', 'name2'"
    ie7 = "Must be 'Config1', but received 'nes'"
    raises(InputError(msg=ie.format('Config1') + ie1), esp, [[]])
    raises(InputError(msg=ie.format('Config1') + ie2), esp, imp | if1)
    raises(InputError(msg=ie.format('Config1') + ie3), esp, imp | if1 | if2)
    raises(InputError(msg=ie.format('ExportSensitive') + ie4), exp_sens, if1 | if2 | if3 | if4)
    raises(InputError(msg=ie.format('Config1') + ie5),
           Config1(io=True, profiles=True).cfg.io.export_section, 'nes')
    raises(InputError(msg=ie.format('Config1') + ie6), esp, 'nes')
    raises(InputError(msg=ie.format('Config1') + ie7), ess, 'nes')

    msg = "Cannot export 'ExportSensitive' config section. Errors:"
    f1 = "Field f1=[1] (list) by <lambda>: CheckTypeError('Field [1] (list) must be str type')"
    f2 = "Field f2=2 (int) by <lambda>: CheckTypeError('Field 2 (int) must be str type')"
    raises(IOExportError(msg + f"\n\t{f1}"), exp_sens, if3, typecast=False)
    raises(IOExportError(msg + f"\n\t{f1}\n\t{f2}"), exp_sens, if3 | if4, typecast=False)


def test_export_configs():
    # Prepare simple config data
    data_s = Config4(io=True)
    data_s.C4 = 10
    ecs = data_s.cfg.io.export_config

    # Section names
    sec_internal = data_s.cfg.io._key_section
    sec_default = data_s.cfg.def_sect
    sec_simple = 'IO'
    sec_profile1 = 'profile1'
    sec_profile2 = 'Profile 2'

    # Section values
    val_internal = {'profile': repr(sec_default)} | {'fields': "{'profile1': ('C4',)}"}
    val_default = {'C4': '4'}
    val_modified = {'C4': '10'}

    # Prepare profiles config data
    data_p = Config4(io=True, profiles=True)
    data_p.C4 = 10
    data_p.cfg.profiles.set(sec_profile1, val_default, typecast=True, defaults=False)
    data_p.cfg.profiles.set(sec_profile2)
    ecp = data_p.cfg.io.export_config

    # Internal section completed
    ip_ = {sec_internal: val_internal}

    # Default sections completed
    ds_ = {sec_default: {}}
    dp_ = {sec_default: val_modified}
    dss = {sec_default: exp_strict | val_default}
    dps = {sec_default: exp_strict | val_modified}

    # Simple config section completed
    vs_ = {sec_simple: val_modified}
    vss = {sec_simple: exp_strict | val_modified}

    # Profiles config section completed
    vp_1 = {sec_profile1: val_default}
    vp_2 = {sec_profile2: {}}
    vps2 = {sec_profile2: exp_strict | val_modified}

    # Exceptions
    exc_ie = partial(InputError, 'profiles', func_name='Config4.cfg.io.export_config()')
    msg_disabled = "Profiles disabled, but provided"
    msg_extra = ("Extra profile: ''. "
                 "Must be not more than expected ('profile1', 'Profile 2'), but received: ''")

    def fmt_cte(section, value):
        inner_exc = CheckTypeError(f'Field {value} (int) must be str type')
        return IOExportError(f"Cannot export 'IO' config section {section!r}. Errors:\n"
                             f"\tField C4={value} (int) by <lambda>: {inner_exc!r}")

    # Build subtest dataset
    profiles_set = [None, '', sec_profile1, [sec_profile1], [sec_profile1, sec_profile2]]
    cases = product(profiles_set, *((False, True),) * 3)
    names = ('profiles', 'strict_defaults', 'strict_data', 'typecast')

    # Run subtest
    for i, profiles, s_def, s_data, typecast in (st := subtest('', 40, cases, names=names)):
        kwargs = dict(zip(names[1:], (s_def, s_data, typecast), strict=True))

        # Prepare simple result
        if profiles is None:
            if typecast:
                rs = (dss if s_def else ds_) | (vss if s_data else vs_)
            else:
                rs = fmt_cte(sec_default, 4) if s_def else fmt_cte(sec_simple, 10)
        else:
            rs = exc_ie(msg=f'{msg_disabled}: {profiles!r}')

        # Prepare profiles result
        if not typecast:
            rp = fmt_cte(sec_default, 10)
        elif profiles == '':
            rp = exc_ie(msg=msg_extra)
        else:
            rp = ip_ | (dps if s_def else dp_)
            if profiles is None or sec_profile1 in profiles:
                rp |= vp_1
            if profiles is None or sec_profile2 in profiles:
                rp |= (vps2 if s_data else vp_2)

        # Test both
        for name, target, result in (('simple', ecs, rs), ('profiles', ecp, rp)):
            if any(map(is_exception, results := as_holder(result))):
                try:
                    raises(result, target, profiles, **kwargs)
                except Exception as e:
                    st.send(('', type(e).__name__, results[0]))
                else:
                    st.send((f'Exception {name}', results[0], results[0]))
            else:
                st.send((f'Result {name}', safe(target, profiles, **kwargs), result))


def test_import_field():
    wfn = 'v_not_exists'                # Wrong field name
    wev = 'wrong value'                 # Wrong eval value
    wrv = WrongReprType()               # Wrong repr value
    wcv = "'wrong value'"               # Wrong custom value
    cfn = 'v_list'                      # Correct field name
    ccv = "[{'s': 4}, 1, 0.7, 'data']"  # Correct custom value
    ccr = [{'s': 4}, 1, 0.7, 'data']    # Correct custom result

    # Correct
    cfg = Config1(io=True).cfg
    split_i = tuple(cfg.get_types.values()).index(OwnInt)
    import_field = cfg.io.import_field
    assert import_field(cfn, ccv) == ccr
    assert import_field(cfn, ccv, True) == ccr
    assert import_field(cfn, ccv, False) == ccr

    exp_values = list(exp_strict.values())
    exp_f_std, exp_f_safe = exp_values[:split_i], exp_values[split_i + 1:]

    imp_values = list(imp_strict.values())
    imp_f_std, imp_f_safe = imp_values[:split_i], imp_values[split_i + 1:]

    names_safe = list(exp_strict)[split_i + 1:]

    exp_dict = dict(zip(cfg.get_fields, exp_f_std + ['5'] + exp_f_safe))
    imp_list = imp_f_std + [OwnInt(5)] + imp_f_safe

    exp_dict_safe = dict(zip(cfg.get_fields, exp_f_std)) | dict(zip(names_safe, exp_f_safe))
    imp_list_safe = imp_f_std + imp_f_safe

    assert [import_field(k, v) for k, v in exp_dict.items()] == imp_list
    assert [import_field(k, v, True) for k, v in exp_dict.items()] == imp_list
    assert [import_field(k, v, False) for k, v in exp_dict_safe.items()] == imp_list_safe

    # Errors
    exc_field = partial(FieldError, 'Import', cfg.name)

    exc1 = CheckTypeError('Field 5 (int) must be OwnInt type')
    exc1f = exc_field('v_cust1', from_value='5', by_func='literal_eval', reason=repr(exc1))
    raises((exc1f, exc1), import_field, 'v_cust1', '5', False)

    exc2 = KeyError(wfn)
    exc2f = exc_field(wfn, from_value=ccv, reason=repr(exc2))
    raises((exc2f, exc2), import_field, wfn, ccv)

    exc3 = SyntaxError('invalid syntax', ('<unknown>', 1, 7, wev, 1, 12))
    exc3f = exc_field(cfn, from_value=wev, by_func='literal_eval', reason=repr(exc3))
    raises((exc3f, exc3), import_field, cfn, wev)

    exc4 = TypeError("__repr__ returned non-string (type WrongReprType)")
    exc4f = exc_field(cfn, from_value=wrv, by_func='literal_eval', reason=repr(exc4))
    raises((exc4f, exc4), import_field, cfn, wrv)

    exc5 = CheckTypeError("Field 'wrong value' (str) must be list type")
    exc5f = exc_field(cfn, from_value=wcv, by_func='literal_eval', reason=repr(exc5))
    raises((exc5f, exc5), import_field, cfn, wcv, typecast=False)


def test_import_section():
    exp = exp_strict
    exp2 = exp.copy()
    exp2['v_bool'] = 'True'

    # i1_, i1m = {'v_bool': 'False'}, {'v_bool': 'True'}
    # o1_, o1m = {'v_bool': False}, {'v_bool': True}
    i2m = {'v_int': '32767'}
    o2m = {'v_int': 32767}

    imp = imp_strict
    imp2 = imp.copy()
    imp2['v_bool'] = True

    cfg_s = Config1(io=True).cfg
    cfg_p = Config1(io=True, profiles=True).cfg
    iss = cfg_s.io.import_section
    isp = cfg_p.io.import_section

    # Not change data in configs (single and profile)
    assert iss(i2m) == isp(i2m) == o2m
    assert cfg_s.get_data == cfg_p.get_data == cfg_s.get_defaults == cfg_p.get_defaults == imp

    assert iss(exp) == isp(exp) == imp
    assert cfg_s.get_data == cfg_p.get_data == cfg_s.get_defaults == cfg_p.get_defaults == imp

    assert iss(exp2) == isp(exp2) == imp2
    assert cfg_s.get_data == cfg_p.get_data == cfg_s.get_defaults == cfg_p.get_defaults == imp

    # Change data in configs (single)
    pass  # Not implemented

    # Change data in configs (profile)
    pass  # Not implemented

    # Errors
    def names(target):
        return repr(tuple(target))[1:-1]

    add = f"Must be not more than expected ({names(cfg_s.get_fields)}), but received"

    ef1 = {'wrong_name': 'wrong_data'}
    ef2 = {'some_name': 'some_data'}
    ef3 = {'v_int': 13}
    ef4 = {'v_dict': 1}

    ie = "Provided wrong parameter to Config1.cfg.io.import_section(): raw_section. "
    ie1 = "[[]] (list) must be Mapping type"
    ie2 = f"Extra field: 'wrong_name'. {add}: {names(exp | ef1)}"
    ie3 = f"Extra fields: 'wrong_name', 'some_name'. {add}: {names(exp | ef1 | ef2)}"
    ie4 = f"Extra fields: 'wrong_name', 'some_name'. {add}: {names(exp | ef1 | ef2 | ef3 | ef4)}"
    raises(InputError(msg=ie + ie1), iss, [[]])
    raises(InputError(msg=ie + ie1), isp, [[]])
    raises(InputError(msg=ie + ie2), iss, exp | ef1)
    raises(InputError(msg=ie + ie2), isp, exp | ef1)
    raises(InputError(msg=ie + ie3), iss, exp | ef1 | ef2)
    raises(InputError(msg=ie + ie3), isp, exp | ef1 | ef2)
    raises(InputError(msg=ie + ie4), iss, exp | ef1 | ef2 | ef3 | ef4)
    raises(InputError(msg=ie + ie4), isp, exp | ef1 | ef2 | ef3 | ef4)

    msg = "Cannot import 'Config1' config section"
    p1 = "Field v_int=13 (int) by literal_eval: ValueError('malformed node or string: 13')"
    p2 = "Field v_dict=1 (int) by literal_eval: ValueError('malformed node or string: 1')"
    raises(IOImportError(msg + f". Errors:\n\t{p1}"), iss, exp | ef3)
    raises(IOImportError(msg + f". Errors:\n\t{p1}"), isp, exp | ef3)
    raises(IOImportError(msg + f". Errors:\n\t{p1}\n\t{p2}"), iss, exp | ef3 | ef4)
    raises(IOImportError(msg + f". Errors:\n\t{p1}\n\t{p2}"), isp, exp | ef3 | ef4)


def test_import_config():
    # Prepare simple and profiles configs
    data_s = Config4(io=True)
    data_p = Config4(io=True, profiles=True)
    ics = data_s.cfg.io.import_config
    icp = data_p.cfg.io.import_config
    df = exp_strict | {'C4': '4'}                       # default fields

    # Internal section keys
    kiv = data_s.cfg.io._key_version
    kip = data_s.cfg.io._key_profile
    kif = data_s.cfg.io._key_fields

    # Values
    e1m, i1m = {'v_bool': 'True'}, {'v_bool': True}
    e2_ = {'v_int': '65535'}
    e2m, i2m = {'v_int': '32767'}, {'v_int': 32767}

    # Sections names
    internal = data_s.cfg.io._key_section
    default_ = data_s.cfg.def_sect
    simple__ = 'IO'
    profile_ = 'p1'

    # Exported values
    ev_d_ = e2m                                                 # default
    ev_s_ = e1m | e2_                                           # simple
    ev_p_ = ev_s_ | ev_d_                                       # profile
    ev_f_ = e1m                                                 # fields active
    ev_id = {kip: repr(default_)}                               # internal default
    ev_ip = {kip: repr(profile_)}                               # internal profile
    ev_if = {kip: repr(profile_), kif: "{'p1': ('v_bool',)}"}   # internal fields (profiles active)

    # 1. Exported Simple
    s___ed_ = {default_: {} | ev_d_}                            # default
    s___eds = {default_: df | ev_d_}                            # default strict
    s___es_ = {simple__: {} | ev_s_}                            # section
    s___ess = {simple__: df | ev_s_}                            # section strict

    # 2. Exported Profiles: default
    pd__ed_ = {internal: ev_id, default_: {} | ev_p_}           # default
    pd__eds = {internal: ev_id, default_: df | ev_p_}           # default strict
    pd__es_ = {}                                                # section
    pd__ess = {}                                                # section strict

    # 3. Exported Profiles: default, active fields
    # The same as 2, because default profile always have all fields active

    # 4. Exported Profiles: profile
    pp__ed_ = {internal: ev_ip, default_: {} | ev_d_}           # default
    pp__eds = {internal: ev_ip, default_: df | ev_d_}           # default strict
    pp__es_ = {profile_: {} | ev_s_}                            # section
    pp__ess = {profile_: df | ev_s_}                            # section strict

    # 5. Profiles: profile, active fields
    ppa_ed_ = {internal: ev_if, default_: {} | ev_d_}           # default
    ppa_eds = {internal: ev_if, default_: df | ev_d_}           # default strict
    ppa_es_ = {profile_: {} | ev_f_}                            # section

    # Typecast error
    e1 = CheckTypeError('Field 5 (int) must be OwnInt type')
    e2 = CheckTypeError("Field '4' (str) must be int type")
    msg = ("Cannot import 'IO' config section {!r}. Errors:\n"
           f"\tField v_cust1='5' (str) by literal_eval: {e1!r}\n"
           f"\tField C4='4' (str) by <lambda>: {e2!r}")

    def import_and_compare_configs(**kwargs):
        nonlocal k
        k += 1
        i_data = Config4(io=True, profiles=profiles)
        i_data.cfg.io.import_config(data, **kwargs)
        assert e_data.cfg.get_data == i_data.cfg.get_data
        assert e_data.cfg.get_defaults == i_data.cfg.get_defaults
        if profiles:
            assert e_data.cfg.profiles.get == i_data.cfg.profiles.get
            assert e_data.cfg.profiles.active == i_data.cfg.profiles.active
            assert e_data.cfg.profiles.active_fields == i_data.cfg.profiles.active_fields
        assert data == i_data.cfg.io.export_config(strict_defaults=bd, strict_data=bv)

    # Correct
    i = j = k = 0
    section = defaults = bd = bv = data = None
    try:
        for i, (section, defaults, d_, ds, s_, ss) in enumerate([
            (simple__, None,  s___ed_, s___eds, s___es_, s___ess),
            (default_, True,  pd__ed_, pd__eds, pd__es_, pd__ess),
            (default_, False, pd__ed_, pd__eds, pd__es_, pd__ess),
            (profile_, True,  pp__ed_, pp__eds, pp__es_, pp__ess),
            (profile_, False, ppa_ed_, ppa_eds, ppa_es_, ppa_es_)
        ], 1):
            # Prepare source config
            if profiles := section != simple__:
                e_data = Config4(io=True, profiles=True)
                e_data.cfg.profiles.set(section, i1m, defaults=defaults)
                e_data.cfg.profiles.set(default_, i2m)
                e_data.cfg.profiles.switch(section)
            else:
                e_data = Config4(io=True)
                e_data.cfg.set_fields(i1m)
                e_data.cfg.set_defaults(i2m)

            # Check source config and target configs for equality
            tests = product([(False, d_), (True, ds)], [(False, s_), (True, ss)])
            for j, ((bd, sd), (bv, sv)) in enumerate(tests, 1):
                # Export
                k, data = 0, sd | sv
                assert data == e_data.cfg.io.export_config(strict_defaults=bd, strict_data=bv)

                # Import
                dd, dv = data.get(default_, ()), data.get(section, {})
                if (dd := 'C4' in dd) or 'C4' in dv:
                    k = 1
                    i1 = Config4(io=True, profiles=profiles)
                    raises(IOImportError(msg.format(default_ if dd else section)),
                           i1.cfg.io.import_config, data, typecast=False)
                else:
                    import_and_compare_configs(typecast=False)
                import_and_compare_configs(typecast=True)
                import_and_compare_configs(sections=(default_, section))

    except Exception as e:
        raise AssertionError(f"Correct import test failed at {i}.{j}.{k}: "
                             f"{section=}, {defaults=}, {bd=}, {bv=}, \n{data=}") from e

    # Errors

    # For version errors only
    with (cfg_v := Config4(io=True).cfg):
        cfg_v.version = '0.1'
    icv = cfg_v.io.import_config

    # Valid params
    vpp = {kip: repr(default_)}
    vpf = {kif: "{'p1': ('v_str', 'v_int')}"}

    # Valid sections
    vs_is = {internal: vpp}
    vs_ip = {internal: vpp | vpf}
    vsd = {default_: {}}
    vsp = {'p1': {'v_str': '123', 'v_int': '5'}}

    def names(target):
        return repr(tuple(target))[1:-1]

    # Input errors
    ie = "Provided wrong parameter to Config4.cfg.io.import_config()"
    add = "Must be not more than expected ({}), but received: {}"
    add2 = add.format("'DEFAULT'", "'Some'")
    add3 = add.format(names(cfg_v.get_fields), "'wrong'")
    add4 = add.format(names(cfg_v.get_fields), "'v_bool', 'wrong'")

    exc1 = TypeError("'int' object is not iterable")
    exc2 = SyntaxError('invalid syntax', ('<unknown>', 0, 0, '', 0, 0))
    exc3 = TypeError('cannot convert dictionary update sequence element #0 to a sequence')

    ies = f"{ie}: sections. Extra section: 'Some'. {add}"      # sections
    ie_s1 = InputError(msg=ies.format("'IO'", "'Some'"))
    ie_s2 = InputError(msg=ies.format("'IO'", "'IO', 'Some'"))
    ie_s3 = InputError(msg=ies.format("'p1'", "'Some'"))
    ie_s4 = InputError(msg=ies.format("'p1', '1', '2'", "'Some'"))

    ci_p = "is not needed, but provided"                        # check_input provided error
    ci_n = "is needed, but not provided"                        # check_input needed error
    af_p = "Active fields dict is not parsed"                   # active_fields parsing
    af_e = f"Extra active fields profile: 'Some'. {add2}"       # active_fields extra
    afke = f"Extra 'p1' profile active field: 'wrong'. {add3}"  # active_fields extra
    df_e = f"Extra default field: 'wrong'. {add4}"              # default field extra

    ier = f"{ie}: raw_config."                                  # raw_config
    msg_r14 = (f"{ier} Extra 'p1' profile field: 'v_bool'. Absent 'p1' profile field: 'v_str'. "
               "Must be equal to expected ('v_str', 'v_int'), but received: 'v_bool', 'v_int'")
    ie_r01 = InputError(msg=f"{ier} {internal!r} section {ci_p}")
    ie_r02 = InputError(msg=f"{ier} {internal!r} section {ci_n}")
    ie_r03 = InputError(msg=f"{ier} {kiv.capitalize()} {ci_p}")
    ie_r04 = InputError(msg=f"{ier} {kiv.capitalize()} {ci_n}")
    # ie_r05 = InputError(msg=f"{ier} {kip.capitalize()} {ci_p}")                 waits for version
    ie_r06 = InputError(msg=f"{ier} {kip.capitalize()} {ci_n}")
    ie_r07 = InputError(msg=f"{ier} Active profile is not provided: 'Some'")
    ie_r08 = (InputError(msg=f"{ier} {af_p}: '1'"), exc1)
    ie_r09 = (InputError(msg=f"{ier} {af_p}: ''"), exc2)
    ie_r10 = (InputError(msg=f"{ier} {af_p}: '[1]'"), exc3)
    ie_r11 = InputError(msg=f"{ier} {af_e}")
    ie_r12 = InputError(msg=f"{ier} {afke}")
    ie_r13 = InputError(msg=f"{ier} {df_e}")
    ie_r14 = InputError(msg=msg_r14)

    raises(ie_s1, ics, {}, 'Some')
    raises(ie_s2, ics, {}, ('IO', 'Some'))
    raises(ie_s3, icp, vs_ip | vsp, 'Some')
    raises(ie_s4, icp, vs_ip | vsp | {'1': {}, '2': {}}, 'Some')

    raises(ie_r01, ics, {internal: {}})
    raises(ie_r02, icp, {})
    raises(ie_r03, icp, {internal: {kiv: ''}})
    raises(ie_r04, icv, {internal: {}})
    # raises(ie_r05, icv, {internal: {kiv: '', kip: ''}})                         waits for version
    raises(ie_r06, icp, {internal: {}})
    raises(ie_r07, icp, {internal: {kip: "'Some'"}})
    raises(ie_r08, icp, {internal: vpp | {kif: '1'}} | vsd)
    raises(ie_r09, icp, {internal: vpp | {kif: ''}} | vsd)
    raises(ie_r10, icp, {internal: vpp | {kif: '[1]'}} | vsd)
    raises(ie_r11, icp, {internal: vpp | {kif: "{'Some': ('v_str',)}"}} | vsd)
    raises(ie_r12, icp, {internal: vpp | {kif: "{'p1': ('wrong',)}"}} | vsd | vsp)
    raises(ie_r13, ics, {default_: {'v_bool': True, 'wrong': True}})
    raises(ie_r13, icp, {default_: {'v_bool': True, 'wrong': True}} | vs_is)
    raises(ie_r14, icp, vs_ip | vsd | {'p1': {'v_bool': 'True', 'v_int': '1'}})

    # IOImport Errors
    msg = "Cannot import 'IO' config. "
    exc4 = NotImplementedError('Version import is not available yet')
    tmpl = ("Cannot import 'IO' config section {!r}. Errors:\n\tField v_bool=True (bool)"
            " by literal_eval: ValueError('malformed node or string: True')")

    raises((IOImportError(msg + repr(exc4)), exc4), icv, {internal: {kiv: ''}})
    raises(IOImportError(tmpl.format(default_)), ics, {default_: {'v_bool': True}})
    raises(IOImportError(tmpl.format(default_)), icp, {default_: {'v_bool': True}} | vs_is)
    raises(IOImportError(tmpl.format(simple__)), ics, {simple__: {'v_bool': True}})
    raises(IOImportError(tmpl.format('Some1')), icp, {'Some1': {'v_bool': True}} | vs_is | vsd)
