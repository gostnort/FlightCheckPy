#!/usr/bin/env python3
"""
Home page for HBPR UI - System overview and quick actions
"""

import streamlit as st
import pandas as pd
from ui.common import apply_global_settings, get_hbpr_database_client, is_db_available
from ui.components.home_metrics import get_home_summary
from ui.components.main_stats import get_and_display_main_statistics


def build_summary_message(summary):
    """构建摘要信息，只显示非零的部分
    
    Args:
        summary: 包含统计数据的字典
    
    Returns:
        str: 格式化的摘要信息
    """
    lines = []
    
    # 标题行 - 始终显示
    title = f"{summary['flight_number']} / {summary['flight_date']}"
    lines.append(title)
    
    # 总数行 - 始终显示
    total_line = f"TOTAL {summary['total_accepted']} + {summary['infant_count']} INF"
    lines.append(total_line)
    
    # 舱位分布 - 只显示非零的舱位
    class_parts = []
    if summary.get('accepted_first', 0) > 0:
        class_parts.append(f"F_{summary['accepted_first']}")
    if summary.get('accepted_business', 0) > 0:
        class_parts.append(f"J_{summary['accepted_business']}")
    if summary.get('accepted_economy', 0) > 0:
        class_parts.append(f"Y_{summary['accepted_economy']}")
    if class_parts:
        lines.append(f"ACCEPTED PAX: {" / ".join(class_parts)}")
    
    # 比率 - 始终显示
    ratio_display = f"{summary['ratio']}%" if summary['ratio'] is not None else "N/A"
    lines.append(f"RATIO: {ratio_display}")
    
    # ID员工 - 只显示非零的
    id_parts = []
    if summary.get('id_c', 0) > 0:
        id_parts.append(f"ID_J: {summary['id_c']}")
    if summary.get('id_y', 0) > 0:
        id_parts.append(f"ID_Y: {summary['id_y']}")
    if id_parts:
        lines.append("  ".join(id_parts))
    else:
        lines.append("ID: N/A")
    
    # NOSHOW - 只显示非零的
    noshow_parts = []
    if summary.get('noshow_f', 0) > 0:
        noshow_parts.append(f"F_{summary['noshow_f']}")
    if summary.get('noshow_c', 0) > 0:
        noshow_parts.append(f"J_{summary['noshow_c']}")
    if summary.get('noshow_y', 0) > 0:
        noshow_parts.append(f"Y_{summary['noshow_y']}")
    if noshow_parts:
        lines.append(f"NO_SHOW: {' / '.join(noshow_parts)}")
    else:
        lines.append("NO_SHOW: N/A")
    # INAD
    lines.append(f"INAD: {summary['inad_total']}")
    
    return "\n".join(lines)


def show_home_page():
    """显示主页"""
    apply_global_settings()
    # Create two columns for layout
    col1, col2 = st.columns(2)
    with col1:
        # 标题和刷新按钮在同一行
        header_col1, header_col2, not_used_col3 = st.columns([5, 2, 1])
        with header_col1:
            st.subheader("📊 Main Statistics")
        with header_col2:
            if st.button("🔄 Refresh", key="refresh_main_stats", use_container_width=True):
                # 清除缓存的数据库客户端实例，强制重新加载
                port = st.session_state.get("db_service_port")
                if port:
                    hbpr_client_key = f"hbpr_db_client_{port}"
                    if hbpr_client_key in st.session_state:
                        del st.session_state[hbpr_client_key]
                st.rerun()
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
                get_and_display_main_statistics(db)
        except Exception as e:
            st.error(f"❌ Error loading main statistics: {e}")
    with col2:
        st.subheader("📈 Home Summary")
        
        # 添加视图模式选择器
        view_mode = st.selectbox(
            "View Mode:",
            options=["Summary", "Flight Sheet"],
            key="home_view_mode"
        )
        
        if view_mode == "Summary":
            # 原有的摘要显示
            try:
                # Get home summary metrics
                summary = get_home_summary()
                if summary:
                    # 航班摘要信息折叠块 - 使用新函数构建消息（只显示非零项）
                    title = f"{summary['flight_number']} / {summary['flight_date']}"
                    with st.expander(title, expanded=True):
                        msg = build_summary_message(summary)
                        st.code(msg)
                else:
                    st.info("No summary data available.")
            except Exception as e:
                st.error(f"❌ Error loading home summary: {e}")
        else:  # Flight Sheet
            try:
                from ui.components.home_flight_sheet import build_flight_sheet_data, render_flight_sheet_table
                
                # 检查数据库状态
                if not is_db_available():
                    st.warning("⚠️ Please select a database to view flight sheet.")
                    return
                
                db = get_hbpr_database_client()
                if db:
                    with st.spinner("Building flight sheet..."):
                        sheet_data = build_flight_sheet_data(db)
                        render_flight_sheet_table(sheet_data)
                else:
                    st.warning("⚠️ Database not loaded")
            except Exception as e:
                st.error(f"❌ Error loading flight sheet: {e}")

    # 显示缺失号码表格
    missing_numbers = db.get_all_statistics().get('missing_numbers', []) if db.get_all_statistics() else []
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

