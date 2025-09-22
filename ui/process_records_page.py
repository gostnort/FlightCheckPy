#!/usr/bin/env python3
"""
Process Records page for HBPR UI - Main navigation interface for record processing
"""

import streamlit as st
from ui.process_records.info import show_info_tab
from ui.process_records.add_hbprs import show_add_hbprs_tab
from ui.process_records.edit_hbpr import show_edit_hbpr_tab
from ui.process_records.add_commands import show_add_commands_tab
from ui.process_records.edit_command import show_edit_command_tab
from ui.process_records.timeline import show_timeline_tab


def show_process_records():
    """显示处理记录页面"""
    st.markdown("<h3>🔍 Process Records</h3>", unsafe_allow_html=True)

    if not st.session_state.get('authenticated', False):
        st.warning("⚠️ Please log in first.")
        return

    try:
        # 定义标签页选项
        tab_options = ["ℹ️ Info", "➕ Add HBPRs", "✏️ Edit a HBPR", "📝 Add Commands", "📋 Edit a Command", "📅 Timeline"]

        # 处理程序化标签页切换
        if hasattr(st.session_state, 'process_records_tab'):
            target_tab = st.session_state.process_records_tab
            # Find the index of the target tab to set as default
            try:
                default_index = tab_options.index(target_tab)
            except ValueError:
                default_index = 0
            del st.session_state.process_records_tab
        else:
            default_index = 0

        # 使用tabs来控制页面
        tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(tab_options)

        with tab1:
            show_info_tab()
        with tab2:
            show_add_hbprs_tab()
        with tab3:
            show_edit_hbpr_tab()
        with tab4:
            show_add_commands_tab()
        with tab5:
            show_edit_command_tab()
        with tab6:
            show_timeline_tab()

    except Exception as e:
        st.error(f"❌ Error: {str(e)}")
        st.info("💡 Please ensure you are logged in and have selected a database.")

