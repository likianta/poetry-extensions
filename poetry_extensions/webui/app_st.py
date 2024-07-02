import streamlit as st
from lk_utils import fs

from poetry_extensions import init_template
from poetry_extensions import poetry_export


def _get_session() -> dict:
    if __name__ not in st.session_state:
        st.session_state[__name__] = {
            'project_paths': [],
        }
    return st.session_state[__name__]


def main() -> None:
    session = _get_session()
    
    # init
    path = st.text_input('Project path')
    if st.button('Init template'):
        init_template.main(path)
    
    st.divider()
    
    # poetry export
    st.text_input(
        'Add new project path',
        key='_new_project_path',
        on_change=_add_project_path
    )
    if session['project_paths']:
        selected_path = st.radio(
            'Project to lock requirements',
            session['project_paths'],
            0,
            key='_project_select',
            # on_change=_reorder_project_paths
        )
        if st.button('Lock requirements'):
            poetry_export.main(selected_path)
        if st.button('Sort paths'):
            session['project_paths'].sort()
            st.rerun()


def _add_project_path() -> None:
    session = _get_session()
    if x := st.session_state['_new_project_path']:
        path = fs.normpath(x)
        if path not in session['project_paths']:
            session['project_paths'].insert(0, path)
        st.session_state['_new_project_path'] = ''


def _reorder_project_paths() -> None:
    session = _get_session()
    selected_path = st.session_state['_project_select']
    selected_index = session['project_paths'].index(selected_path)
    session['project_paths'].pop(selected_index)
    session['project_paths'].insert(0, selected_path)


if __name__ == '__main__':
    # strun 3001 poetry_extensions/webui/app_st.py
    main()
