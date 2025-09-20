#!/usr/bin/env python3
"""
Home page for HBPR UI - System overview and quick actions
"""

import streamlit as st
import pandas as pd
from ui.common import apply_global_settings, get_hbpr_database_client, is_db_available
import os
from ui.components.home_metrics import get_home_summary
from ui.components.main_stats import get_and_display_main_statistics


def show_home_page():
    """显示主页"""
    apply_global_settings()

    # Create two columns for layout
    col1, col2 = st.columns([2, 1])

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
                get_and_display_main_statistics(db.get_all_statistics())
        except Exception as e:
            st.error(f"❌ Error loading main statistics: {e}")

    with col2:
        st.subheader("📈 Home Summary")
        try:
            # Get home summary metrics
            summary = get_home_summary()
            if summary:
                # 航班摘要信息折叠块
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
            else:
                st.info("No summary data available.")
        except Exception as e:
            st.error(f"❌ Error loading home summary: {e}")

    # 显示缺失号码表格
    missing_numbers = all_stats.get('missing_numbers', []) if all_stats else []
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
        messages.append("✅ No missing HBNB numbers found!")
    # 显示消息
    msg_length = len(messages)
    if msg_length > 0:
        # 根据消息数量动态创建列
        cols = st.columns(msg_length)
        for i, message in enumerate(messages):
            with cols[i]:
                st.success(message)
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

