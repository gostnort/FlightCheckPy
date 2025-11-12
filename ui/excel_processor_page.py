#!/usr/bin/env python3
"""
Excel处理页面 - 导入Excel文件并根据TKNE和CKIN CCRD生成输出文件
"""

import streamlit as st
import pandas as pd
import os
import time
from pathlib import Path
from datetime import datetime
from ui.common import get_hbpr_database_client, is_db_available
from scripts.excel_processor import (
    process_excel_file as core_process_excel_file,
    generate_output_excel as core_generate_output_excel,
    calculate_cash_and_total_amounts,
    format_date_ddmmmyy,
)
from scripts.api_encoder.mood_rename_worker import start_mood_rename_process
from scripts.excel_printer import print_excel_file


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
                    # 生成带时间戳的文件名（LLM响应前使用）
                    timestamp = datetime.now().strftime("%H%M%S")
                    timestamp_filename = f"{fn}_{fd}_EMD_{timestamp}.xlsx"
                    output_file = get_output_file_path(timestamp_filename)
                    # 生成Excel文件
                    try:
                        core_generate_output_excel(
                            result_df, unprocessed_records, output_file, cash_total
                        )
                    except Exception as e:
                        st.error(f"❌ Failed to generate output file: {str(e)}")
                        return
                    # 启动后台进程生成心情描述并重命名文件 - 总是重命名
                    username = st.session_state.get("username", "unknown")
                    # 始终启动重命名进程（测试项目）
                    start_mood_rename_process(
                        cash_total if cash_total > 0 else 100.0,
                        total_amount if total_amount > 0 else 1000.0,
                        username if username != "unknown" else "test",
                        output_file,
                        fn,
                        fd,
                    )
                    # 保存到session state以便后续检查状态
                    st.session_state["excel_rename_process"] = {
                        "timestamp_file": output_file,
                        "needs_rename": True,
                        "final_filename": timestamp_filename,
                    }
                    # 不要立即 rerun()，让后台进程有时间完成
                    # st.rerun()  【已注释 - 改为让前端主动轮询状态】
            # 检查是否有已生成的文件（在每次渲染时检查，以便更新重命名状态）
            rename_info = st.session_state.get("excel_rename_process", {})
            # 显示重命名进行中的状态 - 但不立即rerun，给后台进程时间
            if (
                rename_info
                and rename_info.get("needs_rename")
                and not rename_info.get("needs_rename_completed")
            ):
                status_placeholder = st.empty()
                status_placeholder.info("⏳ LLM生成心情描述并重命名文件中... 请稍候")
                # 等待一小段时间，让后台进程完成
                for i in range(6):  # 最多等待6秒
                    time.sleep(0.5)  # 每次只等0.5秒，让UI保持响应
                    status_placeholder.info(f"⏳ 处理中... ({i * 0.5:.1f}秒)")
                st.session_state["excel_rename_process"]["needs_rename_completed"] = (
                    True
                )
                status_placeholder.success("✅ 文件已重命名！")
            if rename_info and rename_info.get("timestamp_file"):
                timestamp_file = rename_info["timestamp_file"]
                final_filename = rename_info.get(
                    "final_filename", Path(timestamp_file).name
                )
                output_file = timestamp_file
                # 检查是否有重命名后的文件
                file_dir = Path(timestamp_file).parent
                # 查找匹配的 EMD 文件（除了时间戳文件本身）
                for file in file_dir.glob("*.xlsx"):
                    if str(file) != timestamp_file and "EMD" in file.name:
                        output_file = str(file)
                        final_filename = file.name
                        break
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
                # 显示文件保存位置和提供下载链接
                col_download, col_info = st.columns([1, 2])
                with col_download:
                    st.subheader("📥 File Generated")
                with col_info:
                    st.success(f"✅ File saved to: {output_file}")
                # 下载和打印按钮（始终显示，只要文件存在）
                if Path(output_file).exists():
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
                            success, message, html_component, metadata = print_excel_file(
                                output_file
                            )
                            if success:
                                if html_component:
                                    st.components.v1.html(html_component, height=0)
                                st.success(message)
                                if metadata:
                                    label_map = {
                                        "flight_number": "航班号",
                                        "flight_date": "航班日期",
                                        "record_count": "记录数量",
                                        "cash_total": "现金合计",
                                        "total_amount": "总金额",
                                        "unprocessed_records": "未处理记录",
                                    }
                                    st.subheader("📋 打印元数据")
                                    for key in [
                                        "flight_number",
                                        "flight_date",
                                        "record_count",
                                        "cash_total",
                                        "total_amount",
                                    ]:
                                        if key in metadata and metadata[key] not in [
                                            None,
                                            "",
                                        ]:
                                            value = metadata[key]
                                            if isinstance(value, float):
                                                value = f"{value:,.2f}"
                                            st.markdown(
                                                f"- **{label_map.get(key, key)}**：{value}"
                                            )
                                    if metadata.get("unprocessed_records"):
                                        st.markdown("**未处理记录：**")
                                        for item in metadata["unprocessed_records"]:
                                            st.markdown(f"  - {item}")
                            else:
                                st.error(message)
                else:
                    st.error(f"❌ 文件不存在: {output_file}")
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
        st.warning(
            f"⚠️ 无法访问 Downloads 文件夹或创建 C:\\temp，将使用当前目录: {str(e)}"
        )
        return filename
