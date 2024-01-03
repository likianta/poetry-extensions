import os
import re

import lk_logger
from argsense import cli
from lk_utils import dumps
from lk_utils import fs
from lk_utils.textwrap import dedent

lk_logger.setup(quiet=True, show_varnames=True)

template = dedent("""
    [tool.poetry]
    name = "$package_name$"
    version = "0.1.0"
    description = ""
    authors = ["likianta <likianta@foxmail.com>"]
    # readme = "README.md"
    packages = [{ include = "$package_name_snakecase$" }]
    
    [tool.poetry.dependencies]
    python = "^$pyversion$"
    
    [[tool.poetry.source]]
    name = "tsinghua"
    url = "https://mirrors.tuna.tsinghua.edu.cn/pypi/web/simple/"
    priority = "default"
    
    [[tool.poetry.source]]
    name = "likianta-hosted"
    url = "http://likianta.pro:2006/"
    priority = "supplemental"

    [build-system]
    requires = ["poetry-core"]
    build-backend = "poetry.core.masonry.api"
""")


@cli.cmd()
def main(
    target_dir: str = None,
    package_name: str = None,
    pyversion: str = '3.11',
) -> None:
    if target_dir is None:
        target_dir = os.getcwd()
    if package_name is None:
        package_name = (
            fs.dirname(target_dir)
            .lower()
            .replace('_', '-')
            .replace(' ', '-')
        )
    assert re.match(r'[-a-z]+', package_name)
    print(package_name, ':v2')
    
    output = (
        template
        .replace('$package_name$', package_name)
        .replace('$package_name_snakecase$', package_name.replace('-', '_'))
        .replace('$pyversion$', pyversion)
    )
    dumps(output, target_dir + '/pyproject.toml', 'plain')


if __name__ == '__main__':
    # pox poetry_extensions/init_template.py <dir>
    # pox poetry_extensions/init_template.py <dir> --pyversion 3.8
    cli.run(main)
