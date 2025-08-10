#!/usr/bin/env python3
"""
Sort Records functionality for HBPR UI - Record sorting and filtering interface
"""

import streamlit as st
import pandas as pd
import sqlite3
import re
from scripts.hbpr_info_processor import HbprDatabase
from ui.common import get_current_database


def show_sort_records():
    """显示记录表格"""
    try:
        # 获取当前选中的数据库
        selected_db_file = get_current_database()
        
        if not selected_db_file:
            st.error("❌ No database selected.")
            st.info("💡 Please select a database from the sidebar or build one first in the Database Management page.")
            return
        
        db = HbprDatabase(selected_db_file)
        
        st.subheader("📋 Processed Records")
        
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
