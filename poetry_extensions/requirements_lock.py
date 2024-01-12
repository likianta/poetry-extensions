"""
DELETE: this script is going to be deleted. pls turn to `./poetry_export.py`.
"""
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
    flatten_deps: bool = False,
) -> None:
    """
    kwargs:
        include_dev_group (-d):
        flatten_deps (-f):
    """
    file_i = f'{cwd}/poetry.lock'
    file_m = f'{cwd}/pyproject.toml'  # assistant
    file_o = f'{cwd}/{filename}'
    
    data_i = _reformat_locked_data(loads(file_i, 'toml'))
    data_m = _reformat_pyproj_data(loads(file_m, 'toml'), include_dev_group)
    data_o = _init_output_template(file_o, flatten_deps)
    
    top_deps = data_m.keys()
    all_deps = _flatten_all_dependencies(data_i)
    if flatten_deps:
        top_deps = set(_flatten_top_dependencies(top_deps, all_deps))
    else:
        top_deps = set(top_deps)
    # print(sorted(top_deps), ':l')
    
    # -------------------------------------------------------------------------
    
    all_info = defaultdict(lambda: {
        'version': '',
        'url'    : '',
        # https://peps.python.org/pep-0496/#micro-language
        'markers': defaultdict(lambda: defaultdict(set)),
        #   {chain: {marker: {(operator, value), ...}, ...}, ...}
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
                    all_info[name]['markers']['<top>'][
                        'sys_platform'].add(('==', p))
                if 'python' in raw_info:
                    pyver: str = raw_info['python']
                    #   e.g. {..., 'python': '>=3.8,<3.11'}
                    for part in re.split(r', *', pyver):
                        a, b = re.match(
                            r'(.*?) *(\d+\.\d+(?:\.\d+)?)$', part
                        ).groups()  # e.g. '>= 3.10' -> ('>=', '3.10')
                        all_info[name]['markers']['<top>'][
                            'python_version'].add((a, b))
            else:
                all_info[name]['markers']['<top>']['<no_marker>'] = set()
    
    # add markers
    for name, item in data_i.items():
        for dep_name, dep_spec in item['dependencies'].items():
            if dep_name in all_info:
                if isinstance(dep_spec, dict) and 'markers' in dep_spec:
                    '''
                    case examples:
                        {..., 'markers': 'sys_platform == "win32"'}
                        {..., 'markers': 'platform_machine != "i386" and
                            platform_machine != "i686"'}
                        {..., 'markers': 'sys_platform == "freebsd" or
                            sys_platform == "linux"'}
                    '''
                    for part in re.split(r' (?:and|or) ', dep_spec['markers']):
                        a, b, c = re.match(r'(.+) (.+) "(.+)"', part).groups()
                        all_info[dep_name]['markers'][name][a].add((b, c))
                else:
                    all_info[dep_name]['markers'][name]['<no_marker>'] = set()
    
    # inherit markers
    for name, deps in all_deps.items():
        # if name in data_m:  # the top deps can't be inherited
        #     continue
        if name in all_info:
            base_markers: dict = all_info[name]['markers']
            for dep_name in deps:
                if dep_name in all_info:
                    for k, v in tuple(base_markers.items()):
                        for k1, v1 in v.items():
                            if k1 != '<no_marker>':
                                all_info[dep_name]['markers'][
                                    name][k1].update(v1)
                    # if name == 'pyside6':  # test
                    #     print(dep_name, base_markers, all_info[dep_name]['markers'], ':lv')
    
    for name in sorted(all_info.keys()):
        dict_ = all_info[name]
        print(name, ':i')
        if dict_['version']:
            if dict_['url']:
                line = '{} @ {}'.format(name, dict_['url'])
            else:
                line = '{}=={}'.format(name, dict_['version'])
            if dict_['markers']:
                if x := _resolve_markers(dict_['markers']):
                    line += ' ; {}'.format(x)
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
            'version'     : item['version'],
            'source'      : item['source'],
            'files'       : item['files'],
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


def _resolve_markers(
    markers: t.Dict[str, t.Dict[str, t.Set[t.Tuple[str, str]]]]
) -> str:
    """
    https://peps.python.org/pep-0496/
    practical examples:
        {'python_version': {('>=', '3.8'), ('<', '3.12')}}
            -> 'python_version >= "3.8" and python_version < "3.11"'
        {'python_version': {('==', '3.8'), ('==', '3.12')}}
            -> 'python_version == "3.8" or python_version == "3.12"'
        {'python_version': {('>=', '3.8')}, 'sys_platform': {('==', 'win32')}}
            -> '(python_version >= "3.8") and (sys_platform == "win32")'
    """
    total_groups = set()
    
    for domain, sub_markers in markers.items():
        if '<no_marker>' in sub_markers:
            if len(sub_markers) == 1:
                return ''
            else:
                sub_markers.pop('<no_marker>')
        
        # fix duplicate markers
        if 'platform_system' in sub_markers:
            dict_ = {'Darwin': 'darwin', 'Linux': 'linux', 'Windows': 'win32'}
            for k, v in sub_markers.pop('platform_system'):
                sub_markers['sys_platform'].add((k, dict_[v]))
        
        groups = []
        for marker, constraints in sub_markers.items():
            assert constraints
            has_equal_sign = False
            parts = []
            for operator, value in sorted(constraints):
                parts.append('{} {} "{}"'.format(marker, operator, value))
                if not has_equal_sign:
                    if operator == '==':
                        has_equal_sign = True
            if len(parts) == 1:
                groups.append(parts[0])
            else:
                # how to join `parts`
                sep = ' or ' if has_equal_sign else ' and '
                groups.append('({})'.format(sep.join(parts)))
        
        if len(groups) == 1:
            total_groups.add('({})'.format(groups[0].strip('()')))
        else:
            total_groups.add('({})'.format(' and '.join(groups)))
    if len(total_groups) == 1:
        return tuple(total_groups)[0].strip('()')
    else:
        return ' or '.join(total_groups)


if __name__ == '__main__':
    # pox poetry_extensions/requirements_lock.py
    cli.run(main)
