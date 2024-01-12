
```shell
pip install poetry -t `chore/poetry_plugin_export_(modified)`
pip install poetry-plugin-export -t `chore/poetry_plugin_export_(modified)`
pip install lk-logger -t `chore/poetry_plugin_export_(modified)`
```

manually copy `chore/modified_source.py` content to overwrite 
`chore/poetry_plugin_export_(modified)/poetry_plugin_export/walker.py`.

then you can use `poetry_extensions/poetry_export.py`.

```shell
pox poetry_extensions/poetry_export.py -h
pox poetry_extensions/poetry_export.py <proj_dir>
pox poetry_extensions/poetry_export.py <proj_dir> -d
...
```
