#!/usr/bin/env python3
"""
Add Commands tab for Process Records page Import commands from files
"""

import streamlit as st
import pandas as pd
import os
import traceback
from ui.common import (
    is_db_available,
    get_hbpr_database_client,
    trigger_auto_save
)
from scripts.command_processor import CommandProcessor


def show_add_commands_tab():
    """显示添加命令标签页"""
    st.subheader("📝 Add Commands")
    # 检查数据库是否可用
    if not is_db_available():
        st.warning("⚠️ Please select a database from the sidebar to begin.")
        return
    # 初始化CommandProcessor
    try:
        db_connection = get_hbpr_database_client().get_connection()
        processor = CommandProcessor(db_connection)
    except Exception as e:
        st.error(f"❌ Failed to initialize Command Processor: {e}")
        st.text(traceback.format_exc())
        return
    # 显示导入命令界面
    show_import_commands(processor)


def cleanup_command_files():
    """清理命令分析页面创建的文件"""
    command_files = ["uploaded_commands.txt"]
    for file_path in command_files:
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
            except Exception:
                pass


def show_import_commands(processor: CommandProcessor):
    """显示命令导入界面"""
    st.subheader("📥 Import Commands from Text File")
    if not processor.flight_info:
        st.warning("⚠️ No flight information found in selected database")
    # 清理之前的命令文件
    cleanup_command_files()
    uploaded_file = st.file_uploader(
        "Choose command text file:",
        type=['txt'],
        help="Upload your command text file (e.g., sample_commands.txt)"
    )
    # 如果上传了文件显示预览
    if uploaded_file is not None:
        file_path = "uploaded_commands.txt"
        with open(file_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
        with st.expander("📖 Preview File Content (first 50 lines)"):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    lines = f.readlines()[:50]
                    st.text(''.join(lines))
            except Exception as e:
                st.error(f"Error reading file: {e}")
    # 操作按钮
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("🔄 Parse and Analyze", use_container_width=True):
            parse_commands_from_file(processor, "uploaded_commands.txt")
    with col2:
        if st.button("💾 Store Commands", use_container_width=True, type="primary"):
            if 'matching_commands' in st.session_state and st.session_state.matching_commands:
                stats = processor.store_commands(st.session_state.matching_commands)
                st.success(f"✅ Stored {stats['new']} new, {stats['updated']} updated, {stats['skipped']} skipped")
                trigger_auto_save()
                cleanup_command_files()
            else:
                st.warning("⚠️ No matching commands to store. Please parse a file first.")
    with col3:
        if st.button("🗑️ Clear", use_container_width=True):
            processor.erase_commands_table()
            cleanup_command_files()
            st.rerun()
    # 显示不匹配的命令
    if 'non_matching_commands_df' in st.session_state:
        with st.expander("📋 Non-Matching Commands", expanded=True):
            st.dataframe(st.session_state.non_matching_commands_df, use_container_width=True)


def parse_commands_from_file(processor: CommandProcessor, file_path: str):
    """从上传的文件中解析命令"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        with st.spinner("Parsing commands..."):
            commands = processor.parse_commands_from_text(content)
        # 分离匹配和不匹配的命令
        matching_commands, non_matching_commands = [], []
        for cmd in commands:
            if processor.validate_flight_info(cmd['flight_number'], cmd['flight_date']):
                matching_commands.append(cmd)
            else:
                non_matching_commands.append(cmd)
        # 保存到session state
        st.session_state.matching_commands = matching_commands
        st.session_state.non_matching_commands_df = pd.DataFrame(non_matching_commands)
        st.success(f"✅ Parsed {len(commands)} commands. Found {len(matching_commands)} matching flight info.")
    except Exception as e:
        st.error(f"❌ Error parsing commands: {e}")
        st.text(traceback.format_exc())
