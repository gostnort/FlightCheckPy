#!/usr/bin/env python3
"""
Excel处理页面 - 导入Excel文件并根据TKNE和CKIN CCRD生成输出文件
"""

import streamlit as st
import pandas as pd
import os
import time
import hashlib
import random
from pathlib import Path
from datetime import datetime
from typing import Tuple
from ui.common import get_hbpr_database_client, is_db_available
from scripts.excel_processor import (
    process_excel_file as core_process_excel_file,
    generate_output_excel as core_generate_output_excel,
    calculate_cash_and_total_amounts,
    format_date_ddmmmyy,
)
from scripts.excel_printer import print_excel_file


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
        st.warning(
            f"⚠️ 无法访问 Downloads 文件夹或创建 C:\\temp，将使用当前目录: {str(e)}"
        )
        return filename


def generate_unique_hashed_filename(fn: str, fd: str) -> Tuple[str, str]:
    """
    生成随时间哈希的唯一EMD文件名及保存路径。
    随时间哈希，不重名就好，万一重名再试一次。
    Returns:
        (filename, full_output_path)
    """
    while True:
        # 基于当前纳秒时间戳和随机数生成哈希
        time_seed = f"{time.time_ns()}_{random.randint(1000, 9999)}"
        hash_suffix = hashlib.sha256(time_seed.encode("utf-8")).hexdigest()[:8]
        filename = f"{fn}_{fd}_EMD_{hash_suffix}.xlsx"
        output_path = get_output_file_path(filename)
        if not Path(output_path).exists():
            return filename, output_path
        time.sleep(0.001)


def show_excel_processor():
    """显示Excel处理页面"""
    st.markdown("<h3>📊 Excel Processor</h3>", unsafe_allow_html=True)
    if not is_db_available():
        st.warning("⚠️ Please select a database from the sidebar to begin.")
        return
    # Additional CSS to ensure bottom content is visible
    st.markdown(
        """
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
    """,
        unsafe_allow_html=True,
    )
    # 标题与调试开关同一行
    col_uploader, col_debug = st.columns([3, 1])
    with col_uploader:
        st.subheader("📁 Upload Excel File")
    with col_debug:
        debug_on = st.toggle(
            "Debug",
            value=st.session_state.get("debug_on", False),
            help="Enable to see detailed processing logs for each row.",
        )
        # 将debug状态保存到session_state，以便在rerun后恢复
        st.session_state["debug_on"] = debug_on
    producer_name = st.text_input(
        "👤 制作人姓名",
        value=st.session_state.get("producer_name", ""),
        placeholder="请输入将写入C13的名字",
        help="该名字将会写入输出模板SUM工作表的C13位置，用于标记制作人。",
    )
    st.session_state["producer_name"] = producer_name
    uploaded_file = st.file_uploader(
        "Select the Excel file to process",
        type=["xlsx", "xls"],
        help="Upload an Excel file containing TKNE data for processing",
    )
    if uploaded_file is not None:
        try:
            # 正确读取Excel文件，第二行为表头（header=1），支持XLS和XLSX格式
            file_ext = uploaded_file.name.lower().split(".")[-1]
            if file_ext == "xls":
                # 对于XLS格式，明确指定引擎
                try:
                    df_input = pd.read_excel(uploaded_file, header=1, engine="xlrd")
                except ImportError:
                    st.error(
                        "❌ xlrd package is missing, cannot read XLS files. Please install: pip install xlrd"
                    )
                    return
                except Exception as e:
                    st.error(f"❌ Failed to read XLS file: {str(e)}")
                    return
            else:
                # 对于XLSX格式，使用默认引擎
                try:
                    df_input = pd.read_excel(uploaded_file, header=1, engine="openpyxl")
                except Exception as e:
                    st.error(f"❌ Failed to read XLSX file: {str(e)}")
                    return
            # 列名与位置的严格校验在核心处理函数内执行
            # 处理按钮
            if st.button(
                "🚀 Start Processing", type="primary", use_container_width=True
            ):
                if not producer_name or not producer_name.strip():
                    st.error("❌ 请输入制作人姓名后再开始处理。")
                    return
                with st.spinner("Processing Excel file..."):
                    try:
                        # Get the database client and pass it to the core processor
                        db_client = get_hbpr_database_client()
                        if not db_client:
                            st.error(
                                "Database connection not available. Please ensure a database is selected."
                            )
                            return
                        result_df, unprocessed_records, debug_logs = (
                            core_process_excel_file(db_client, df_input, debug=debug_on)
                        )
                        # 保存debug_logs到session_state以便重新渲染时使用
                        st.session_state["excel_debug_logs"] = debug_logs
                    except ValueError as ve:
                        st.error(f"❌ Data validation failed: {str(ve)}")
                        return
                    except Exception as e:
                        st.error(
                            f"❌ An error occurred while processing the file: {str(e)}"
                        )
                        return
                if result_df is not None:
                    # Debug开关：打开时显示每行输入与输出详情
                    debug_logs = st.session_state.get("excel_debug_logs", [])
                    if debug_on and debug_logs:
                        st.subheader("🛠️ Debug Details (Input and Output per Row)")
                        for entry in debug_logs:
                            with st.expander(f"Row {entry.get('row_index', '?')}"):
                                st.write("Input:")
                                st.json(entry.get("input", {}))
                                st.write("Output:")
                                st.json(entry.get("output", {}))
                    # 显示处理结果
                    st.subheader("✅ Processing Results")
                    st.dataframe(result_df, use_container_width=True)
                    # 显示未处理的记录（错误信息）
                    if unprocessed_records:
                        st.subheader("⚠️ Unprocessed CKIN CCRD Records")
                        for record in unprocessed_records:
                            st.warning(
                                f"Passenger: {record['name']}, TKNE: {record['tkne']}, CKIN CCRD: {record['ckin_ccrd']}"
                            )
                    # 生成输出文件
                    # 使用全局航班信息（由核心处理在首次行设置）
                    # 计算现金和总金额
                    cash_total, total_amount = calculate_cash_and_total_amounts(
                        df_input
                    )
                    # 重新获取全局变量，确保获取到最新值
                    from scripts.excel_processor import FLIGHT_NUMBER, FLIGHT_DATE

                    fn = FLIGHT_NUMBER or "FLIGHT"
                    fd = format_date_ddmmmyy(FLIGHT_DATE) if FLIGHT_DATE else "DATE"
                    # 使用随时间哈希生成唯一文件名（不重名就好，万一重名再试一次）
                    output_filename, output_file = generate_unique_hashed_filename(
                        fn, fd
                    )
                    # 生成Excel文件
                    try:
                        core_generate_output_excel(
                            result_df,
                            unprocessed_records,
                            output_file,
                            cash_total,
                            producer_name.strip(),
                        )
                        st.session_state["excel_generated_file"] = {
                            "output_file": output_file,
                            "filename": output_filename,
                        }
                    except Exception as e:
                        st.error(f"❌ Failed to generate output file: {str(e)}")
                        return
            # 检查是否有已生成的文件（每次渲染时检查并展示下载与打印）
            generated_info = st.session_state.get("excel_generated_file", {})
            if generated_info and generated_info.get("output_file"):
                output_file = generated_info["output_file"]
                final_filename = generated_info.get("filename", Path(output_file).name)
                # 显示Debug详情（如果启用）
                debug_logs = st.session_state.get("excel_debug_logs", [])
                if debug_on and debug_logs:
                    st.subheader("🛠️ Debug Details (Input and Output per Row)")
                    for entry in debug_logs:
                        with st.expander(f"Row {entry.get('row_index', '?')}"):
                            st.write("Input:")
                            st.json(entry.get("input", {}))
                            st.write("Output:")
                            st.json(entry.get("output", {}))
                if Path(output_file).exists():
                    col_download, col_info = st.columns([1, 2])
                    with col_download:
                        st.subheader("📥 File Generated")
                    with col_info:
                        st.success(f"✅ File saved to: {output_file}")
                    # 下载和打印按钮
                    col_download_btn, col_print_btn = st.columns(2)
                    with col_download_btn:
                        with open(output_file, "rb") as f:
                            st.download_button(
                                label="📥 Download",
                                data=f.read(),
                                file_name=final_filename,
                                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                use_container_width=True,
                            )
                    with col_print_btn:
                        if st.button(
                            "🖨️ Print", use_container_width=True, key="print_button"
                        ):
                            success, message, html_component, _ = print_excel_file(
                                output_file
                            )
                            if success:
                                if html_component:
                                    st.components.v1.html(html_component, height=0)
                                st.success(message)
                            else:
                                st.error(message)
                else:
                    st.error(f"❌ 生成的文件不存在: {output_file}")
        except Exception as e:
            st.error(f"❌ An error occurred while processing the file: {str(e)}")
            st.info("💡 Please check if the Excel file format is correct")
