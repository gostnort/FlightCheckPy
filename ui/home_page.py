#!/usr/bin/env python3
"""
Home page for HBPR UI - System overview and quick actions
"""

import streamlit as st
import pandas as pd
from ui.common import apply_global_settings, get_current_database
from scripts.hbpr_info_processor import HbprDatabase
import os
from ui.components.home_metrics import get_home_summary


def show_home_page():
    """显示主页"""
    # Apply settings
    apply_global_settings()
    # 检查是否需要刷新
    if 'refresh_home' in st.session_state and st.session_state.refresh_home:
        st.session_state.refresh_home = False
        st.rerun()
    col1, col2 = st.columns([3,2])
    with col1:
        st.subheader("📈 System Overview")
        # 检查数据库状态
        try:
            # 获取当前选中的数据库
            selected_db_file = get_current_database()
            if not selected_db_file:
                st.error("❌ No database selected!")
                st.info("💡 Please select a database from the sidebar or build one first using the Database Management page.")
                return
            # 使用选中的数据库
            db = HbprDatabase(selected_db_file)
            st.success(f"DB connected: {os.path.basename(selected_db_file)}")
            # Display main statistics using reusable component
            from ui.components.main_stats import get_and_display_main_statistics
            all_stats = get_and_display_main_statistics(db)
            
            # Extract data for additional sections
            missing_numbers = all_stats.get('missing_numbers', []) if all_stats else []
            # 显示缺失号码表格
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
            else:
                st.success("✅ No missing HBNB numbers found!")
        except Exception as e:
            st.error(f"❌ No database found: {str(e)}")
            st.info("💡 Please build a database first using the Database Management page.")
    with col2:
        st.subheader("🚀 Quick Actions")
        if st.button("✏️ Add/Edit HBPR Record", use_container_width=True):
            st.session_state.current_page = "🔍 Process Records"
            st.session_state.process_records_tab = "✏️ Add/Edit Record"
            st.rerun()
        if st.button("✒️ Add/Edit Command", use_container_width=True):
            st.session_state.current_page = "📋 Other Commands"
            st.session_state.command_analysis_tab = "✒️ Add/Edit Data"
            st.rerun()
        if st.button("🔄 Refresh Statistics", use_container_width=True):
            # 强制刷新所有统计信息
            db.invalidate_statistics_cache()
            st.rerun()
        # 航班摘要信息折叠块
        try:
            summary = get_home_summary(selected_db_file)
            title = f"{summary['flight_number']} / {summary['flight_date']}"
            with st.expander(title, expanded=True):
                total_line = f"TOTAL {summary['total_accepted']} + {summary['infant_count']} INF"
                j_y_line = f"J_{summary['accepted_business']} / Y_{summary['accepted_economy']}"
                ratio_display = f"{summary['ratio']}%" if summary['ratio'] is not None else "N/A"
                ratio_line = f"RATIO: {ratio_display}"
                id_line = f"ID_J: {summary['id_j']}  ID_Y: {summary['id_y']}"
                noshow_line = f"NOSHOW: J_{summary['noshow_j']} / Y_{summary['noshow_y']}"
                inad_line = f"INAD: {summary['inad_total']}"
                msg = "\n".join([
                    title,
                    total_line,
                    j_y_line,
                    ratio_line,
                    id_line,
                    noshow_line,
                    inad_line,
                ])
                st.code(msg)
        except Exception as e:
            st.info(f"Summary not available: {str(e)}")
    st.markdown("---")
    # 最近活动
    st.subheader("📝 导航指南")
    col_left, col_right = st.columns(2)
    with col_left:
        st.markdown("""
        使用左侧边栏中的导航按钮访问不同功能：
        ## 🗄️ **数据库管理**
        - 从HBPR列表文件构建数据库
        - 导入和处理HBPR列表数据
        - 管理数据库文件并查看航班信息
        ## 🔍 **处理记录** 
        - 手动添加/编辑单个HBPR记录
        - 验证和处理所有记录
        - 创建简单的HBNB占位符
        - 将处理后的数据导出到Excel
        - 对记录进行排序和筛选
        ## 📊 **Excel处理器**
        - 导入包含TKNE数据的Excel文件
        - 处理EMD销售日报
        - 生成格式化的输出文件
        - 自动匹配CKIN CCRD记录
        """)
    with col_right:
        st.markdown("<br><br>", unsafe_allow_html=True)
        st.markdown("""
        ## 📋 **其他指令**
        - 添加/编辑指令分析数据  
        - 处理EMD（电子杂费单）记录
        - 分析指令模式和验证
        ## ⚙️ **设置**
        - 配置字体族和大小偏好
        
        **💡 开始使用：** 从边栏下拉菜单中选择数据库，然后使用导航按钮访问所需功能。
        """)

