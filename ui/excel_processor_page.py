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
                    # 生成带时间戳的文件名（LLM响应前使用）
                    timestamp = datetime.now().strftime("%H%M%S")
                    timestamp_filename = f"{fn}_{fd}_EMD_{timestamp}.xlsx"
                    output_file = get_output_file_path(timestamp_filename)
                    # 生成Excel文件
                    try:
                        core_generate_output_excel(
                            result_df,
                            unprocessed_records,
                            output_file,
                            cash_total,
                            producer_name.strip(),
                        )
                    except Exception as e:
                        st.error(f"❌ Failed to generate output file: {str(e)}")
                        return
                    # 启动后台进程生成心情描述并重命名文件 - 总是重命名
                    username = st.session_state.get("username", "unknown")
                    # 始终启动重命名进程（测试项目）
                    process, shared_status = start_mood_rename_process(
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
                        "shared_status": shared_status,
                        "process": process,
                    }
                    # 不要立即 rerun()，让后台进程有时间完成
                    # st.rerun()  【已注释 - 改为让前端主动轮询状态】
            # 检查是否有已生成的文件（在每次渲染时检查，以便更新重命名状态）
            rename_info = st.session_state.get("excel_rename_process", {})
            if rename_info and rename_info.get("timestamp_file"):
                timestamp_file = rename_info["timestamp_file"]
                shared_status = rename_info.get("shared_status")
                # 从共享状态读取结果（无需文件I/O）
                status_data = None
                if shared_status:
                    # 检查进程是否还在运行
                    process = rename_info.get("process")
                    if process and not process.is_alive():
                        # 进程已完成，读取共享状态
                        try:
                            status_data = dict(shared_status)  # 转换为普通dict以便使用
                            # 标记为已完成，避免重复检查
                            if not rename_info.get("needs_rename_completed"):
                                st.session_state["excel_rename_process"][
                                    "needs_rename_completed"
                                ] = True
                                if status_data.get("success"):
                                    st.success("✅ 文件重命名完成！")
                                else:
                                    st.warning(
                                        f"⚠️ 重命名失败，使用原始文件名: {status_data.get('error', '未知错误')}"
                                    )
                        except Exception as e:
                            st.warning(f"⚠️ 读取共享状态失败: {str(e)}")
                    elif shared_status.get("completed"):
                        # 共享状态显示已完成，直接读取
                        try:
                            status_data = dict(shared_status)
                            if not rename_info.get("needs_rename_completed"):
                                st.session_state["excel_rename_process"][
                                    "needs_rename_completed"
                                ] = True
                                if status_data.get("success"):
                                    st.success("✅ 文件重命名完成！")
                                else:
                                    st.warning(
                                        f"⚠️ 重命名失败，使用原始文件名: {status_data.get('error', '未知错误')}"
                                    )
                        except Exception as e:
                            st.warning(f"⚠️ 读取共享状态失败: {str(e)}")
                # 根据共享状态确定输出文件（只有在状态完成时才确定文件）
                output_file = None
                final_filename = None
                # 只有在共享状态显示完成时（重命名进程已完成）才确定输出文件
                if status_data:
                    if status_data.get("success"):
                        # 重命名成功，使用状态文件中的新文件名
                        new_filepath = status_data.get("new_filepath")
                        if new_filepath and Path(new_filepath).exists():
                            output_file = new_filepath
                            final_filename = status_data.get(
                                "new_filename", Path(new_filepath).name
                            )
                        else:
                            # 状态文件说成功但文件不存在，这是错误情况
                            st.error(f"❌ 重命名后的文件不存在: {new_filepath}")
                    else:
                        # 重命名失败，使用原始时间戳文件
                        if Path(timestamp_file).exists():
                            output_file = timestamp_file
                            final_filename = Path(timestamp_file).name
                        else:
                            # 原始文件也不存在，这是错误情况
                            st.error(f"❌ 原始文件不存在: {timestamp_file}")
                else:
                    # 共享状态显示仍在处理中
                    status_placeholder = st.empty()
                    status_placeholder.info(
                        "⏳ LLM生成心情描述并重命名文件中... 请稍候"
                    )
                    # 自动刷新以检查共享状态（最多等待30秒）
                    max_wait_time = 30  # 秒
                    check_interval = 0.5  # 每0.5秒检查一次（更快响应）
                    wait_start_time = rename_info.get("wait_start_time", 0)
                    if wait_start_time == 0:
                        # 记录开始等待时间
                        st.session_state["excel_rename_process"]["wait_start_time"] = (
                            time.time()
                        )
                        # 立即触发第一次刷新
                        time.sleep(check_interval)
                        st.rerun()
                    else:
                        elapsed_time = time.time() - wait_start_time
                        if elapsed_time < max_wait_time:
                            # 等待一小段时间后自动刷新
                            time.sleep(check_interval)
                            st.rerun()
                        else:
                            # 超时，停止自动刷新
                            status_placeholder.warning(
                                "⏳ 等待超时，请手动刷新页面检查状态"
                            )
                            if (
                                "wait_start_time"
                                in st.session_state["excel_rename_process"]
                            ):
                                del st.session_state["excel_rename_process"][
                                    "wait_start_time"
                                ]
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
                # 只有在状态文件存在且文件存在时才显示下载和打印按钮
                if status_data and output_file and Path(output_file).exists():
                    col_download, col_info = st.columns([1, 2])
                    with col_download:
                        st.subheader("📥 File Generated")
                    with col_info:
                        st.success(f"✅ File saved to: {output_file}")
                    # 下载和打印按钮（只有在重命名完成且文件存在时显示）
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
                elif not status_data:
                    # 状态文件不存在，仍在等待重命名完成
                    pass  # 等待消息已在上面显示
                elif output_file is None:
                    # 状态文件存在但无法确定输出文件（错误情况已在上面显示）
                    pass
                else:
                    # 状态文件存在但文件不存在（错误情况已在上面显示）
                    pass
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
