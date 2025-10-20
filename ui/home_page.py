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
    st.subheader("📝 导航指南")
    col_left, col_right = st.columns(2)
    with col_left:
        st.markdown("""
        ## 🗄️ **数据库管理**
        - 从HBPR列表文件创建、导入和管理数据库。
        - 查看航班信息和数据库状态。
        - 自动保存和加载数据库到内存服务。
        ## 🔍 **记录处理** 
        - 手动添加/编辑HBPR和PR（旅客记录）。
        - 验证HBPR和PR记录的格式和内容。
        - 替换或复制现有记录。
        - 追踪和更新HBNB（航班登机号）缺失情况。
        - 批量处理HBPR记录。
        """)
    with col_right:
        st.markdown("<br><br>", unsafe_allow_html=True)
        st.markdown("""
        ## 📊 **Excel处理器**
        - 导入EMD（电子杂费单）销售日报Excel文件。
        - 自动匹配TKNE（票号）与HBPR记录，并提取CKIN CCRD（值机信用卡）信息。
        - 处理废票（Void EMDs）。
        - 生成格式化的输出Excel报告。
        ## 📋 **指令分析**
        - 解析、验证和管理AIRC、SY等系统指令。
        - 提取指令中的航班号和日期信息。
        - 支持指令的版本控制和历史查看。
        - 删除或编辑指令记录。
        ## ⚙️ **设置**
        - 配置字体族和大小偏好。
        **💡 开始使用：** 从边栏下拉菜单中选择或创建数据库，然后使用导航按钮访问所需功能。
        """)

