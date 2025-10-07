#!/usr/bin/env python3
"""
Excel处理页面 - 导入Excel文件并根据TKNE和CKIN CCRD生成输出文件
"""

import streamlit as st
import pandas as pd
import os
from pathlib import Path
from ui.common import get_hbpr_database_client, is_db_available
from scripts.excel_processor import (
    process_excel_file as core_process_excel_file,
    generate_output_excel as core_generate_output_excel,
    calculate_cash_and_total_amounts,
    format_date_ddmmmyy
)
from scripts.api_encoder.gemma3_client import generate_mood_description


def show_excel_processor():
    """显示Excel处理页面"""
    st.markdown("<h3>📊 Excel Processor</h3>", unsafe_allow_html=True)
    
    if not is_db_available():
        st.warning("⚠️ Please select a database from the sidebar to begin.")
        return

    # Additional CSS to ensure bottom content is visible
    st.markdown("""
    <style>
    /* Ensure Excel processor page content is fully visible */
    .main .block-container {
        padding-bottom: 6rem !important;
        margin-bottom: 2rem !important;
    }
    /* Ensure download buttons and success messages are visible */
    .stSuccess, .stDownloadButton {
        margin-bottom: 1rem !important;
    }
    /* Make sure the entire page content is scrollable */
    .stApp {
        height: auto !important;
        min-height: 100vh !important;
        overflow-y: auto !important;
    }
    </style>
    """, unsafe_allow_html=True)
    # 标题与调试开关同一行
    col_uploader, col_debug = st.columns([3, 1])
    with col_uploader:
        st.subheader("📁 Upload Excel File")
    with col_debug:
        debug_on = st.toggle("Debug", value=False, help="Enable to see detailed processing logs for each row.")
    uploaded_file = st.file_uploader(
            "Select the Excel file to process",
            type=['xlsx', 'xls'],
            help="Upload an Excel file containing TKNE data for processing"
        )
    if uploaded_file is not None:
        try:
            # 正确读取Excel文件，第二行为表头（header=1），支持XLS和XLSX格式
            file_ext = uploaded_file.name.lower().split('.')[-1]
            if file_ext == 'xls':
                # 对于XLS格式，明确指定引擎
                try:
                    df_input = pd.read_excel(uploaded_file, header=1, engine='xlrd')
                except ImportError:
                    st.error("❌ xlrd package is missing, cannot read XLS files. Please install: pip install xlrd")
                    return
                except Exception as e:
                    st.error(f"❌ Failed to read XLS file: {str(e)}")
                    return
            else:
                # 对于XLSX格式，使用默认引擎
                try:
                    df_input = pd.read_excel(uploaded_file, header=1, engine='openpyxl')
                except Exception as e:
                    st.error(f"❌ Failed to read XLSX file: {str(e)}")
                    return
            # 列名与位置的严格校验在核心处理函数内执行
            # 处理按钮
            if st.button("🚀 Start Processing", type="primary", use_container_width=True):
                with st.spinner("Processing Excel file..."):
                    try:
                        # Get the database client and pass it to the core processor
                        db_client = get_hbpr_database_client()
                        if not db_client:
                            st.error("Database connection not available. Please ensure a database is selected.")
                            return

                        result_df, unprocessed_records, debug_logs = core_process_excel_file(db_client, df_input, debug=debug_on)
                    except ValueError as ve:
                        st.error(f"❌ Data validation failed: {str(ve)}")
                        return
                    except Exception as e:
                        st.error(f"❌ An error occurred while processing the file: {str(e)}")
                        return
                if result_df is not None:
                    # Debug开关：打开时显示每行输入与输出详情
                    if debug_on and debug_logs:
                        st.subheader("🛠️ Debug Details (Input and Output per Row)")
                        for entry in debug_logs:
                            with st.expander(f"Row {entry.get('row_index', '?')}"):
                                st.write("Input:")
                                st.json(entry.get('input', {}))
                                st.write("Output:")
                                st.json(entry.get('output', {}))
                    # 显示处理结果
                    st.subheader("✅ Processing Results")
                    st.dataframe(result_df, use_container_width=True)
                    # 显示未处理的记录（错误信息）
                    if unprocessed_records:
                        st.subheader("⚠️ Unprocessed CKIN CCRD Records")
                        for record in unprocessed_records:
                            st.warning(f"Passenger: {record['name']}, TKNE: {record['tkne']}, CKIN CCRD: {record['ckin_ccrd']}")
                    # 生成输出文件
                    # 使用全局航班信息（由核心处理在首次行设置）
                    # 计算现金和总金额
                    cash_total, total_amount = calculate_cash_and_total_amounts(df_input)
                    # 获取当前用户名并生成心情描述
                    username = st.session_state.get('username', 'unknown')
                    mood_description = "平静"  # 默认值
                    if cash_total > 0 and total_amount > 0 and username != 'unknown':
                        try:
                            mood_description = generate_mood_description(cash_total, total_amount, username)
                        except Exception as e:
                            st.warning(f"Error generating mood description: {e}")
                            mood_description = "复杂"
                    # 生成包含心情描述的文件名，处理重名情况
                    # 重新获取全局变量，确保获取到最新值
                    from scripts.excel_processor import FLIGHT_NUMBER, FLIGHT_DATE
                    fn = FLIGHT_NUMBER or 'FLIGHT'
                    fd = format_date_ddmmmyy(FLIGHT_DATE) if FLIGHT_DATE else 'DATE'
                    # 生成文件名，如果重名则添加数字后缀
                    base_mood = mood_description
                    attempt = 0
                    while attempt < 100:  # 最多尝试100次
                        if attempt == 0:
                            filename = f"{fn}_{fd}_EMD_{mood_description}.xlsx"
                        else:
                            filename = f"{fn}_{fd}_EMD_{base_mood}{attempt}.xlsx"
                        
                        output_file = get_output_file_path(filename)
                        # 检查文件是否已存在
                        if not Path(output_file).exists():
                            break  # 文件不存在，可以使用这个文件名
                        attempt += 1
                    try:
                        core_generate_output_excel(result_df, unprocessed_records, output_file, cash_total)
                    except Exception as e:
                        st.error(f"❌ Failed to generate output file: {str(e)}")
                        return
                    # 显示文件保存位置和提供下载链接
                    col_download, col_info = st.columns([1, 2])
                    with col_download:
                        st.subheader("📥 File Generated")
                    with col_info:
                        st.success(f"✅ File saved to: {output_file}")
                    with open(output_file, 'rb') as f:
                        st.download_button(
                            label="📥 Download",
                            data=f.read(),
                            file_name=filename,
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            use_container_width=True
                        )
        except Exception as e:
            st.error(f"❌ An error occurred while processing the file: {str(e)}")
            st.info("💡 Please check if the Excel file format is correct")


def get_output_file_path(filename: str) -> str:
    """确定输出文件的保存路径"""
    # 首先尝试用户的Downloads文件夹
    try:
        downloads_path = Path.home() / "Downloads"
        # 检查目录是否存在且可写
        if downloads_path.is_dir() and os.access(str(downloads_path), os.W_OK):
            return str(downloads_path / filename)
    except Exception:
        # 在某些环境下 Path.home() 可能会失败
        pass
    # 如果Downloads文件夹不可用，则尝试 C:\temp
    try:
        temp_dir = Path("C:/temp")
        temp_dir.mkdir(parents=True, exist_ok=True)
        output_path = temp_dir / filename
        st.info(f"📁 文件将保存至: {output_path}")
        return str(output_path)
    except Exception as e:
        # 最后的备用方案：当前工作目录
        st.warning(f"⚠️ 无法访问 Downloads 文件夹或创建 C:\\temp，将使用当前目录: {str(e)}")
        return filename
 