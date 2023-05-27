"""Build badges from mypy result files
    Generate mypy tests badge from customized junit file (1 test == 1 source file)
        --junit-xml flag generates single testcase for all source files
        mypy2junit package fails at file build (if no mypy issues found)
    Generate mypy imprecise coverage badge from txt report"""
import re

from pathlib import Path
from argparse import ArgumentParser

from genbadge import Badge
from genbadge.main import gen_tests_badge


# Paths and its parts
root_dir_name = 'configlayer'
log_in_path = 'temp/mypy.log'
imp_in_path = 'temp/mypy/index.txt'
xml_out_path = 'temp/mypy.xml'
tests_badge_path = 'reports/mypy.svg'
imp_badge_path = 'reports/mypy-imp.svg'


# Templates regexp for mypy output
passed = ".*Success: no issues found in (?P<t>.*) source files?"
failed = ".*Found (?P<e>.*) errors? in (?P<f>.*) files? \\(checked (?P<t>.*) source files?\\)"

# Templates for junit xml
xml_template = """<?xml version="1.0" encoding="utf-8"?>
<testsuite errors="0" failures="{f}" name="mypy" skips="0" tests="{t}" time="0.000">
{items}</testsuite>"""
xml_case = ('  <testcase classname="mypy" file="mypy" line="{line}" name="mypy" time="0.000">'
            '{msg}</testcase>\n')
xml_fail = '\n    <failure message="message">failure</failure>'


def parse_cli():
    args = ArgumentParser(description=__doc__)
    args.add_argument('-l', '--log', type=str, nargs='?', default=log_in_path,
                      help=f'mypy input log path (default: {log_in_path}; '
                           f'get file: mypy . > {log_in_path})')
    args.add_argument('-i', '--imprecise', type=str, nargs='?', default=imp_in_path,
                      help=f'mypy input imprecise index.txt path (default: {imp_in_path}; '
                           f'get file: mypy {root_dir_name} --txt-report '
                           f'{imp_in_path.rstrip("/index.txt")})')
    args.add_argument('-x', '--xml', type=str, nargs='?', default=xml_out_path,
                      help=f'mypy output xml path (default: {xml_out_path})')
    args.add_argument('-tb', '--tests_badge', type=str, nargs='?', default=tests_badge_path,
                      help=f'mypy tests badge path (default: {tests_badge_path})')
    args.add_argument('-ib', '--imprecise_badge', type=str, nargs='?', default=imp_badge_path,
                      help=f'mypy imprecise badge path (default: {imp_badge_path})')
    args.add_argument('-r', '--root', type=str, nargs='?', default=root_dir_name,
                      help=f'root directory name (default: {root_dir_name})')
    return args.parse_args()


def get_root(dir_name):
    path = Path().absolute()
    while path.name != dir_name:
        if (new_path := path.parent) == path:
            raise NotADirectoryError(f"{dir_name!r} is not found")
        path = new_path
    return path


def get_data_lines(path: Path, **kwargs) -> list[str]:
    with path.open(**kwargs) as file:
        lines = file.read().splitlines()
    return lines


def read_log(path: Path) -> tuple[int, int]:
    errors = ''
    for encoding in (None, 'UTF-16LE'):
        try:
            lines = get_data_lines(path, encoding=encoding)
        except Exception as e:
            errors += f'{path}, {encoding = }, exception: {e}'
            continue

        if found := re.match(passed, lines[0]):
            return int(found.group('t')), 0
        elif found := re.match(failed, lines[-1]):
            return int(found.group('t')), int(found.group('f'))
        errors += '\t\t'.join((f'{path}, {encoding = }, data:\n', *lines))

    raise ValueError('\n\t'.join(('No templates found:', f'{passed = }', f'{failed = }', errors)))


def write_xml(path: Path, tests: int, fails: int):
    items = [xml_case.format(line=i+1, msg=xml_fail if fails > i else 'ok') for i in range(tests)]
    with path.open('w') as xml:
        xml.write(xml_template.format(f=fails, t=tests, items=''.join(items)))


def read_imprecise(path: Path) -> str:
    return get_data_lines(path)[-2].split('|')[2].split()[0]


def write_imprecise(path: Path, data_str: str):
    Badge('mypy-imprecise', data_str, 'lightgrey').write_to(path)
    print(f"SUCCESS - mypy-imprecise badge created: {path.as_posix()!r}")


if __name__ == '__main__':
    cli = parse_cli()
    root = get_root(cli.root)

    # Get xml
    log_data = read_log(root / cli.log)
    write_xml(root / cli.xml, *log_data)

    # Get badge (seems not good idea to make it in that way)
    try:
        gen_tests_badge((f'-i{root / cli.xml}', f'-o{root / cli.tests_badge}', '-n mypy'))
    except SystemExit:
        pass

    # Get imprecise badge
    imp_data = read_imprecise(root / cli.imprecise)
    write_imprecise(root / cli.imprecise_badge, imp_data)
