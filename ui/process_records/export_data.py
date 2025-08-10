#!/usr/bin/env python3
"""
Export Data functionality for HBPR UI - Data export interface
"""

import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime
from io import BytesIO
from scripts.hbpr_info_processor import HbprDatabase
from ui.common import get_current_database


def show_export_data():
    """显示导出选项"""
    try:
        # 获取当前选中的数据库
        selected_db_file = get_current_database()
        
        if not selected_db_file:
            st.error("❌ No database selected.")
            st.info("💡 Please select a database from the sidebar or build one first in the Database Management page.")
            return
        
        db = HbprDatabase(selected_db_file)
        
        st.subheader("📤 Export Data")
        
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
        
        col1, col2, col3 = st.columns(3)
        
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
        
        with col3:
            # 原始文本导出
            origin_txt_data = export_as_origin_txt(db.db_file)
            st.download_button(
                label="📄 Download as Orig Txt",
                data=origin_txt_data,
                file_name=f"origin_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
                mime="text/plain",
                use_container_width=True
            )
        
        # 显示导出预览
        st.subheader("👀 Export Preview")
        st.dataframe(df.head(10), use_container_width=True)
        st.info(f"📊 Total records ready for export: {len(df)}")
    except Exception as e:
        st.error(f"❌ Error preparing export: {str(e)}")


def export_as_origin_txt(db_file: str) -> str:
    """
    导出原始文本格式，包含full_record表的record_content和commands表的command_type、command_full
    Args:
        db_file (str): 数据库文件路径   
    Returns:
        str: 格式化的原始文本内容
    """
    content_parts = []
    try:
        conn = sqlite3.connect(db_file)
        
        # 导出full_record表的record_content
        cursor = conn.execute("""
            SELECT hbnb_number, record_content 
            FROM hbpr_full_records 
            ORDER BY hbnb_number
        """)
        full_records = cursor.fetchall()
        if full_records:
            for hbnb_number, record_content in full_records:
                content_parts.append(record_content)
                content_parts.append("")
        # 导出commands表的command_type和command_full
        cursor = conn.execute("""
            SELECT command_full, content
            FROM commands 
            ORDER BY command_full, content
        """)
        
        commands = cursor.fetchall()
        if commands:
            for command_full, content in commands:
                content_parts.append(f">{command_full}\n{content}")
                content_parts.append("")
        
        conn.close()
        
        return "\n".join(content_parts)
        
    except Exception as e:
        return f"Error exporting data: {str(e)}"
