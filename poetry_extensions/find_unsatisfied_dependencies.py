"""
req: deptry
"""
import sys
import typing as t

from argsense import cli
from lk_utils import fs
from lk_utils import load
from lk_utils import run_cmd_args


@cli.cmd()
def main(source_dir: str) -> None:
    project_dir = fs.parent(source_dir)
    assert fs.exists(f'{project_dir}/pyproject.toml')
    
    run_cmd_args(
        sys.executable, '-m', 'deptry', source_dir,
        '--config', f'{project_dir}/pyproject.toml',
        '--json-output', fs.xpath('../temp.json'),
        # verbose=True,
        ignore_error=True
    )
    
    missing = set()
    redundant = set()
    # unknown = set()
    
    log: list = fs.load(fs.xpath('../temp.json'))
    for xdict in log:
        match xdict['error']['code']:
            case 'DEP001':
                missing.add(xdict['module'])
            case 'DEP002':
                redundant.add(xdict['module'])
            case 'DEP004':
                pass
            case _:
                print('unrecognized code', xdict, ':v3l')
    
    ignores = _load_custom_rules(f'{project_dir}/pyproject.toml')
    for x in sorted(missing):
        if x not in ignores:
            print(f'missing: {x}', ':v4s1i2')
    for x in sorted(redundant):
        if x not in ignores:
            print(f'redundant: {x}', ':v3s1i2')


@cli.cmd()
def show_help() -> None:
    run_cmd_args(
        sys.executable, '-m', 'deptry', '--help',
        verbose=True,
    )


def _load_custom_rules(pyproj_file: str) -> t.Sequence[str]:
    conf = load(pyproj_file)
    try:
        return conf['tool']['poetry_extensions']['deptry']['ignores']
    except KeyError:
        return ()


if __name__ == '__main__':
    # pox poetry_extensions/find_unsatisfied_dependencies.py show-help
    # pox poetry_extensions/find_unsatisfied_dependencies.py main <dir>
    cli.run()
