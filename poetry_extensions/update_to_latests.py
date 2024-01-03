"""
find the latest version of a package.
"""
import requests
from argsense import cli
from lk_utils import loads


@cli.cmd()
def process_simple_list(file: str) -> None:
    for line in loads(file, 'plain').splitlines():
        line = line.strip()
        if line and not line.startswith('#'):
            name = line
            version = _get_one(name)
            print(name, version, ':i2v2')
            
            
@cli.cmd()
def get_one(package_name: str) -> None:
    version = _get_one(package_name)
    print(package_name, version, ':v2')


def _get_one(package_name: str) -> str:
    url = 'https://pypi.org/pypi/{}/json'.format(package_name)
    resp = requests.get(url)
    data = resp.json()
    return data['info']['version']


if __name__ == '__main__':
    # pox projects/poetry_enhancement/all_latests.py get-one $name
    cli.run()
