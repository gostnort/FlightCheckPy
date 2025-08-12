#!/usr/bin/env python3
"""
Process All Records functionality for HBPR UI - Batch processing and error handling
"""

import streamlit as st
import pandas as pd
import sqlite3
from scripts.hbpr_info_processor import CHbpr, HbprDatabase
from ui.common import get_current_database


def show_process_all_records():
    """显示处理所有记录页面"""
    try:
        db = HbprDatabase()
        db.find_database()
        
        # 获取当前选中的数据库
        selected_db_file = get_current_database()    
        if not selected_db_file:
            st.error("❌ No database selected! Please select a database from the sidebar.")
            return
        # 如果选择了不同的数据库，重新初始化
        if selected_db_file != db.db_file:
            db = HbprDatabase(selected_db_file)
        # 处理控制
        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown("**Processing Options:**")
        with col2: 
            if st.button("🚀 Start Processing", use_container_width=True):
                    start_processing_all_records(db, None)  # Always process all records
        with col3:
            if st.button("🧹 Erase Result", use_container_width=True):
                erase_splited_records(db)
        # 显示错误分组统计
        show_error_summary(db)
        # 显示错误信息
        show_error_messages(db)     
    except Exception as e:
        st.error(f"❌ Error accessing database: {str(e)}")


def start_processing_all_records(db, batch_size):
    """开始处理所有记录"""
    try:
        # 获取所有记录
        conn = sqlite3.connect(db.db_file)
        cursor = conn.cursor()
        cursor.execute("SELECT hbnb_number FROM hbpr_full_records ORDER BY hbnb_number")
        records = [row[0] for row in cursor.fetchall()]
        conn.close()
        
        if not records:
            st.info("ℹ️ No records found.")
            return
        
        results_container = st.container()
        
        processed_count = 0
        valid_count = 0
        error_count = 0
        
        # 使用spinner显示处理状态
        with st.spinner(f"🔄 Processing {len(records)} records..."):
            for hbnb_number in records:
                try:
                    # 处理记录
                    content = db.get_hbpr_record(hbnb_number)
                    chbpr = CHbpr()
                    chbpr.run(content)
                    
                    # 更新数据库
                    success = db.update_with_chbpr_results(chbpr)
                    
                    if success:
                        processed_count += 1
                        if chbpr.is_valid():
                            valid_count += 1
                        else:
                            error_count += 1
                    
                except Exception as e:
                    # 静默处理错误，不显示具体错误信息
                    pass
        
        # 显示结果总结
        with results_container:
            st.success(f"🎉 Processed {processed_count} records")
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("Total Processed", processed_count)
            with col2:
                st.metric("Valid Records", valid_count)
            with col3:
                st.metric("Records with Errors", error_count)
        
        # 自动刷新页面以显示新的错误信息
        st.rerun()
    
    except Exception as e:
        st.error(f"❌ Processing error: {str(e)}")


def erase_splited_records(db):
    """清除所有处理结果，重置hbpr_full_records表中的处理字段"""
    try:
        with st.spinner("🧹 Erasing all processing results..."):
            # 调用数据库类的erase_splited_records方法
            success = db.erase_splited_records()
            
            if success:
                st.success("✅ Successfully erased all processing results!")
                st.info("ℹ️ All processing fields have been reset. Only HBNB numbers and raw content remain.")
                
                # 自动刷新页面以显示更新后的状态
                st.rerun()
            else:
                st.error("❌ Failed to erase processing results.")
    
    except Exception as e:
        st.error(f"❌ Error during cleanup: {str(e)}")


def show_error_summary(db):
    """显示错误分组统计"""
    try:
        conn = sqlite3.connect(db.db_file)
        # 查询有错误的记录
        df = pd.read_sql_query("""
            SELECT error_baggage, error_passport, error_name, error_visa, error_other
            FROM hbpr_full_records 
            WHERE is_validated = 1 AND is_valid = 0 AND error_count > 0
        """, conn)
        conn.close()
        if df.empty:
            st.info("ℹ️ No error messages found. All processed records are valid!")
            return
        # 统计每种错误类型的数量
        error_types = ['error_baggage', 'error_passport', 'error_name', 'error_visa', 'error_other']
        error_labels = ['Baggage', 'Passport', 'Name', 'Visa', 'Other']
        error_counts = {}
        for error_type, label in zip(error_types, error_labels):
            # 计算非空错误的数量
            count = df[df[error_type].notna() & (df[error_type] != '')].shape[0]
            error_counts[label] = count
        # 显示错误统计
        total_records_with_errors = len(df)
        st.write(f"📊 **Total records with errors: {total_records_with_errors}**")
        labels = {'Baggage': '🧳',
                   'Passport': '🪪', 'Name': '👤', 'Visa': '🛂', 'Other': '🔧'}
        # 使用列显示每种错误类型的统计
        cols = st.columns(5)
        for i, (label, count) in enumerate(error_counts.items()):
            with cols[i]:
                st.metric(
                    label=f"{labels[label]} {label}",
                    value=count
                )
    except Exception as e:
        st.error(f"❌ Error loading error summary: {str(e)}")


def show_error_messages(db):
    """显示错误信息"""
    try:
        conn = sqlite3.connect(db.db_file)
        # 查询有错误的记录
        df = pd.read_sql_query("""
            SELECT hbnb_number, name, error_count, error_baggage, error_passport, error_name, error_visa, error_other, validated_at
            FROM hbpr_full_records 
            WHERE is_validated = 1 AND is_valid = 0 AND error_count > 0
            ORDER BY validated_at DESC, hbnb_number
        """, conn)
        conn.close()
        if df.empty:
            st.info("ℹ️ No error messages found. All processed records are valid!")
            return
        # 添加错误类型过滤下拉框（移除"All"选项）
        error_types = ['Baggage', 'Passport', 'Name', 'Visa', 'Other']
        selected_error_type = st.selectbox(
            "🔍 Filter by Error Type:",
            error_types
        )
        # 根据选择的错误类型过滤记录
        error_field_map = {
            'Baggage': 'error_baggage',
            'Passport': 'error_passport', 
            'Name': 'error_name',
            'Visa': 'error_visa',
            'Other': 'error_other'
        }
        error_field = error_field_map[selected_error_type]
        df = df[df[error_field].notna() & (df[error_field] != '')]
        if df.empty:
            st.info(f"ℹ️ No {selected_error_type} error messages found!")
            return
        # 显示错误统计
        total_errors = len(df)
        st.write(f"**Found {total_errors} records with errors:**")
        # 分页显示错误信息
        items_per_page = 10
        total_pages = (total_errors + items_per_page - 1) // items_per_page
        if total_pages > 1:
            page = st.selectbox("Page:", range(1, total_pages + 1), key="error_page")
            start_idx = (page - 1) * items_per_page
            end_idx = min(start_idx + items_per_page, total_errors)
            page_df = df.iloc[start_idx:end_idx]
        else:
            page_df = df
        # 初始化session state用于跟踪哪个记录显示弹窗
        if 'show_popup_for' not in st.session_state:
            st.session_state.show_popup_for = None
        # 显示错误记录
        for _, row in page_df.iterrows():
            # 构建选中错误类型的文本用于显示在expander标题中
            error_field = error_field_map[selected_error_type]
            if row[error_field] and row[error_field].strip():
                # 取错误文本的前70个字符用于标题显示
                CONST_ERROR_PREVIEW_LENGTH = 70
                error_preview = row[error_field].strip()[:CONST_ERROR_PREVIEW_LENGTH]
                if len(row[error_field].strip()) > CONST_ERROR_PREVIEW_LENGTH:
                    error_preview += "..."
                display_error = error_preview
            else:
                display_error = "Unknown error"
            
            with st.expander(f"🚫 {display_error}"):
                st.write(f"**Validated at:** {row['validated_at']}")
                # 添加查看记录的弹出窗口
                col1, col2, col3 = st.columns([3, 1, 1])
                with col1:
                    st.write("**Quick Actions:**")
                with col2:
                    # 切换到Add/Edit Record标签页的按钮
                    if st.button("✏️ Edit", key=f"edit_{row['hbnb_number']}", use_container_width=True):
                        # 设置要切换的标签页
                        st.session_state.process_records_tab = "✏️ Add/Edit Record"
                        # 设置要选择的HBNB号码
                        st.session_state.selected_hbnb_for_edit = row['hbnb_number']
                        st.rerun()
                with col3:
                    # 根据当前状态显示不同的按钮样式
                    is_viewing = st.session_state.show_popup_for == row['hbnb_number']
                    button_text = "❌ Close" if is_viewing else "👀 View"
                    if st.button(button_text, key=f"view_{row['hbnb_number']}", use_container_width=True):
                        if is_viewing:
                            st.session_state.show_popup_for = None
                        else:
                            st.session_state.show_popup_for = row['hbnb_number']
                        st.rerun()
                # 如果当前记录需要显示弹窗，则显示弹窗内容
                if st.session_state.show_popup_for == row['hbnb_number']:
                    show_record_popup(db, row['hbnb_number'])
                # 显示选中的错误类型信息
                error_field = error_field_map[selected_error_type]
                if row[error_field] and row[error_field].strip():
                    # 使用markdown来支持换行显示
                    error_text = row[error_field].replace('\n', '<br>')
                    st.markdown(f"🔴 **{selected_error_type}:** {error_text}", unsafe_allow_html=True)
        
        if total_pages > 1:
            st.info(f"Showing page {page} of {total_pages} ({len(page_df)} of {total_errors} records)")
    except Exception as e:
        st.error(f"❌ Error loading error messages: {str(e)}")


def show_record_popup(db, hbnb_number):
    """显示记录的弹出窗口"""
    try:
        # 获取原始内容
        content = db.get_hbpr_record(hbnb_number)
        # Apply dynamic font settings
        apply_font_settings()
        # 显示原始内容，使用全宽度
        st.text_area(
            "Raw Content:",
            content,
            height=400,
            disabled=True,
            key=f"popup_content_{hbnb_number}",
        )
    except Exception as e:
        st.error(f"❌ Error retrieving record: {str(e)}")


def apply_font_settings():
    """Apply dynamic font settings from session state"""
    # Get font settings from session state
    font_family = st.session_state.get('settings', {}).get('font_family', 'Courier New')
    font_size_percent = st.session_state.get('settings', {}).get('font_size_percent', 100)
    
    # Calculate font size in pixels (assuming default is 14px)
    font_size_px = int(14 * font_size_percent / 100)
    
    # Apply font settings using CSS
    st.markdown(f"""
    <style>
    .stTextArea textarea {{
        font-family: '{font_family}', monospace !important;
        font-size: {font_size_px}px !important;
    }}
    .stDataFrame {{
        font-family: '{font_family}', monospace !important;
        font-size: {font_size_px}px !important;
    }}
    </style>
    """, unsafe_allow_html=True)
