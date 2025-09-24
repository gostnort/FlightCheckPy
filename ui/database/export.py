#!/usr/bin/env python3
"""
Export tab for Database page - Data export operations
"""

import streamlit as st
import pandas as pd
import re
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


def clean_text_for_export(text: str) -> str:
    """
    清理文本数据，移除或替换无法在Excel/CSV中使用的字符
    """
    if not text or not isinstance(text, str):
        return ""
    
    cleaned = re.sub(r'[\x00-\x1f\x7f]', ' ', text)
    cleaned = re.sub(r'[^\x20-\x7e\n\r\t]', ' ', cleaned)
    cleaned = re.sub(r'[^\w\s\-\.\,\:\;\+\=\*\/\(\)\[\]\{\}\<\>\|\&\^\%\$\#\@\!\?]', ' ', cleaned)
    cleaned = re.sub(r' +', ' ', cleaned)
    cleaned = re.sub(r'\n\s*\n', '\n', cleaned)
    cleaned = cleaned.strip()
    
    if not cleaned:
        cleaned = "[Data cleaned - contains non-exportable characters]"
    
    return cleaned


def safe_export_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """
    安全地准备DataFrame用于导出，处理所有可能有问题的字段
    """
    if df.empty:
        return df
    
    export_df = df.copy()
    
    text_columns = ['pnr', 'name', 'seat', 'class', 'destination', 'ff', 'pspt_name', 
                   'pspt_exp_date', 'ckin_msg', 'asvc_msg', 'inbound_flight', 
                   'outbound_flight', 'properties', 'tkne', 'error_baggage', 
                   'error_passport', 'error_name', 'error_visa', 'error_other']
    
    for col in text_columns:
        if col in export_df.columns:
            export_df[col] = export_df[col].fillna('').astype(str).apply(clean_text_for_export)
    
    for col in export_df.columns:
        if export_df[col].dtype == 'object':
            export_df[col] = export_df[col].fillna('').astype(str).apply(
                lambda x: clean_text_for_export(x) if isinstance(x, str) else x
            )
    
    return export_df


def export_as_origin_txt(conn) -> str:
    """导出为原始txt格式"""
    try:
        if hasattr(conn, 'cursor') and hasattr(conn.cursor(), 'execute'):
            cursor = conn.cursor()
            cursor.execute("""
                SELECT record_content
                FROM hbpr_full_records
                WHERE is_validated = 1
                ORDER BY hbnb_number
            """)
            columns = [desc[0] for desc in cursor.description] if cursor.description else ['record_content']
            rows = cursor.fetchall()
            df = pd.DataFrame(rows, columns=columns) if rows else pd.DataFrame(columns=columns)
        else:
            df = pd.read_sql_query("""
                SELECT record_content
                FROM hbpr_full_records
                WHERE is_validated = 1
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
            SELECT hbnb_number, created_at, is_validated, is_valid, boarding_number,
                   pnr, name, seat, class, destination, bag_piece, bag_weight,
                   bag_allowance, ff, pspt_name, pspt_exp_date, ckin_msg, asvc_msg,
                   expc_piece, expc_weight, asvc_piece, fba_piece, ifba_piece,
                   has_infant, flyer_benefit, is_ca_flyer, inbound_flight,
                   outbound_flight, properties, tkne, error_count, error_baggage,
                   error_passport, error_name, error_visa, error_other, validated_at,
                   bol_duplicate
            FROM hbpr_full_records
            WHERE is_validated = 1
            ORDER BY hbnb_number
        """)
        
        if df.empty:
            st.info("ℹ️ No processed records to export.")
            return
        
        export_df = safe_export_dataframe(df)
        
        col1, col2, col3 = st.columns(3)
        with col1:
            csv_data = export_df.to_csv(index=False)
            st.download_button(
                label="📥 Download as CSV",
                data=csv_data,
                file_name=f"hbpr_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv",
                use_container_width=True
            )
        with col2:
            excel_buffer = BytesIO()
            export_df.to_excel(excel_buffer, index=False, engine='openpyxl')
            excel_data = excel_buffer.getvalue()
            st.download_button(
                label="📊 Download as Excel",
                data=excel_data,
                file_name=f"hbpr_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )
        with col3:
            conn = db.get_connection()
            origin_txt_data = export_as_origin_txt(conn)
            st.download_button(
                label="📄 Download as Orig Txt",
                data=origin_txt_data,
                file_name=f"origin_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
                mime="text/plain",
                use_container_width=True
            )
        
        st.subheader("👀 Export Preview")
        st.dataframe(export_df, 
                     use_container_width=True,
                     hide_index=True)
        st.info(f"📊 Total records ready for export: {len(export_df)}")
        
        st.info("💡 **Note**: CSV and Excel exports exclude the raw record content field to prevent errors. Use 'Download as Orig Txt' to get the original data.")
        
    except Exception as e:
        st.error(f"❌ Error preparing export: {str(e)}")
        st.error("💡 If the error is related to data format, try using the 'Download as Orig Txt' option.")

