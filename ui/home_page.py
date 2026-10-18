#!/usr/bin/env python3
"""
Home page for HBPR UI - System overview and quick actions
"""

import streamlit as st
import pandas as pd
from ui.common import apply_global_settings, get_hbpr_database_client, is_db_available, reload_database_from_disk
from ui.components.flight_summary import build_summary_message
from ui.components.main_stats import display_main_statistics
from ui.components.home_flight_sheet import build_flight_sheet_data, render_flight_sheet_table, has_required_sy_commands


def show_home_page():
    """显示主页"""
    apply_global_settings()
    # Create two columns for layout
    col1, col2 = st.columns([3,2])
    with col1:
        st.subheader("📊 Main Statistics")
        try:
            # 检查数据库状态
            if not is_db_available():
                st.warning("⚠️ Please select a database from the sidebar to begin.")
                return
            # 使用内存数据库
            db = get_hbpr_database_client()
            if db is None:
                st.error("❌ No database loaded in memory")
                return
            with st.spinner("Loading database statistics..."):
                all_stats = db.get_all_statistics()
                display_main_statistics(all_stats)
        except Exception as e:
            st.error(f"❌ Error loading main statistics: {e}")
    with col2:
        # 航班摘要信息折叠块 - 使用新函数构建消息（只显示非零项）
        try:
            msg = build_summary_message()
            if msg:
                with st.expander('📈 Home Summary', expanded=True):
                    st.code(msg)
            else:
                st.info("No summary data available.")
        except Exception as e:
            st.error(f"❌ Error loading home summary: {e}")
        button_col1, button_col2 = st.columns(2)
        with button_col1:
            if st.button("🔄 Refresh", key="refresh_main_stats", use_container_width=True):
                # 清除所有组件相关的缓存数据，强制重新加载
                port = st.session_state.get("db_service_port")
                if port:
                    # 清除数据库客户端缓存
                    hbpr_client_key = f"hbpr_db_client_{port}"
                    if hbpr_client_key in st.session_state:
                        del st.session_state[hbpr_client_key]
                    # 清除其他可能的组件缓存
                    db_port_client_key = f"db_port_client_{port}"
                    if db_port_client_key in st.session_state:
                        del st.session_state[db_port_client_key]
                # 清除组件相关的缓存状态
                cache_keys_to_clear = [
                    'home_metrics_cache',
                    'main_stats_cache',
                    'flight_sheet_cache'
                ]
                for key in cache_keys_to_clear:
                    if key in st.session_state:
                        del st.session_state[key]
                st.rerun()
        with button_col2:
            if st.button("📥 Reload DB", key="reload_database", use_container_width=True):
                # 从磁盘重新加载数据库以反映手动更改
                reload_database_from_disk()
                st.rerun()
    # 显示缺失号码表格
    missing_numbers = db.get_missing_hbnb_numbers() if db else []
    if missing_numbers:
        st.subheader("🚫 Missing HBNB Numbers")
        # 分页显示缺失号码
        items_per_page = 20
        total_pages = (len(missing_numbers) + items_per_page - 1) // items_per_page
        if total_pages > 1:
            page = st.selectbox("Page:", range(1, total_pages + 1), key="missing_page")
            start_idx = (page - 1) * items_per_page
            end_idx = min(start_idx + items_per_page, len(missing_numbers))
            page_missing = missing_numbers[start_idx:end_idx]
        else:
            page_missing = missing_numbers
        # 创建缺失号码的DataFrame
        missing_df = pd.DataFrame({
            'Missing HBNB Numbers': page_missing
        })
        st.dataframe(missing_df, use_container_width=True)
        if total_pages > 1:
            st.info(f"Showing page {page} of {total_pages} ({len(page_missing)} of {len(missing_numbers)} missing numbers)")
    # 创建航班表格 - 仅在同时存在到达和出发SY命令时显示
    db = get_hbpr_database_client()
    if db:
        if has_required_sy_commands(db):
            with st.spinner("Building flight sheet..."):
                sheet_data = build_flight_sheet_data(db)
                render_flight_sheet_table(sheet_data)
        # 如果没有必要的SY命令，不显示任何内容（静默跳过）
    else:
        st.warning("⚠️ Database not loaded")
    st.markdown("---")
    # 最近活动
    st.subheader("📝 Navigation guide")
    col_left, col_right = st.columns(2)
    with col_left:
        st.markdown("""
        ## 🗄️ **Database**
        - Create, import, and manage databases from HBPR list files.
        - View flight information and database status.
        - Save and load databases through the in-memory service.
        ## 🔍 **Process Records**
        - Add or edit HBPR and PR passenger records by hand.
        - Check HBPR and PR format and content.
        - Replace or copy an existing record.
        - Track missing HBNB numbers.
        - Process HBPR records in bulk.
        """)
    with col_right:
        st.markdown("""
        ## 📊 **EMD Summary**
        - Import the EMD sales daily Excel file.
        - Match TKNE ticket numbers to HBPR records and read CKIN CCRD.
        - Handle void EMDs.
        - Write a formatted Excel report.
        ## 📋 **Commands**
        - Parse, check, and manage AIRC, SY, and other system commands.
        - Read flight number and date from a command.
        - Keep command versions and history.
        - Delete or edit a command record.
        ## ⚙️ **Settings**
        - Set the font family and size.
        **Start here:** pick or create a database in the sidebar, then open a page from the navigation buttons.
        """)

