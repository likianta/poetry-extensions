"""
command: py src/poetry_one_step/poetry_one_step.py ...
"""
import os.path
import re

from argsense import cli
from lk_utils import subproc
from lk_utils import xpath


@cli.cmd()
def by_given_name(package_name: str, no_deps=False) -> None:
    """
    kwargs:
        no_deps (-d):
    """
    lk_root = xpath('../../../..', True)
    dir_ = f'{lk_root}/{package_name}'
    print(package_name, dir_)
    assert os.path.exists(dir_)
    by_given_path(dir_, no_deps)


@cli.cmd()
def by_given_path(dir_: str, no_deps=False) -> None:
    """
    kwargs:
        no_deps (-d):
    """
    dir_ = xpath(dir_, True)
    file = f'{dir_}/pyproject.toml'
    config = open(file, 'r').read()
    version = re.search(r'version = "(.+)"', config).group(1)
    
    package_name = re.search(r'name = "(.+)"', config).group(1)
    package = f'{package_name} {version}'
    print(package, ':v2')
    
    file = '{}/dist/{}-{}-py3-none-any.whl'.format(
        dir_, package_name.replace("-", "_"), version
    )
    print(f'[u]{file}[/]', ':r')
    
    if not os.path.exists(file):
        print(f'poetry build {package}')
        # os.chdir(dir_)
        subproc.run_cmd_args(
            'poetry', 'build', '-f', 'wheel', '-C', dir_,
            verbose=True
        )
    
    print(f'pip install {package}')
    subproc.run_cmd_args(
        *subproc.compose_cmd(
            'pip', 'install', file,
            ('--no-deps' if no_deps else '')
        ),
        verbose=True
    )
    print('done', ':t')


if __name__ == '__main__':
    cli.run()
