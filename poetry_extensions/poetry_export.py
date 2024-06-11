"""
this script helps avoid `poetry export` command working failed at some \
packages, for example `pythonnet>=3.0.0`, `numpy = { version = "^1.26.2", \
python = ">=3.9,<4.0", platform = "linux" }`.

prerequisites:
    see `chore/poetry_plugin_export_(modified)/readme.md`.
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

_modified_plugin_path = xpath(
    '../chore/poetry_plugin_export_(modified)/poetry_plugin_export'
)
assert fs.exists(_modified_plugin_path), (
    'see "chore/poetry_plugin_export_(modified)/readme.md"'
)


@cli.cmd()
def main(
    working_dir: str = '.',
    filename_o: str = 'requirements.lock',
    include_dev_group: bool = False,
    strip_redundant_pyverspec: bool = True,
) -> None:
    """
    kwargs:
        include_dev_group (-d):
        strip_redundant_pyverspec (-s):
    """
    working_dir = fs.abspath(working_dir)
    os.chdir(working_dir)
    pyproj_file = 'pyproject.toml'
    poetry_file = 'poetry.lock'
    assert fs.exists(pyproj_file) and fs.exists(poetry_file)
    
    pyproj_data = loads(pyproj_file, 'toml')
    poetry_data = loads(poetry_file, 'toml')
    del pyproj_file, poetry_file
    
    run_cmd_args(
        (sys.executable, '-m', 'poetry', 'export'),
        ('-o', (temp_file := f'{working_dir}/{filename_o}.tmp')),
        '--without-hashes',
        *(('--with', group) for group in sorted(
            _get_groups(pyproj_data, include_dev_group)
        )),
        ('--directory', fs.abspath(working_dir)),
        verbose=True,
        ignore_return=True,
        cwd=fs.parent(_modified_plugin_path),
    )
    
    reformat_requirements_lock_file(
        pyproj_data,
        poetry_data,
        temp_file,
        filename_o,
        strip_redundant_pyverspec
    )
    fs.remove_file(temp_file)
    
    print(':t', f'done. see result at "{working_dir}/{filename_o}"')


def reformat_requirements_lock_file(
    pyproj_data: dict,
    poetry_data: dict,
    temp_file: str,
    output_file: str,
    strip_redundant_pyverspec: bool = False,
) -> None:
    def get_package_2_custom_url_dict() -> dict:
        out = {}
        for item in poetry_data['package']:
            if item['source']['type'] == 'legacy':
                if item['source']['reference'].startswith('likianta'):
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
    
    data_r = loads(temp_file, 'plain')
    data_w = [
        '# this file was auto generated by https://github.com/likianta/poetry-'
        'extensions : /poetry_extensions/poetry_export.py',
        
        '# file was updated at {}'.format(timestamp('y-m-d h:n:s')),
        
        '# use `pip` command to install: \n'
        '#   pip install -U -r {} --no-deps'.format(fs.basename(output_file)),
        
        '',
        '--index-url https://pypi.tuna.tsinghua.edu.cn/simple',
        '--extra-index-url http://likianta.pro:2006',
        '--trusted-host likianta.pro',
        '',
    ]
    
    pkg_2_url = get_package_2_custom_url_dict()
    pyverspec = 'python_version >= "{}" and python_version < "{}"'.format(
        pyproj_data['tool']['poetry']['dependencies']['python'].lstrip('>=^'),
        '4.0'
    )
    # print(pyverspec, ':v')

    pattern = re.compile(r'^(.+)==(.+) ; (.+)', re.M)
    for m in pattern.finditer(data_r):
        name, ver, markers = m.groups()
        name = normalize_name(name)
        if name in pkg_2_url:
            data_w.append('{} @ {}'.format(name, pkg_2_url[name]))
        else:
            if strip_redundant_pyverspec:
                markers = (
                    markers
                    .replace(pyverspec, '*')
                    .replace('* and ', '')
                    .replace(' and *', '')
                    .replace('*', '')
                )
                if (
                    markers.count('(') == 1 and
                    markers.count(')') == 1 and
                    markers.startswith('(') and
                    markers.endswith(')')
                ):
                    markers = markers.strip('()')
            data_w.append('{}=={} ; {}'.format(name, ver, markers).strip(' ;'))
    
    dumps(data_w, output_file)


def _get_groups(
    pyproject_data: dict,
    include_dev_group: bool = False
) -> t.Iterator[str]:
    if 'group' in pyproject_data['tool']['poetry']:
        for name in pyproject_data['tool']['poetry']['group']:
            if name == 'dev' and not include_dev_group:
                continue
            yield name


if __name__ == '__main__':
    # pox poetry_extensions/poetry_export.py <proj_dir>
    # pox poetry_extensions/poetry_export.py <proj_dir> -d
    cli.run(main)
