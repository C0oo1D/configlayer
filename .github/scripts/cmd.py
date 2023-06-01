"""Commands needed for GitHub Actions jobs
    get_version -> str
    check_release (on GitHub) -> exit code
    check_publish (on PyPi) -> exit code"""
from json import loads
from typing import Callable
from tomli import load
from argparse import ArgumentParser
from dataclasses import dataclass

import requests
from packaging.version import Version, parse


repo_owner = 'C0oo1D'
functions: dict[str, Callable] = {}


@dataclass
class LatestRelease:
    title: str
    tag_name: str
    published: str
    version: Version

    def __init__(self, repo: str):
        url = f"https://api.github.com/repos/{repo}/releases/latest"
        if data := request(url, 'GitHub', f'{repo} latest release'):
            self.title = data['name']
            self.tag_name = data['tag_name']
            self.published = data['published_at']
        else:
            self.title, self.tag_name, self.published = ([''] * 3)
        self.version = parse(self.tag_name or 'v0.0.0')


def request(url: str, site_name: str, target_name: str):
    response = requests.get(url)
    if response.status_code != requests.codes.ok:
        raise ConnectionError(f'{site_name} was rejected request to {target_name!r} json, '
                              f'response code: {response.status_code}')
    return loads(response.text.encode(response.encoding))


def parse_cli():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument('func_name', choices=functions)
    return parser.parse_args()


def _get_name_version() -> tuple[str, Version]:
    """Get package name and version from pyproject.toml"""
    with open('pyproject.toml', 'rb') as file:
        project = load(file)['project']
    return project['name'], parse(project['version'])


def _get_pypi_version(package_name: str) -> Version:
    """Get package version from PyPi by name"""
    response = request(f'https://pypi.python.org/pypi/{package_name}/json', 'PyPi', package_name)
    return parse(response['info']['version'])


def get_version() -> str:
    """Get local package version -> str"""
    v = _get_name_version()[1]
    return f'v{v.major}.{v.minor}.{v.micro}'


def check_release() -> tuple[int, str]:
    """Check if release to GitHub is needed -> zero exit code == needed"""
    repository, local_version = _get_name_version()
    release = LatestRelease(f'{repo_owner}/{repository}')
    needed = local_version > release.version
    return int(not needed), f"{local_version = }, {release}"


def check_publish() -> tuple[int, str]:
    """Check if publish to PyPi is needed -> zero exit code == needed"""
    name, local_version = _get_name_version()
    pypi_version = _get_pypi_version(name)
    needed = local_version > pypi_version
    return int(not needed), f"{local_version = }, {pypi_version = }"


if __name__ == '__main__':
    functions = dict(locals())

    def get(_, func):
        print(func())

    def check(name, func):
        try:
            err_code, msg = func()
            msg = f"{'not ' if err_code else ''}needed: {msg}"
        except Exception as e:
            err_code, msg = 2, f'skipped, exception occurred during check: {e}'
        print(f'Run {name} job is ' + msg)
        exit(err_code)

    handlers = {k: v for k, v in dict(locals()).items() if k not in functions}
    functions = {k: v for k, v in functions.items() if k.startswith(tuple(handlers))}

    func_name = parse_cli().func_name
    handler, operation = func_name.split('_')
    handlers[handler](operation, functions[func_name])
