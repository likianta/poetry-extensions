## init

```shell
pip install poetry-plugin-export==1.6.0 -t `chore/poetry_plugin_export_(modified)` --no-deps
```

manually delete "poetry_plugin_export-1.6.0.dist-info" folder.

## modify

freely edit the source files in 
`chore/poetry_plugin_export_(modified)/poetry_plugin_export/*`.

see effects by calling `poetry_extensions/poetry_export.py`:

```shell
pox poetry_extensions/poetry_export.py -h
pox poetry_extensions/poetry_export.py <proj_dir>
pox poetry_extensions/poetry_export.py <proj_dir> -d
...
```

## upgrade

we currently don't consider upgrading, the version of `poetry-plugin-export` 
remains 1.6.0.

for future consideration, here is a drat for upgrading:

- pip install new version to a temp folder
- manually compare the source files (can use python difflib)
- apply changes to `chore/poetry_plugin_export_(modified)/poetry_plugin_export/*`
