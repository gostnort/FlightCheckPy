#!/usr/bin/env python3
"""
View Results page for HBPR UI - Results analysis and export interface
"""

import streamlit as st
import pandas as pd
import os
import sqlite3
import re
from datetime import datetime
from io import BytesIO
from scripts.hbpr_info_processor import HbprDatabase
from ui.common import apply_global_settings, get_current_database


def show_view_results():
    """显示结果查看页面"""
    # Apply settings
    apply_global_settings()
    
    st.header("📊 View Processing Results")
    
    try:
        # 获取当前选中的数据库
        selected_db_file = get_current_database()
        
        if not selected_db_file:
            st.error("❌ No database selected.")
            st.info("💡 Please select a database from the sidebar or build one first in the Database Management page.")
            return
        
        db = HbprDatabase(selected_db_file)
        
        tab1, tab2, tab3 = st.tabs(["📈 Statistics", "📋 Records Table", "📤 Export Data"])
        
        with tab1:
            show_statistics(db)
        
        with tab2:
            show_records_table(db)
        
        with tab3:
            show_export_options(db)
    
    except Exception as e:
        st.error(f"❌ Database not available: {str(e)}")
        st.info("💡 Please select a database from the sidebar or build one first in the Database Management page.")


def show_statistics(db):
    """显示统计信息"""
    st.subheader("📈 HBNB Range Statistics")
    
    range_info = db.get_hbnb_range_info()
    missing_numbers = db.get_missing_hbnb_numbers()
    
    # 主要指标
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("HBNB Range", f"{range_info['min']} - {range_info['max']}")
    with col2:
        st.metric("Total Expected", range_info['total_expected'])
    with col3:
        st.metric("Total Found", range_info['total_found'])
    with col4:
        st.metric("Missing Numbers", len(missing_numbers))
    
    # 完整性率
    if range_info['total_expected'] > 0:
        completeness_rate = (range_info['total_found'] / range_info['total_expected']) * 100
        missing_rate = (len(missing_numbers) / range_info['total_expected']) * 100
        
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Completeness Rate", f"{completeness_rate:.1f}%")
        with col2:
            st.metric("Missing Rate", f"{missing_rate:.1f}%")
    
    # 显示缺失号码表格
    if missing_numbers:
        st.subheader("🚫 Missing HBNB Numbers")
        # 分页显示缺失号码
        items_per_page = 30
        total_pages = (len(missing_numbers) + items_per_page - 1) // items_per_page
        
        if total_pages > 1:
            page = st.selectbox("Page:", range(1, total_pages + 1), key="stats_missing_page")
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


def show_records_table(db):
    """显示记录表格"""
    st.subheader("📋 Processed Records")
    
    try:
        conn = sqlite3.connect(db.db_file)
        
        # 查询已处理的记录，包括properties、ckin_msg和asvc_msg字段
        df = pd.read_sql_query("""
            SELECT hbnb_number, boarding_number, name, seat, class, destination,
                   bag_piece, bag_weight, ff, ckin_msg, properties, asvc_msg, error_count
            FROM hbpr_full_records 
            WHERE is_validated = 1
            ORDER BY hbnb_number
        """, conn)
        conn.close()
        
        if df.empty:
            st.info("ℹ️ No processed records found.")
            return
        
        # 提取FF Level（从FF字段中提取最后的字母）
        def extract_ff_level(ff_value):
            if pd.isna(ff_value) or ff_value == '':
                return 'N/A'
            # 提取FF号码最后的字母，如 "CA 050021619897/B" -> "B"
            parts = ff_value.split('/')
            if len(parts) > 1:
                return parts[-1]
            return 'N/A'

        # 添加FF Level列
        df['ff_level'] = df['ff'].apply(extract_ff_level)
        
        # 提取CKIN类型（从CKIN_MSG中提取所有CKIN类型）
        def extract_ckin_type(ckin_msg):
            if pd.isna(ckin_msg) or ckin_msg == '':
                return ''
            # 分割CKIN消息并提取所有CKIN类型
            ckin_list = [msg.strip() for msg in ckin_msg.split(';') if msg.strip()]
            ckin_types = []
            for ckin_msg_item in ckin_list:
                # 匹配 CKIN 后跟 4个字母数字字符，然后是非数字字符
                match = re.search(r'CKIN\s+([A-Z0-9]{4})[^0-9]', ckin_msg_item)
                if match:
                    ckin_types.append(match.group(1))
            return ckin_types

        # 添加CKIN类型列（包含所有CKIN类型，用逗号分隔）
        df['ckin_types'] = df['ckin_msg'].apply(lambda x: ', '.join(extract_ckin_type(x)) if extract_ckin_type(x) else '')
        
        # 收集所有唯一的CKIN类型用于过滤器
        all_ckin_types = set()
        for ckin_types_str in df['ckin_types'].dropna():
            if ckin_types_str != '':
                types_list = [t.strip() for t in ckin_types_str.split(',') if t.strip()]
                all_ckin_types.update(types_list)
        
        # 过滤选项
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            filter_class = st.multiselect("Filter by Class:", df['class'].dropna().unique())
        
        with col2:
            # FF Level过滤器
            ff_levels = sorted(df['ff_level'].dropna().unique())
            filter_ff_level = st.multiselect("Filter by FF Level:", ff_levels)
        
        with col3:
            # CKIN类型过滤器
            available_ckin_types = sorted(list(all_ckin_types))
            filter_ckin_type = st.multiselect("Filter by CKIN Type:", available_ckin_types)
        
        with col4:
            # Properties过滤器 - 替换destination过滤器
            # 从properties字段中提取所有唯一的属性
            all_properties = set()
            for properties_str in df['properties'].dropna():
                if properties_str:
                    properties_list = [prop.strip() for prop in properties_str.split(',') if prop.strip()]
                    all_properties.update(properties_list)
            
            available_properties = sorted(list(all_properties))
            filter_properties = st.multiselect("Filter by Properties:", available_properties)
        
        # 应用过滤器
        filtered_df = df.copy()
        
        if filter_class:
            filtered_df = filtered_df[filtered_df['class'].isin(filter_class)]
        
        if filter_ff_level:
            filtered_df = filtered_df[filtered_df['ff_level'].isin(filter_ff_level)]
        
        if filter_ckin_type:
            # 过滤包含选定CKIN类型的记录
            def has_ckin_type(ckin_types_str, target_ckin_types):
                if pd.isna(ckin_types_str) or ckin_types_str == '':
                    return False
                types_list = [t.strip() for t in ckin_types_str.split(',') if t.strip()]
                return any(ckin_type in types_list for ckin_type in target_ckin_types)
            
            filtered_df = filtered_df[filtered_df['ckin_types'].apply(
                lambda x: has_ckin_type(x, filter_ckin_type)
            )]
        
        if filter_properties:
            # 过滤包含选定属性的记录
            def has_property(properties_str, target_properties):
                if pd.isna(properties_str) or properties_str == '':
                    return False
                properties_list = [prop.strip() for prop in properties_str.split(',') if prop.strip()]
                return any(prop in properties_list for prop in target_properties)
            
            filtered_df = filtered_df[filtered_df['properties'].apply(
                lambda x: has_property(x, filter_properties)
            )]
        
        # 显示表格（不显示ff_level和ckin_types列，因为它们只是用于过滤）
        display_df = filtered_df.drop(columns=['ff_level', 'ckin_types'])
        
        st.dataframe(
            display_df,
            use_container_width=True,
            hide_index=True,  # 隐藏自动序列号
            column_config={
                "hbnb_number": st.column_config.NumberColumn("HBNB", format="%d"),
                "boarding_number": st.column_config.NumberColumn("BN", format="%d"),
                "name": "Name",
                "seat": "Seat",
                "class": "Class",
                "destination": "Destination", 
                "bag_piece": st.column_config.NumberColumn("Bag Pieces", format="%d"),
                "bag_weight": st.column_config.NumberColumn("Bag Weight", format="%d kg"),
                "ff": "FF Number",
                "properties": "Properties",
                "ckin_msg": st.column_config.TextColumn("CKIN Messages", max_chars=100),
                "asvc_msg": st.column_config.TextColumn("ASVC Messages", max_chars=100),
                "error_count": st.column_config.NumberColumn("Errors", format="%d")
            }
        )
        
        st.info(f"📊 Showing {len(filtered_df)} of {len(df)} records")
    
    except Exception as e:
        st.error(f"❌ Error loading records: {str(e)}")


def show_export_options(db):
    """显示导出选项"""
    st.subheader("📤 Export Data")
    
    try:
        conn = sqlite3.connect(db.db_file)
        
        # 获取所有已处理的记录
        df = pd.read_sql_query("""
            SELECT * FROM hbpr_full_records 
            WHERE is_validated = 1
            ORDER BY hbnb_number
        """, conn)
        
        conn.close()
        
        if df.empty:
            st.info("ℹ️ No processed records to export.")
            return
        
        col1, col2 = st.columns(2)
        
        with col1:
            # CSV导出
            csv_data = df.to_csv(index=False)
            st.download_button(
                label="📥 Download as CSV",
                data=csv_data,
                file_name=f"hbpr_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv",
                use_container_width=True
            )
        
        with col2:
            # Excel导出
            excel_buffer = BytesIO()
            df.to_excel(excel_buffer, index=False, engine='openpyxl')
            excel_data = excel_buffer.getvalue()
            st.download_button(
                label="📊 Download as Excel",
                data=excel_data,
                file_name=f"hbpr_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )
        
        # 显示导出预览
        st.subheader("👀 Export Preview")
        st.dataframe(df.head(10), use_container_width=True)
        st.info(f"📊 Total records ready for export: {len(df)}")
    
    except Exception as e:
        st.error(f"❌ Error preparing export: {str(e)}")