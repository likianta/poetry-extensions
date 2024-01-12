"""
this script helps avoid `poetry export` command working failed at some \
packages, for example `pythonnet>=3.0.0`, `numpy = { version = "^1.26.2", \
python = ">=3.9,<4.0", platform = "linux" }`.

prerequisites:
    see `chore/readme.md`.
"""

import os
import re
import sys
import typing as t

from argsense import cli
from lk_utils import dumps
from lk_utils import fs
from lk_utils import loads
from lk_utils import run_cmd_args
from lk_utils import xpath
from lk_utils.time_utils import timestamp


@cli.cmd()
def main(
    working_dir: str = '.',
    filename_o: str = 'requirements.lock',
    include_dev_group: bool = False,
) -> None:
    """
    kwargs:
        include_dev_group (-d):
    """
    os.chdir(working_dir)
    pyproj_file = 'pyproject.toml'
    poetry_file = 'poetry.lock'
    assert fs.exists(pyproj_file) and fs.exists(poetry_file)
    run_cmd_args(
        (sys.executable, '-m', 'poetry', 'export'),
        ('-o', (temp_file := f'{working_dir}/{filename_o}.tmp')),
        '--without-hashes',
        *(('--with', group) for group in sorted(
            _get_groups(pyproj_file, include_dev_group)
        )),
        ('--directory', fs.abspath(working_dir)),
        verbose=True,
        ignore_return=True,
        cwd=xpath('../chore/poetry_plugin_export_(modified)'),
    )
    reformat_requirements_lock_file(poetry_file, temp_file, filename_o)
    fs.remove_file(temp_file)
    print(':t', f'done. see result at "{working_dir}/{filename_o}"')


def reformat_requirements_lock_file(
    # pyproj_file: str,
    poetry_file: str,
    temp_file: str,
    output_file: str,
) -> None:
    def get_package_2_custom_url_dict() -> dict:
        data = loads(poetry_file, 'toml')
        out = {}
        for item in data['package']:
            if item['source']['type'] == 'legacy':
                if item['source']['reference'] == 'likianta-hosted':
                    name = normalize_name(item['name'])
                    out[name] = '{}/{}/{}'.format(
                        item['source']['url'],
                        name,
                        item['files'][0]['file'],
                    )
        return out
    
    def normalize_name(raw: str) -> str:
        return raw.lower().replace('_', '-').replace('.', '-')
        #   e.g. 'jaraco.classes' -> 'jaraco-classes'
    
    pkg_2_url = get_package_2_custom_url_dict()
    data_r = loads(temp_file, 'plain')
    data_w = [
        '# this file was auto generated by '
        '`poetry_extensions/poetry_export.py`',
        
        '# file was updated at {}'.format(timestamp('y-m-d h:n:s')),
        
        '# use `pip` command to install: \n'
        '#   pip install -r {} --no-deps'.format(fs.basename(output_file)),
        
        '',
        '--index-url https://pypi.tuna.tsinghua.edu.cn/simple',
        '--extra-index-url http://likianta.pro:2006',
        '--trusted-host likianta.pro',
        '',
    ]
    
    pattern = re.compile(r'^(.+)==(.+) ; (.+)', re.M)
    for m in pattern.finditer(data_r):
        name, ver, markers = m.groups()
        name = normalize_name(name)
        if name in pkg_2_url:
            data_w.append('{} @ {}'.format(name, pkg_2_url[name]))
        else:
            data_w.append('{}=={} ; {}'.format(name, ver, markers))
            
    dumps(data_w, output_file)


def _get_groups(
    pyproject_file: str,
    include_dev_group: bool = False
) -> t.Iterator[str]:
    data = loads(pyproject_file, 'toml')
    for name in data['tool']['poetry']['group']:
        if name == 'dev' and not include_dev_group:
            continue
        yield name


if __name__ == '__main__':
    # pox poetry_extensions/poetry_export.py <proj_dir>
    # pox poetry_extensions/poetry_export.py <proj_dir> -d
    cli.run(main)
