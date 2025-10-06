#!/usr/bin/env python3
"""
Timeline tab for Process Records page - Timeline view with HBPR and Commands history
"""

import streamlit as st
from ui.common import get_hbpr_database_client
from scripts.command_processor import CommandProcessor


def show_timeline_tab():
    """Show Timeline tab with radio buttons to switch between HBPR and Commands history"""
    st.subheader("📅 Timeline")
    # Radio buttons to switch between HBPR and Commands
    timeline_type = st.radio(
        "Select Timeline Type:",
        ["HBPR Records", "Commands"],
        horizontal=True,
        help="Choose which type of timeline to view"
    )
    if timeline_type == "HBPR Records":
        show_hbpr_timeline()
    else:
        show_commands_timeline()


def show_hbpr_timeline():
    """Show HBPR records timeline (duplicate records)"""
    st.markdown("**HBPR Records Timeline**")
    try:
        db = get_hbpr_database_client()
        if not db:
            st.error("Database connection not available.")
            return
        # Get duplicate records for timeline
        duplicate_hbnbs = db.get_all_duplicate_hbnbs()
        if not duplicate_hbnbs:
            st.info("ℹ️ No duplicate HBPR records found.")
            return
        selected_hbnb = st.selectbox(
            "Select HBNB to view timeline:",
            duplicate_hbnbs,
            help="Select an HBNB number to view its duplicate record timeline"
        )
        if selected_hbnb:
            # Get original and duplicate records
            current_record = db.get_hbpr_record(selected_hbnb)
            duplicate_records = db.get_duplicate_records(selected_hbnb)
            st.markdown(f"### 📅 Timeline for HBNB: **{selected_hbnb}**")
            # Display original record first
            with st.expander("Current Record", expanded=True):
                st.text_area("Content", current_record, height=200, disabled=True, key=f"original_{selected_hbnb}")
            # Display duplicate records
            for dup in duplicate_records:
                is_latest = dup.get('is_latest', False)
                with st.expander(f"Duplicate Record (ID: {dup['id']}) {'(Latest)' if is_latest else ''}", expanded=is_latest):
                    record_content = db.get_duplicate_record_content(dup['id'])
                    st.text_area(f"Content (Created: {dup['created_at']})", record_content, height=200, disabled=True, key=f"dup_{dup['id']}")
    except Exception as e:
        st.error(f"❌ Error loading HBPR timeline: {str(e)}")


def show_commands_timeline():
    """Show commands timeline with auto-load first command"""
    try:
        db = get_hbpr_database_client()
        if not db:
            st.error("Database connection not available.")
            return
        # 创建CommandProcessor实例
        db_connection = db.get_connection()
        processor = CommandProcessor(db_connection)
        # 获取所有命令
        commands_data = processor.get_all_commands_data()
        if not commands_data:
            st.info("ℹ️ No command data found.")
            return
        # 显示命令选择器
        command_options = [cmd['command_full'] for cmd in commands_data]
        # 使用session state记住选择，或默认选择第一个
        if 'selected_timeline_command' not in st.session_state:
            st.session_state['selected_timeline_command'] = command_options[0]
        # 确保选择的命令仍然存在
        if st.session_state['selected_timeline_command'] not in command_options:
            st.session_state['selected_timeline_command'] = command_options[0]
        selected_command = st.selectbox(
            "Select Command to View Timeline:",
            command_options,
            index=command_options.index(st.session_state['selected_timeline_command'])
        )
        # 更新session state
        st.session_state['selected_timeline_command'] = selected_command
        # 显示时间线
        if selected_command:
            show_command_timeline_detail(processor, selected_command)
    except Exception as e:
        st.error(f"❌ Error loading commands timeline: {str(e)}")


def show_command_timeline_detail(processor: CommandProcessor, command_full: str):
    """显示单个命令的时间线详情"""
    try:
        timeline_data = processor.get_command_timeline(command_full)
        if not timeline_data:
            st.warning("⚠️ No timeline data found for this command")
            return
        st.markdown(f"### 📅 Timeline for: **{command_full}**")
        for version_data in timeline_data:
            is_latest = version_data['is_latest']
            with st.expander(f"Version {version_data['version']} {'(Latest)' if is_latest else ''}", expanded=is_latest):
                col1, col2 = st.columns([1, 3])
                with col1:
                    st.metric("Version", version_data['version'])
                    st.caption(f"Created: {version_data['created_at'][:19]}")
                    if not is_latest:
                        if st.button(f"🔄 Restore v{version_data['version']}", key=f"restore_{version_data['id']}"):
                            restore_command_version(processor, command_full, version_data['version'])
                with col2:
                    st.text_area("Content", version_data['content'], height=200, disabled=True, key=f"content_v{version_data['version']}_{version_data['id']}")
    except Exception as e:
        st.error(f"❌ Error showing timeline: {e}")


def restore_command_version(processor: CommandProcessor, command_full: str, version_num: int):
    """恢复指定版本的命令"""
    from ui.common import trigger_auto_save
    try:
        processor.restore_version(command_full, version_num)
        trigger_auto_save()
        st.success(f"✅ Version {version_num} restored successfully!")
        st.rerun()
    except Exception as e:
        st.error(f"❌ Error restoring version: {e}")

