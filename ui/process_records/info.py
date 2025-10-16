#!/usr/bin/env python3
"""
信息标签页用于流程记录页面 - 仅错误显示
"""

import pandas as pd
import streamlit as st

from ui.common import get_hbpr_database_client, is_db_available
from .edit_hbpr import apply_font_settings


def execute_query_to_dataframe(db, query, params=None):
    """
    Execute a SQL query using the remote connection and return results as pandas DataFrame.
    This avoids pandas compatibility issues with RemoteSqliteConnection.
    """
    try:
        conn = db.get_connection()
        cursor = conn.cursor()
        cursor.execute(query, params or [])

        # Get column names from cursor description
        if cursor.description:
            columns = [desc[0] for desc in cursor.description]
        else:
            columns = []

        # Get all rows
        rows = cursor.fetchall()

        # Create DataFrame
        if columns and rows:
            return pd.DataFrame(rows, columns=columns)
        elif columns:
            return pd.DataFrame(columns=columns)
        else:
            return pd.DataFrame()

    except Exception as e:
        st.error(f"❌ Error executing query: {str(e)}")
        return pd.DataFrame()


def show_error_summary(db):
    """显示错误分组统计"""
    try:
        # 查询有错误的记录
        df = execute_query_to_dataframe(db, """
            SELECT error_baggage, error_passport, error_name, error_visa, error_other
            FROM hbpr_full_records
            WHERE is_validated = 1 AND is_valid = 0 AND error_count > 0
        """)
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
        # 查询有错误的记录
        df = execute_query_to_dataframe(db, """
            SELECT hbnb_number, name, error_count, error_baggage, error_passport, error_name, error_visa, error_other, validated_at
            FROM hbpr_full_records
            WHERE is_validated = 1 AND is_valid = 0 AND error_count > 0
            ORDER BY validated_at DESC, hbnb_number
        """)
        if df.empty:
            # This is a bit redundant since show_error_summary already shows a message,
            # but it is helpful if the user has a filter applied.
            # st.info("ℹ️ No error messages found. All processed records are valid!")
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


def show_info_tab():
    """Show the Info tab with error display only (no buttons)"""
    st.subheader("ℹ️ Processing Information")

    if not is_db_available():
        st.warning("⚠️ Please select a database from the sidebar to begin.")
        return

    try:
        db = get_hbpr_database_client()
        if not db:
            st.error("❌ Database connection is not available.")
            return

        # Show error summary and error messages without buttons
        show_error_summary(db)
        show_error_messages(db)

    except Exception as e:
        st.error(f"❌ Error accessing database: {str(e)}")
