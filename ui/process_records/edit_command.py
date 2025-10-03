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
    try:
        commands_data = processor.get_all_commands_data()
        if not commands_data:
            st.info("ℹ️ No command data found. You can manually add commands below.")
            show_manual_command_input(processor, create_table_if_needed=True)
            return
        # 创建DataFrame并显示选择器
        df = pd.DataFrame(commands_data)
        command_options = df['command_full'].tolist()
        
        # 使用session state来记住选择的命令（支持新命令自动选中）
        if 'selected_edit_command' not in st.session_state:
            st.session_state['selected_edit_command'] = command_options[0]
        
        # 如果选中的命令不在列表中（被删除了），选择第一个
        if st.session_state['selected_edit_command'] not in command_options:
            st.session_state['selected_edit_command'] = command_options[0]
        
        # 获取选中命令的索引
        default_index = command_options.index(st.session_state['selected_edit_command'])
        
        selected_command = st.selectbox(
            "Select a Command to Edit:", 
            command_options,
            index=default_index
        )
        
        # 更新session state
        st.session_state['selected_edit_command'] = selected_command
        
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
            # 设置session state以便重新加载后选中新命令
            st.session_state['selected_edit_command'] = command_info['command_full']
            st.success(f"✅ Command '{command_info['command_full']}' saved successfully.")
            trigger_auto_save()
            st.rerun()
        else:
            st.error("❌ Failed to save command.")
    except Exception as e:
        st.error(f"❌ Error saving command: {e}")


def save_edited_data(processor: CommandProcessor, original_command_full: str, edited_raw_input: str):
    """保存编辑的命令数据，支持版本控制"""
    try:
        # 解析编辑后的命令
        new_command_info = processor.parse_single_command(edited_raw_input)
        if not new_command_info:
            st.error("❌ Could not parse a valid command from the edited input.")
            return
        
        new_command_full = new_command_info['command_full']
        
        # 情况1: 命令行发生变化 → 创建新命令（保留旧命令）
        if new_command_full != original_command_full:
            stats = processor.store_commands([new_command_info])
            trigger_auto_save()
            # 设置session state以便重新加载后选中新命令
            st.session_state['selected_edit_command'] = new_command_full
            st.success(f"✅ New command '{new_command_full}' created. Original command '{original_command_full}' kept.")
            # 重新加载以刷新selectbox
            st.rerun()
            return
        
        # 情况2: 命令行相同 → 让store_commands自动处理版本控制
        # - 如果内容不同，会创建新版本 (updated)
        # - 如果内容相同，只更新时间戳 (skipped)
        stats = processor.store_commands([new_command_info])
        trigger_auto_save()
        
        if stats.get('updated', 0) > 0:
            st.success(f"✅ New version created for command '{new_command_full}'.")
        elif stats.get('skipped', 0) > 0:
            st.info("ℹ️ No changes detected. Content is identical to current version.")
        else:
            st.success(f"✅ Command '{new_command_full}' saved.")
        
        st.rerun()
        
    except Exception as e:
        st.error(f"❌ Error saving changes: {e}")
        st.text(traceback.format_exc())


def delete_command_record(processor: CommandProcessor, command_full: str):
    """删除命令的最新版本"""
    try:
        # 首先检查该命令有多少个版本
        timeline_data = processor.get_command_timeline(command_full)
        if not timeline_data:
            st.warning("⚠️ Record not found.")
            return
        
        version_count = len(timeline_data)
        
        # 删除最新版本
        if processor.delete_latest_version(command_full):
            trigger_auto_save()
            if version_count > 1:
                st.success("✅ Latest version deleted. Previous version is now active.")
            else:
                st.success(f"✅ Command '{command_full}' deleted (was the only version).")
            st.rerun()
        else:
            st.warning("⚠️ Failed to delete record.")
    except Exception as e:
        st.error(f"❌ Error deleting record: {e}")
        st.text(traceback.format_exc())
