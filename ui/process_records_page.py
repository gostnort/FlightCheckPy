#!/usr/bin/env python3
"""
Process Records page for HBPR UI - Main navigation interface for record processing
"""

import streamlit as st
from ui.db_management import apply_global_settings, require_database_loaded
from ui.process_records.add_edit_record import show_add_edit_record
from ui.process_records.process_all import show_process_all_records
from ui.process_records.simple_record import show_simple_record
from ui.process_records.export_data import show_export_data
from ui.process_records.sort_records import show_sort_records


@require_database_loaded()
def show_process_records():
    """显示处理记录页面"""
    # Apply settings
    apply_global_settings()
    try:
        # 定义标签页选项
        tab_options = ["🚀 Process All Records", "✏️ Add/Edit Record", "🧻 Simple Record", "📋 Sort Records", "📤 Export Data"]
        
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
        tab1, tab2, tab3, tab4, tab5 = st.tabs(tab_options)

        with tab1:
            show_process_all_records()
        with tab2:
            show_add_edit_record()
        with tab3:
            show_simple_record()
        with tab4:
            show_sort_records()
        with tab5:
            show_export_data()

    except Exception as e:
        st.error(f"❌ Database not available: {str(e)}")
        st.info("💡 Please build a database first in the Database Management page.")

