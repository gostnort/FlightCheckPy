#!/usr/bin/env python3
"""
Export Data functionality for HBPR UI - Data export interface
"""

import streamlit as st
import pandas as pd
import sqlite3
import re
from datetime import datetime
from io import BytesIO
from scripts.hbpr_info_processor import HbprDatabase
from ui.common import get_current_database


def clean_text_for_export(text: str) -> str:
    """
    清理文本数据，移除或替换无法在Excel/CSV中使用的字符
    Args:
        text (str): 原始文本
    Returns:
        str: 清理后的文本
    """
    if not text or not isinstance(text, str):
        return ""
    
    # 移除或替换控制字符（ASCII 0-31, 127）
    cleaned = re.sub(r'[\x00-\x1f\x7f]', ' ', text)
    
    # 移除或替换其他问题字符
    # 替换常见的二进制/hex字符
    cleaned = re.sub(r'[^\x20-\x7e\n\r\t]', ' ', cleaned)
    
    # 特别处理可能包含二进制数据的字段
    # 移除或替换可能导致Excel问题的字符序列
    cleaned = re.sub(r'[^\w\s\-\.\,\:\;\+\=\*\/\(\)\[\]\{\}\<\>\|\&\^\%\$\#\@\!\?]', ' ', cleaned)
    
    # 移除多余的空白字符
    cleaned = re.sub(r' +', ' ', cleaned)
    cleaned = re.sub(r'\n\s*\n', '\n', cleaned)
    
    # 确保文本以可打印字符结尾
    cleaned = cleaned.strip()
    
    # 如果清理后文本为空，返回一个占位符
    if not cleaned:
        cleaned = "[数据已清理 - 包含无法导出的字符]"
    
    return cleaned


def safe_export_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """
    安全地准备DataFrame用于导出，处理所有可能有问题的字段
    Args:
        df (pd.DataFrame): 原始DataFrame
    Returns:
        pd.DataFrame: 清理后的DataFrame
    """
    if df.empty:
        return df
    
    # 创建DataFrame的副本以避免修改原始数据
    export_df = df.copy()
    
    # 定义需要清理的文本字段
    text_columns = ['pnr', 'name', 'seat', 'class', 'destination', 'ff', 'pspt_name', 
                   'pspt_exp_date', 'ckin_msg', 'asvc_msg', 'inbound_flight', 
                   'outbound_flight', 'properties', 'tkne', 'error_baggage', 
                   'error_passport', 'error_name', 'error_visa', 'error_other']
    
    # 清理所有文本字段
    for col in text_columns:
        if col in export_df.columns:
            export_df[col] = export_df[col].fillna('').astype(str).apply(clean_text_for_export)
    
    # 处理其他可能有问题的字段
    for col in export_df.columns:
        if export_df[col].dtype == 'object':
            # 检查是否包含非ASCII字符
            export_df[col] = export_df[col].fillna('').astype(str).apply(
                lambda x: clean_text_for_export(x) if isinstance(x, str) else x
            )
    
    return export_df


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
        
        # 获取所有已处理的记录，但排除可能有问题的record_content字段
        df = pd.read_sql_query("""
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
        """, conn)
        conn.close()
        
        if df.empty:
            st.info("ℹ️ No processed records to export.")
            return
        
        # 使用安全的导出函数清理数据
        export_df = safe_export_dataframe(df)
        
        col1, col2, col3 = st.columns(3)
        with col1:
            # CSV导出
            csv_data = export_df.to_csv(index=False)
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
        st.dataframe(export_df.head(10), use_container_width=True)
        st.info(f"📊 Total records ready for export: {len(export_df)}")
        
        # 添加说明信息
        st.info("💡 **注意**: CSV和Excel导出已排除原始记录内容字段，以避免导出错误。原始数据可通过'Download as Orig Txt'获取。")
        
    except Exception as e:
        st.error(f"❌ Error preparing export: {str(e)}")
        st.error("💡 如果错误与数据格式相关，请尝试使用'Download as Orig Txt'选项导出原始数据。")


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
                # 清理文本内容
                cleaned_content = clean_text_for_export(record_content)
                content_parts.append(cleaned_content)
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
                # 清理命令内容
                cleaned_content = clean_text_for_export(content)
                content_parts.append(f">{command_full}\n{cleaned_content}")
                content_parts.append("")
        conn.close()
        return "\n".join(content_parts)
    except Exception as e:
        return f"Error exporting data: {str(e)}"


def test_data_cleaning():
    """
    测试数据清理功能
    """
    # 测试用例：包含控制字符和特殊字符的文本
    test_cases = [
        ">HBPR: CA984/15AUG25*LAX,67 PNR RL MZBX",
        "Normal text with \x00\x01\x02 control characters",
        "Text with \x7f DEL character",
        "Mixed content: >HBPR: CA984/15AUG25*LAX,67 PNR RL MZBX",
        "Text with \x1f\x1e\x1d control chars",
        ">HBPR: CA984/15AUG25*LAX,67 PNR RL MZBXG7. 1. WANG/ZHIQIANG BN3",
    ]
    
    print("Testing data cleaning function:")
    print("=" * 50)
    
    for i, test_case in enumerate(test_cases, 1):
        cleaned = clean_text_for_export(test_case)
        print(f"Test {i}:")
        print(f"  Original: {repr(test_case)}")
        print(f"  Cleaned:  {repr(cleaned)}")
        print(f"  Length:   {len(cleaned)}")
        print("-" * 30)
    
    return "Data cleaning test completed"


if __name__ == "__main__":
    # 如果直接运行此文件，执行测试
    test_data_cleaning()

