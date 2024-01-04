import re
import typing as t
from collections import defaultdict

from argsense import cli

from lk_utils import dumps
from lk_utils import fs
from lk_utils import loads
from lk_utils.time_utils import timestamp


@cli.cmd()
def main(
    cwd: str = '.',
    filename: str = 'requirements.lock',
    include_dev_group: bool = False,
    only_top_deps: bool = True,
    flatten_top_deps: bool = False,
) -> None:
    """
    kwargs:
        include_dev_group (-d):
        flatten_top_deps (-f):
    """
    file_i = f'{cwd}/poetry.lock'
    file_m = f'{cwd}/pyproject.toml'  # assistant
    file_o = f'{cwd}/{filename}'
    
    data_i = _reformat_locked_data(loads(file_i, 'toml'))
    data_m = _reformat_pyproj_data(loads(file_m, 'toml'), include_dev_group)
    data_o = _init_output_template(file_o, flatten_top_deps)
    
    if only_top_deps:
        top_deps = data_m.keys()
        all_deps = _flatten_all_dependencies(data_i)
        if flatten_top_deps:
            top_deps = set(_flatten_top_dependencies(top_deps, all_deps))
        else:
            top_deps = set(top_deps)
    else:
        raise NotImplementedError
    
    # -------------------------------------------------------------------------
    
    all_info = defaultdict(lambda: {
        'version': '',
        'url'    : '',
        'markers': set(),
        'extras' : set(),
    })
    
    for name in top_deps:
        item = data_i[name]
        
        # info:name:version
        all_info[name]['version'] = item['version']
        
        # info:name:url
        if item['source']['type'] == 'legacy':
            if item['source']['reference'] == 'likianta-hosted':
                all_info[name]['url'] = '{}/{}/{}'.format(
                    item['source']['url'],
                    name,
                    item['files'][0]['file'],
                )
        else:
            all_info[name]['url'] = item['source']['url']
        
        # info:name:markers
        if raw_info := data_m.get(name):
            if isinstance(raw_info, dict):
                if 'platform' in raw_info:
                    p: str = raw_info['platform']
                    assert p in ('darwin', 'linux', 'win32')
                    all_info[name]['markers'].add(f'sys_platform == "{p}"')
                if 'python' in raw_info:
                    pyver: str = raw_info['python']
                    norm_pyver = []
                    assert pyver.startswith(('==', '!=', '>=', '<=', '>', '<'))
                    for part in re.split(r', *', pyver):
                        # part = re.sub(r'(\d+\.\d+(?:\.\d+)?)', r'"\1"', part)
                        # #   e.g. '>=3.10' -> '>="3.10"'
                        a, b = re.match(
                            r'(.*?) *(\d+\.\d+(?:\.\d+)?)$', part
                        ).groups()  # e.g. '>= 3.10' -> ('>=', '3.10')
                        norm_pyver.append('python_version {} "{}"'.format(a, b))
                    all_info[name]['markers'].update(norm_pyver)
        
        # # info:direct_deps_names:markers
        # if 'dependencies' in item:
        #     for dep_name, dep_spec in item['dependencies'].items():
        #         if isinstance(dep_spec, dict):
        #             dep_name = _normalize_name(dep_name)
        #             if 'extras' in dep_spec:
        #                 all_info[dep_name]['extras'].update(dep_spec['extras'])
        #
        #         if isinstance(dep_spec, dict) and 'markers' in dep_spec:
        #             all_info[dep_name]['markers'].add(dep_spec['markers'])
    
    # add markers
    for name, item in data_i.items():
        for dep_name, dep_spec in item['dependencies'].items():
            if dep_name in all_info:
                if isinstance(dep_spec, dict) and 'markers' in dep_spec:
                    # if all_info[dep_name]['markers']:
                    #     print('old markders will be override', dep_name, ':v3')
                    all_info[dep_name]['markers'].add(dep_spec['markers'])
    # inherit markers
    for name, deps in all_deps.items():
        if name in all_info:
            base_markers: set = all_info[name]['markers']
            for dep_name in deps:
                if dep_name in all_info:
                    all_info[dep_name]['markers'].update(base_markers)
    
    for name in sorted(all_info.keys()):
        dict_ = all_info[name]
        print(name, ':i')
        if dict_['version']:
            if dict_['url']:
                line = '{} @ {}'.format(name, dict_['url'])
            else:
                line = '{}=={}'.format(name, dict_['version'])
            if dict_['markers']:
                line += ' ; {}'.format(_resolve_markers(dict_['markers']))
            data_o.append(line)
        else:
            print(f'skip {name}', ':v3s')
    
    dumps(data_o, file_o, 'plain')
    print('done', fs.relpath(file_o), ':t')


def _flatten_all_dependencies(locked_data: dict) -> t.Dict[str, t.Set[str]]:
    all_direct_deps = {
        k: set(v['dependencies'])
        for k, v in locked_data.items()
    }
    
    def flatten(
        direct_deps: t.Set[str], _recorded: t.Set = None
    ) -> t.Iterator[str]:
        if _recorded is None:
            _recorded = set()
        for dep in direct_deps:
            if dep in _recorded:
                continue
            else:
                yield dep
                _recorded.add(dep)
            indirect_deps = all_direct_deps[dep]
            yield from flatten(indirect_deps, _recorded)
    
    out = {}
    for k, v in all_direct_deps.items():
        out[k] = set(flatten(v))
    return out


def _flatten_top_dependencies(
    top_deps: t.Iterable[str], all_deps: dict
) -> t.Iterator[str]:
    for d in top_deps:
        yield d
        yield from all_deps[d]


def _init_output_template(file_o: str, flatten_top_deps: bool) -> list:
    return [
        '# this file was auto generated by '
        '`poetry_extensions/requirements_lock.py`',
        
        '# file was updated at {}'.format(timestamp('y-m-d h:n:s')),
        
        '# use `pip` command to install: \n'
        '#   pip install -r {} {}'.format(
            fs.basename(file_o), '--no-deps' if flatten_top_deps else '',
        ).rstrip(),
        
        '',
        '--index-url https://pypi.tuna.tsinghua.edu.cn/simple',
        '--extra-index-url http://likianta.pro:2006',
        '--trusted-host likianta.pro',
        '',
    ]


def _normalize_name(raw: str) -> str:
    return raw.lower().replace('_', '-').replace('.', '-')
    #   e.g. 'jaraco.classes' -> 'jaraco-classes'


def _reformat_locked_data(data: dict) -> dict:
    """
    returns:
        {
            name: {
                'version': str,
                'source': dict,
                'files': [dict, ...],
                'dependencies': {name: spec, ...}
            }, ...
        }
    """
    out = {}
    all_declared_extras = {}  # {name: container, ...}
    #   `container` is a dict or tuple which implements `__contains__` method.
    
    for item in data['package']:
        name = _normalize_name(item['name'])
        out[name] = {
            'version': item['version'],
            'source': item['source'],
            'files': item['files'],
            'dependencies': {
                _normalize_name(k): v
                for k, v in item.get('dependencies', {}).items()
            },
        }
        all_declared_extras[name] = item.get('extras', ())
    
    # make clear extras
    for k0, v0 in out.items():
        required_extras = all_declared_extras.get(k0, ())
        deps = v0['dependencies']
        for k1, v1 in tuple(deps.items()):
            if isinstance(v1, dict) and v1.get('optional', False):
                try:
                    if (markers := v1['markers']).startswith('extra =='):
                        #   e.g. {..., 'markers': 'extra == "linkify"'}
                        ex_name = markers.split('"')[1]
                        v1.pop('markers')
                    else:
                        assert ' and extra ==' in (markers := v1['markers'])
                        #   e.g. {..., 'markers': 'platform_python_ \
                        #   implementation == "CPython" and extra == "woff"'}
                        match = re.search(r' and extra == "(\w+)"', markers)
                        ex_name = match.group(1)
                        v1['markers'] = v1['markers'].replace(match.group(0), '')
                    v1['extra'] = ex_name
                    if ex_name not in required_extras:
                        deps.pop(k1)
                except (AssertionError, AttributeError) as e:
                    print(k0, k1, v1)
                    raise e
    return out


def _reformat_pyproj_data(data: dict, include_dev_group: bool) -> dict:
    """
    merge groups into default.
    returns:
        {name: spec, ...}
    """
    default: dict = data['tool']['poetry']['dependencies']
    default.pop('python')
    if 'group' in data['tool']['poetry']:
        for k, v in data['tool']['poetry']['group'].items():
            if k == 'dev' and not include_dev_group:
                continue
            default.update(v['dependencies'])
    return {_normalize_name(k): v for k, v in default.items()}


def _resolve_markers(markers: t.Set[str]) -> str:
    temp = defaultdict(list)
    for m in markers:
        a, b = m.split(' ', 1)
        #   e.g. 'python == "3.10"' -> ('python', '== "3.10"')
        temp[a].append(b)
    
    is_and = False
    is_or = False
    if (
        len(temp['sys_platform']) > 1 or
        (temp['sys_platform'] and temp['os_name'])
    ):
        is_or = True
    if len(temp['python']) > 1:
        is_and = True
    assert not (is_and and is_or), 'AND, OR cannot be present in same time'
    del temp
    
    if is_and:
        return ' and '.join(sorted(markers))
    else:
        return ' or '.join(sorted(markers))


if __name__ == '__main__':
    # pox poetry_extensions/requirements_lock.py
    cli.run(main)
