#!/usr/bin/env python3
"""
Export tab for Database page - Data export operations
"""

import streamlit as st
import pandas as pd
from datetime import datetime
from io import BytesIO
from ui.common import (
    get_hbpr_database_client,
    is_db_available
)


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


def export_as_origin_txt(conn) -> str:
    """导出为原始txt格式"""
    try:
        if hasattr(conn, 'cursor') and hasattr(conn.cursor(), 'execute'):
            cursor = conn.cursor()
            cursor.execute("""
                SELECT record_content
                FROM hbpr_full_records
                ORDER BY hbnb_number
            """)
            columns = [desc[0] for desc in cursor.description] if cursor.description else ['record_content']
            rows = cursor.fetchall()
            df = pd.DataFrame(rows, columns=columns) if rows else pd.DataFrame(columns=columns)
        else:
            df = pd.read_sql_query("""
                SELECT record_content
                FROM hbpr_full_records
                ORDER BY hbnb_number
            """, conn)
        
        if df.empty:
            return "No records to export."
        
        processed_records = df['record_content'].astype(str).apply(lambda x: x.replace('\\n', '\n'))
        full_text = "\n\n".join(processed_records)
        return full_text
        
    except Exception as e:
        return f"Error exporting data: {str(e)}"


def show_export_operations():
    """Show export operations tab"""
    st.subheader("📤 Export Data")

    if not is_db_available():
        st.warning("⚠️ No database loaded. Please select one from the sidebar.")
        return

    try:
        db = get_hbpr_database_client()
        if not db:
            st.error("❌ Database connection not available.")
            return
            
        df = execute_query_to_dataframe(db, """
            SELECT *
            FROM hbpr_full_records
            WHERE is_validated = 1
            ORDER BY hbnb_number
        """)
        
        if df.empty:
            st.info("ℹ️ No processed records to export.")
            return

        # 为Excel导出准备包含所有列的数据
        excel_export_df = df.fillna('')
        
        # 为CSV导出准备数据，移除'record_content'列
        csv_export_df = excel_export_df.drop(columns=['record_content'], errors='ignore')

        col1, col2, col3 = st.columns(3)
        with col1:
            # 导出CSV，使用UTF-8编码
            csv_data = csv_export_df.to_csv(index=False, encoding='utf-8-sig')
            st.download_button(
                label="📥 Download as CSV (UTF-8)",
                data=csv_data.encode('utf-8-sig'),
                file_name=f"hbpr_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv",
                use_container_width=True,
                help="CSV文件使用UTF-8编码，Excel可直接打开"
            )
        with col2:
            # 导出Excel，默认使用UTF-8
            excel_buffer = BytesIO()
            excel_export_df.to_excel(excel_buffer, index=False, engine='openpyxl')
            excel_data = excel_buffer.getvalue()
            st.download_button(
                label="📊 Download as Excel",
                data=excel_data,
                file_name=f"hbpr_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
                help="Excel文件支持UTF-8编码"
            )
        with col3:
            # 导出原始TXT，使用UTF-8编码
            conn = db.get_connection()
            origin_txt_data = export_as_origin_txt(conn)
            st.download_button(
                label="📄 Download as Orig Txt (UTF-8)",
                data=origin_txt_data.encode('utf-8'),
                file_name=f"origin_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
                mime="text/plain",
                use_container_width=True,
                help="原始文本使用UTF-8编码"
            )
        
        st.subheader("👀 Export Preview")
        st.dataframe(csv_export_df, 
                     use_container_width=True,
                     hide_index=True)
        st.info(f"📊 Total records ready for export: {len(excel_export_df)}")
        
        st.info("💡 **Note**: All exports use UTF-8 encoding. Data was cleaned during database creation.")
        
    except Exception as e:
        st.error(f"❌ Error preparing export: {str(e)}")
        st.error("💡 If the error is related to data format, try using the 'Download as Orig Txt' option.")

