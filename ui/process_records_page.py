#!/usr/bin/env python3
"""
Process Records page for HBPR UI - Main navigation interface for record processing
"""

import streamlit as st
from ui.common import apply_global_settings
from ui.process_records import (
    show_process_all_records,
    show_add_edit_record,
    show_simple_record,
    show_sort_records,
    show_export_data
)


def show_process_records():
    """显示记录处理页面"""
    # Apply settings
    apply_global_settings()
    try:
        # 定义标签页选项
        tab_options = ["🚀 Process All Records", "✏️ Add/Edit Record", "🧻 Simple Record", "📋 Sort Records", "📤 Export Data"]
        # 初始化默认选择（如果还没有设置）
        if "tab_selector" not in st.session_state:
            st.session_state.tab_selector = tab_options[0]
        # 处理程序化标签页切换
        if hasattr(st.session_state, 'process_records_tab'):
            target_tab = st.session_state.process_records_tab
            if target_tab in tab_options:
                st.session_state.tab_selector = target_tab
            del st.session_state.process_records_tab
        # 使用radio按钮来控制标签页（不设置index，让key自动管理）
        selected_tab = st.radio(
            label="Navigation tabs",
            options=tab_options,
            horizontal=True,
            key="tab_selector",
            label_visibility="collapsed"
        )
        st.markdown("---")
        # 根据选择的标签页显示相应内容
        if selected_tab == "🚀 Process All Records":
            show_process_all_records()
        elif selected_tab == "✏️ Add/Edit Record":
            show_add_edit_record()
        elif selected_tab == "🧻 Simple Record":
            show_simple_record()
        elif selected_tab == "📋 Sort Records":
            show_sort_records()
        elif selected_tab == "📤 Export Data":
            show_export_data()
    except Exception as e:
        st.error(f"❌ Database not available: {str(e)}")
        st.info("💡 Please build a database first in the Database Management page.")

