#!/usr/bin/env python3
"""
简化的数据库选择器组件 - 仅用于侧边栏
"""

import streamlit as st
from pathlib import Path
from ui.common import (
    get_db_port_client,
    get_database_name,
    load_database
)


def render_sidebar_database_selector():
    """渲染侧边栏的数据库选择器 - 简化版"""
    
    # 检查客户端是否可用
    client = get_db_port_client()
    if not client:
        st.error("❌ 数据库服务不可用")
        return
    
    # 获取当前数据库名称和状态
    current_db = get_database_name()
    if current_db == "N/A" or current_db == "Error":
        current_db = None
    
    # 检查是否有未保存的更改
    # 使用session state来跟踪
    has_unsaved_changes = st.session_state.get('db_has_unsaved_changes', False)
    
    # 获取自定义文件夹
    custom_folder = st.session_state.get('custom_db_folder')
    
    # 获取数据库列表
    try:
        db_files = client.list_databases(custom_folder)
        # 验证数据库
        valid_db_files = []
        for db_file in db_files:
            try:
                validation_result = client.validate_database_schema(db_file)
                if validation_result.get("valid", False):
                    valid_db_files.append(db_file)
            except Exception:
                pass
    except Exception:
        st.error("❌ 无法获取数据库列表")
        return
    # 创建选择界面
    if not valid_db_files:
        folder_desc = f"'{custom_folder}'" if custom_folder else "'databases'"
        st.selectbox(
            "💾 数据库:",
            options=[f"未在 {folder_desc} 中找到"],
            disabled=True
        )
    else:
        # 格式化显示名称
        def format_db_name(db_path):
            name = Path(db_path).name
            # 如果是当前数据库且有未保存更改，用红色显示
            if name == current_db and has_unsaved_changes:
                return f"🔴 {name}"
            elif name == current_db:
                return f"✅ {name}"
            else:
                return name 
        # 找到当前数据库的索引
        current_index = 0
        if current_db:
            try:
                db_names = [Path(db).name for db in valid_db_files]
                current_index = db_names.index(current_db)
            except ValueError:
                pass
        selected = st.selectbox(
            "💾 数据库:",
            options=valid_db_files,
            format_func=format_db_name,
            index=current_index,
            key="sidebar_db_selector"
        )
        # 如果选择改变，显示加载按钮
        if selected and Path(selected).name != current_db:
            if st.button("📥 加载", use_container_width=True, key="sidebar_load_db"):
                with st.spinner("加载中..."):
                    if load_database(selected):
                        st.success("✅ 已加载")
                        # 清除未保存状态
                        st.session_state.db_has_unsaved_changes = False
                        st.rerun()
                    else:
                        st.error("❌ 加载失败")
        # 显示当前数据库状态
        if current_db and has_unsaved_changes:
            st.markdown(
                """<div style='background-color: #ffcccc; padding: 5px; border-radius: 5px; margin-top: 5px;'>
                <small>⚠️ 有未保存的更改</small>
                </div>""", 
                unsafe_allow_html=True
            )