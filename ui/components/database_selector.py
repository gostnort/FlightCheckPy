#!/usr/bin/env python3
"""
简化的数据库选择器组件 - 仅用于侧边栏
"""

from pathlib import Path

import streamlit as st

from scripts.config_manager import get_config_value, set_config_value
from ui.common import format_database_choice, get_db_port_client, load_database


def _resolved(path: str) -> str:
    return str(Path(path).resolve())


def _default_index(valid_files: list, current_name: str) -> int:
    names = [Path(path).name for path in valid_files]
    if current_name and current_name in names:
        return names.index(current_name)
    last_name = Path(get_config_value("db_preferences", "last_selected_db", "") or "").name
    if last_name in names:
        return names.index(last_name)
    return 0


def _remember_open_database(db_path: str) -> None:
    name = Path(db_path).name
    if not name or not get_config_value("db_preferences", "remember_last_db", True):
        return
    if get_config_value("db_preferences", "last_selected_db", "") == name:
        return
    set_config_value("db_preferences", "last_selected_db", name)


def _switch_database(widget_key: str) -> None:
    """切换当前库。只在用户改选时调用一次。"""
    # 侧边栏和管理页各有一个下拉框，同一次重跑里只接受先到的那次切换。
    if st.session_state.get("_db_switch_done"):
        return
    selected = st.session_state.get(widget_key)
    if not selected:
        return
    st.session_state["_db_switch_done"] = True
    if load_database(selected):
        st.session_state.pop("_db_bootstrap_target", None)
        _remember_open_database(selected)


def _path_for_name(valid_files: list, name: str):
    if not name:
        return None
    for path in valid_files:
        if Path(path).name == name:
            return path
    return None


def _shown_database(valid_files: list, active_name: str) -> str:
    """服务器已打开的库，否则是上次打开的库，再否则是列表第一项。"""
    active_path = _path_for_name(valid_files, active_name)
    if active_path:
        return active_path
    return valid_files[_default_index(valid_files, active_name)]


def _activate_shown_database(valid_files: list, active_name: str) -> None:
    """页面初次显示时，on_change 不会发生。服务器还没打开库，就打开下拉框上的那一项。"""
    if _path_for_name(valid_files, active_name):
        st.session_state.pop("_db_bootstrap_target", None)
        return
    target = _shown_database(valid_files, active_name)
    if st.session_state.get("_db_bootstrap_target") == target:
        return
    if load_database(target):
        st.session_state.pop("_db_bootstrap_target", None)
        _remember_open_database(target)
        return
    st.session_state["_db_bootstrap_target"] = target


def _bind_open_database(widget_key: str, valid_files: list, active_name: str) -> None:
    """两个下拉框都写成同一个路径，避免各记一个 index。"""
    st.session_state[widget_key] = _shown_database(valid_files, active_name)


def render_database_selectbox(valid_files: list, *, widget_key: str, label: str = "💾 Database:"):
    """选择数据库。已在内存中的库只切换当前指针。"""
    client = get_db_port_client()
    try:
        health = client.health() if client else {}
    except Exception:
        health = {}
    active_name = health.get("db")
    _bind_open_database(widget_key, valid_files, active_name)
    selected = st.selectbox(
        label,
        options=valid_files,
        format_func=format_database_choice,
        key=widget_key,
        on_change=_switch_database,
        args=(widget_key,),
    )
    failed = set(health.get("failed") or [])
    if _resolved(selected) in failed and health.get("load_error"):
        st.warning(f"Load failed: {health.get('load_error')}")
    return selected


def _valid_databases(client, folder):
    valid_files = []
    for item in client.list_database_status(folder):
        if item.get("valid") and item.get("path"):
            valid_files.append(item["path"])
    return valid_files


def render_sidebar_database_selector():
    """渲染侧边栏的数据库选择器。"""
    client = get_db_port_client()
    if not client:
        st.error("❌ Database service is unavailable")
        return
    st.session_state["_db_switch_done"] = False
    custom_folder = st.session_state.get("custom_db_folder")
    try:
        valid_db_files = _valid_databases(client, custom_folder)
    except Exception:
        st.error("❌ Could not load the database list")
        return
    try:
        health = client.health()
        pending = int(health.get("disk_write_pending") or 0)
        disk_error = health.get("last_disk_error")
    except Exception:
        health = {}
        pending = 0
        disk_error = None
    if pending:
        st.caption(f"Writing to disk ({pending})")
    if disk_error:
        st.warning(f"Disk write failed: {disk_error}")
    if not valid_db_files:
        folder_desc = f"'{custom_folder}'" if custom_folder else "'databases'"
        st.selectbox(
            "💾 Database:",
            options=[f"None found in {folder_desc}"],
            disabled=True,
        )
    else:
        _activate_shown_database(valid_db_files, health.get("db") or "")
        try:
            health = client.health()
        except Exception:
            pass
        render_database_selectbox(valid_db_files, widget_key="sidebar_db_selector")
        if health.get("db") and st.session_state.get("db_has_unsaved_changes", False):
            st.markdown(
                """<div style='background-color: #ffcccc; padding: 5px; border-radius: 5px; margin-top: 5px;'>
                <small>⚠️ Unsaved changes</small>
                </div>""",
                unsafe_allow_html=True,
            )
