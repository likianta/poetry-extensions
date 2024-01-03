import os

from argsense import cli
from lk_utils import loads
from lk_utils import run_cmd_args


@cli.cmd()
def main(
    cwd: str = None,
    include_groups: bool = True,
    include_dev_gorup: bool = False,
) -> None:
    """
    kwargs:
        include_groups (-g):
        include_dev_gorup (-d):
    """
    if cwd: os.chdir(cwd)
    
    if not include_groups:
        run_cmd_args(
            'poetry', 'export', '-o', 'requirements.lock', '--without-hashes'
        )
    else:
        conf = loads('./pyproject.toml')
        groups = list(conf['tool']['poetry']['group'].keys())
        if not include_dev_gorup and 'dev' in groups:
            groups.remove('dev')
        run_cmd_args(
            'poetry', 'export', '-o', 'requirements.lock', '--without-hashes',
            *(('--with', name) for name in sorted(groups))
        )
    
    print(':t', 'see result at "requirements.lock"')


if __name__ == '__main__':
    # pox poetry_extensions/poetry_export.py -h
    # pox poetry_extensions/poetry_export.py <cwd>
    # pox poetry_extensions/poetry_export.py <cwd> -d
    cli.run(main)
