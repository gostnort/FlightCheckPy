#!/usr/bin/env python3
"""
Excel处理页面 - 导入Excel文件并根据TKNE和CKIN CCRD生成输出文件
"""

import streamlit as st
import pandas as pd
import os
from ui.common import apply_global_settings, get_current_database
from scripts.hbpr_info_processor import HbprDatabase
from scripts.excel_processor import (
    process_excel_file as core_process_excel_file,
    generate_output_excel as core_generate_output_excel,
)


def show_excel_processor():
    """显示Excel处理页面"""
    apply_global_settings()
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
    # 检查数据库状态
    selected_db_file = get_current_database()
    if not selected_db_file:
        st.error("❌ 未选择数据库!")
        st.info("💡 请从侧边栏选择数据库或先创建数据库。")
        return
    db = HbprDatabase(selected_db_file)
    # 标题与调试开关同一行
    col_uploader, col_debug = st.columns([3, 1])
    with col_uploader:
        st.subheader("📁 上传Excel文件")
    with col_debug:
        debug_on = st.toggle("Debug", value=False, help="开启后显示每一行的输入与输出详情")
    uploaded_file = st.file_uploader(
            "选择要处理的Excel文件",
            type=['xlsx', 'xls'],
            help="上传包含TKNE数据的Excel文件进行处理"
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
                    st.error("❌ 缺少xlrd包，无法读取XLS文件。请安装：pip install xlrd")
                    return
                except Exception as e:
                    st.error(f"❌ 读取XLS文件失败: {str(e)}")
                    return
            else:
                # 对于XLSX格式，使用默认引擎
                try:
                    df_input = pd.read_excel(uploaded_file, header=1, engine='openpyxl')
                except Exception as e:
                    st.error(f"❌ 读取XLSX文件失败: {str(e)}")
                    return
            # 列名与位置的严格校验在核心处理函数内执行
            # 处理按钮
            if st.button("🚀 开始处理", type="primary", use_container_width=True):
                with st.spinner("正在处理Excel文件..."):
                    try:
                        result_df, unprocessed_records, debug_logs = core_process_excel_file(df_input, db, debug=debug_on)
                    except ValueError as ve:
                        st.error(f"❌ 数据校验失败: {str(ve)}")
                        return
                    except Exception as e:
                        st.error(f"❌ 处理文件时发生错误: {str(e)}")
                        return
                if result_df is not None:
                    # Debug开关：打开时显示每行输入与输出详情
                    if debug_on and debug_logs:
                        st.subheader("🛠️ Debug 明细（每行输入与输出）")
                        for entry in debug_logs:
                            with st.expander(f"第 {entry.get('row_index', '?')} 行"):
                                st.write("输入：")
                                st.json(entry.get('input', {}))
                                st.write("输出：")
                                st.json(entry.get('output', {}))
                    # 显示处理结果
                    st.subheader("✅ 处理结果")
                    st.dataframe(result_df, use_container_width=True)
                    # 显示未处理的记录（错误信息）
                    if unprocessed_records:
                        st.subheader("⚠️ 未处理的CKIN CCRD记录")
                        for record in unprocessed_records:
                            st.warning(f"乘客: {record['name']}, TKNE: {record['tkne']}, CKIN CCRD: {record['ckin_ccrd']}")
                    # 生成输出文件
                    from datetime import datetime
                    timestamp = datetime.now().strftime("%H%M%S")
                    base_name = os.path.splitext(uploaded_file.name)[0]
                    # 使用全局航班信息（由核心处理在首次行设置）
                    from scripts.excel_processor import FLIGHT_NUMBER, FLIGHT_DATE, format_date_ddmmmyy
                    fn = FLIGHT_NUMBER or 'FLIGHT'
                    fd = format_date_ddmmmyy(FLIGHT_DATE) if FLIGHT_DATE else 'DATE'
                    filename = f"{fn}_{fd}_EMD{timestamp}.xlsx"
                    output_file = get_output_file_path(filename)
                    try:
                        core_generate_output_excel(result_df, unprocessed_records, output_file)
                    except Exception as e:
                        st.error(f"❌ 生成输出文件失败: {str(e)}")
                        return
                    # 显示文件保存位置和提供下载链接
                    col_download, col_info = st.columns([1, 2])
                    with col_download:
                        st.subheader("📥 文件已生成")
                    with col_info:
                        st.success(f"✅ 文件已保存到: {output_file}")
                    with open(output_file, 'rb') as f:
                        st.download_button(
                            label="📥 下载",
                            data=f.read(),
                            file_name=f"processed_{base_name}.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            use_container_width=True
                        )
        except Exception as e:
            st.error(f"❌ 处理文件时发生错误: {str(e)}")
            st.info("💡 请检查Excel文件格式是否正确")


def get_output_file_path(filename: str) -> str:
    """确定输出文件的保存路径"""
    # 首先尝试用户的Downloads文件夹
    downloads_path = os.path.expanduser("~\Downloads")
    if os.path.exists(downloads_path) and os.access(downloads_path, os.W_OK):
        output_path = os.path.join(downloads_path, filename)
        return output_path
    # 如果Downloads不存在或无法访问，尝试创建C:\temp
    try:
        temp_dir = "C:\\temp"
        if not os.path.exists(temp_dir):
            os.makedirs(temp_dir)
            st.info(f"📁 创建临时目录: {temp_dir}")
        output_path = os.path.join(temp_dir, filename)
        st.info(f"📁 文件将保存到: {temp_dir}\\{filename}")
        return output_path
    except Exception as e:
        # 最后的备用方案：当前工作目录
        st.warning(f"⚠️ 无法访问Downloads或创建C:\\temp，使用当前目录: {str(e)}")
        return filename
 