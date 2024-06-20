import re

from argsense import cli
from lk_utils import fs


@cli.cmd()
def main(proj_dir: str) -> None:
    content = fs.load(f'{proj_dir}/pyproject.toml', 'plain')
    data_i = tuple(content.splitlines())
    data_o = []
    #   ~~{str group: [(str line, str type, optional dict info), ...], ...}~~
    #   ~~{str group: [str line, ...], ...}~~
    #   [str line, ...]
    
    flag = 'INIT'
    skip = -1  # DELETE
    # part = []
    temp = {}
    last: str
    curr: str
    next: str
    for i, (last, curr, next) in enumerate(zip(
        (None, *data_i),
        data_i,
        (*data_i[1:], None),
    ), 1):
        if i <= skip:
            continue
        if flag == 'INIT':
            if curr == '[tool.poetry.dependencies]':
                flag = 'MAIN_DEPS_START'
            data_o.append(curr)
            continue
        if flag == 'MAIN_DEPS_START':
            assert curr.startswith('python =')
            data_o.append(curr)
            flag = 'MAIN_DEPS_INDEXING'
            temp = None
            continue
        if flag == 'MAIN_DEPS_INDEXING':
            if m := re.match(r'(?:# )?([-\w]+) = ', curr):
                temp = {'curr_name': m.group(1),
                        'collection': {m.group(1): [curr]}}
                flag = 'MAIN_DEPS_BODY'
            else:
                assert not temp
                data_o.append(curr)
            if next.startswith('[['):
                assert not temp
                flag = 'SEARCHING_GROUPS'
            continue
        if flag == 'MAIN_DEPS_BODY':
            if m := re.match(r'(?:# )?([-\w]+) = ', curr):
                assert temp
                temp['curr_name'] = m.group(1)
                temp['collection'][temp['curr_name']] = [curr]
            else:
                temp['collection'][temp['curr_name']].append(curr)
            if next.startswith('[['):
                assert temp
                for key in sorted(temp['collection']):
                    data_o.extend(temp['collection'][key])
                temp = None
                flag = 'SEARCHING_GROUPS'
            continue
        if flag == 'SEARCHING_GROUPS':
            if re.fullmatch(
                r'\[\[tool\.poetry\.group\.([-\w]+)\.dependencies]]', curr
            ):
                flag = 'GROUP_DEPS'
            data_o.append(curr)
            continue
        if flag == 'GROUP_DEPS':
            if m := re.match(r'(?:# )?([-\w]+) = ', curr):
                if not temp:
                    temp = {'curr_name': m.group(1),
                            'collection': {m.group(1): [curr]}}
                else:
                    temp['curr_name'] = m.group(1)
                    temp['collection'][temp['curr_name']] = [curr]
            else:
                assert temp
                temp['collection'][temp['curr_name']].append(curr)
            if next.startswith('[['):
                assert temp
                for key in sorted(temp['collection']):
                    data_o.extend(temp['collection'][key])
                temp = None
                flag = 'SEARCHING_GROUPS'
            continue
    
    fs.copy_file(f'{proj_dir}/pyproject.toml',
                 fs.xpath('../chore/pyproject_backup.toml'), True)
    fs.dump(data_o, f'{proj_dir}/pyproject.toml', 'plain')


if __name__ == '__main__':
    # pox poetry_extensions/sort.py ...
    cli.run(main)
