#!/usr/bin/env python3
"""
Edit a Command tab for Process Records page Edit individual commands
"""

import streamlit as st
import pandas as pd
import traceback
from ui.common import (
    is_db_available,
    get_hbpr_database_client,
    trigger_auto_save
)
from scripts.command_processor import CommandProcessor


def show_edit_command_tab():
    """显示编辑命令标签页"""
    st.subheader("📋 Edit a Command")
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
    # 显示编辑命令界面
    show_edit_data(processor)


def show_edit_data(processor: CommandProcessor):
    """显示命令数据编辑界面"""
    st.subheader("✏️ Edit Command Data")
    try:
        commands_data = processor.get_all_commands_data()
        if not commands_data:
            st.info("ℹ️ No command data found. You can manually add commands below.")
            show_manual_command_input(processor, create_table_if_needed=True)
            return
        # 创建DataFrame并显示选择器
        df = pd.DataFrame(commands_data)
        command_options = df['command_full'].tolist()
        selected_command = st.selectbox("Select Command to Edit:", command_options)
        # 获取选中的记录
        record = df[df['command_full'] == selected_command].iloc[0]
        # 显示编辑表单
        with st.form("edit_command_form"):
            edited_raw_input = st.text_area("Full command content:", value=record.get('content', ''), height=375)
            # 按钮列
            col1, col2 = st.columns(2)
            with col1:
                if st.form_submit_button("💾 Save Changes", use_container_width=True):
                    save_edited_data(processor, selected_command, edited_raw_input)
            with col2:
                if st.form_submit_button("🗑️ Delete Record", use_container_width=True, type="secondary"):
                    delete_command_record(processor, selected_command)
    except Exception as e:
        st.error(f"❌ Error in edit interface: {e}")


def show_manual_command_input(processor: CommandProcessor, create_table_if_needed: bool = False):
    """显示手动命令输入界面"""
    st.markdown("### Manually Add New Command")
    if not processor.flight_info:
        st.warning("⚠️ No flight information found in selected database")
        return
    # 获取航班信息
    flight_info = processor.flight_info
    with st.form("manual_command_form"):
        raw_input = st.text_area(
            "Full command content:",
            height=300,
            placeholder=f">SY:{flight_info['flight_number']}/{flight_info['flight_date']}\n..."
        )
        if st.form_submit_button("💾 Add Command", use_container_width=True, type="primary"):
            if raw_input.strip():
                save_manual_command(processor, raw_input.strip(), create_table_if_needed)
            else:
                st.error("❌ Command content cannot be empty.")


def save_manual_command(processor: CommandProcessor, raw_input: str, create_table_if_needed: bool = False):
    """保存手动输入的命令支持版本控制"""
    try:
        command_info = processor.parse_single_command(raw_input)
        if not command_info:
            st.error("❌ Could not parse a valid command from the input.")
            return
        # 存储命令
        stats = processor.store_commands([command_info])
        if stats.get('new', 0) > 0 or stats.get('updated', 0) > 0:
            st.success(f"✅ Command '{command_info['command_full']}' saved successfully.")
            trigger_auto_save()
            st.rerun()
        else:
            st.error("❌ Failed to save command.")
    except Exception as e:
        st.error(f"❌ Error saving command: {e}")


def save_edited_data(processor: CommandProcessor, original_command_full: str, edited_raw_input: str):
    """保存编辑的命令数据支持版本控制"""
    try:
        new_command_info = processor.parse_single_command(edited_raw_input)
        if not new_command_info:
            st.error("❌ Could not parse a valid command from the edited input.")
            return
        # 如果命令行发生变化删除旧记录并创建新记录
        if new_command_info['command_full'] != original_command_full:
            st.info("Command line was changed. Deleting old record and creating a new one.")
            processor.delete_command(original_command_full)
        # 存储命令
        processor.store_commands([new_command_info])
        trigger_auto_save()
        st.success(f"✅ Command '{new_command_info['command_full']}' saved.")
        st.rerun()
    except Exception as e:
        st.error(f"❌ Error saving changes: {e}")


def delete_command_record(processor: CommandProcessor, command_full: str):
    """删除命令记录"""
    try:
        if processor.delete_command(command_full):
            trigger_auto_save()
            st.success(f"✅ Record '{command_full}' deleted.")
            st.rerun()
        else:
            st.warning("⚠️ Record not found.")
    except Exception as e:
        st.error(f"❌ Error deleting record: {e}")
