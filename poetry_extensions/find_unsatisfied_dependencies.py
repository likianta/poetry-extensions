"""
use ast to parse the source code and find all imports.
if imports in pyproject.toml are defined but not used across the source code, print them out.
"""

import ast

import lk_logger
from argsense import cli
from lk_utils import fs

lk_logger.update(show_varnames=True)


@cli.cmd()
def main(source_dir: str, include_dev_group: bool = False) -> None:
    """
    required:
        <user_project>
        |- <source>         # <- `source_dir`
        |- pyproject.toml
    """
    project_dir = fs.parent(source_dir)
    assert fs.exists(f"{project_dir}/pyproject.toml")

    imported_packages = set()  # {top_name, ...}
    for f in fs.findall_files(source_dir, ".py"):
        code = fs.load(f.path)
        tree = ast.parse(code)
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    top_name = alias.name.split(".")[0]
                    imported_packages.add(top_name)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    top_name = node.module.split(".")[0]
                    imported_packages.add(top_name)
    print(len(imported_packages))

    defined_packages = set()
    conf = fs.load(f"{project_dir}/pyproject.toml")
    for x in conf["tool"]["poetry"]["dependencies"]:
        if x == "python":
            continue
        name = x.replace("-", "_")
        defined_packages.add(name)
    if "group" in conf["tool"]["poetry"]:
        for k, x in conf["tool"]["poetry"]["group"].items():
            if not include_dev_group and k == "dev":
                continue
            for y in x["dependencies"]:
                name = y.replace("-", "_")
                defined_packages.add(name)
    print(len(defined_packages))

    try:
        ignored = frozenset(
            x.replace("-", "_")
            for x in conf["tool"]["poetry-extensions"]["ignored_redundant_packages"]
        )
    except Exception:
        ignored = frozenset()

    for x in sorted(defined_packages):
        if x not in imported_packages:
            if x not in ignored:
                print(x, ":iv3")


if __name__ == "__main__":
    # pox poetry_extensions/find_unsatisfied_dependencies.py <src_dir>
    # pox poetry_extensions/find_unsatisfied_dependencies.py <src_dir> :true
    cli.run(main)
