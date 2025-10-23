#!/usr/bin/env python3
"""
Command analysis page for airline command processing
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


def cleanup_command_files():
    """清理命令分析页面创建的文件"""
    command_files = ["uploaded_commands.txt"]
    for file_path in command_files:
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
            except Exception:
                pass


def show_command_analysis():
    """Display command analysis page"""
    st.markdown("<h3>📋 Other Commands Analysis</h3>", unsafe_allow_html=True)
    
    if not is_db_available():
        st.warning("⚠️ Please select a database from the sidebar to begin.")
        return
    
    try:
        db_connection = get_hbpr_database_client().get_connection()
        processor = CommandProcessor(db_connection)
    except Exception as e:
        st.error(f"❌ Failed to initialize Command Processor: {e}")
        st.text(traceback.format_exc())
        return

    tab_options = ["✒️ Add/Edit Commands", "📥 Import Commands", "📊 View Data", "📅 Timeline", "🗃️ Maintain"]
    
    tab1, tab2, tab3, tab4, tab5 = st.tabs(tab_options)

    with tab1:
        show_edit_data(processor)
    with tab2:
        show_import_commands(processor)
    with tab3:
        show_view_data(processor)
    with tab4:
        show_timeline_view(processor)
    with tab5:
        show_command_settings(processor)


def show_import_commands(processor: CommandProcessor):
    """Show command import interface"""
    st.subheader("📥 Import Commands from Text File")
    if not processor.flight_info:
        st.warning("⚠️ No flight information found in selected database")
    
    cleanup_command_files()
    uploaded_file = st.file_uploader(
        "Choose command text file:",
        type=['txt'],
        help="Upload your command text file (e.g., sample_commands.txt)"
    )
    
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

    if 'non_matching_commands_df' in st.session_state:
        with st.expander("📋 Non-Matching Commands", expanded=True):
            st.dataframe(st.session_state.non_matching_commands_df, use_container_width=True)


def parse_commands_from_file(processor: CommandProcessor, file_path: str):
    """Parse commands from uploaded file"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        with st.spinner("Parsing commands..."):
            commands = processor.parse_commands_from_text(content)
        
        matching_commands, non_matching_commands = [], []
        for cmd in commands:
            if processor.validate_flight_info(cmd['flight_number'], cmd['flight_date']):
                matching_commands.append(cmd)
            else:
                non_matching_commands.append(cmd)

        st.session_state.matching_commands = matching_commands
        st.session_state.non_matching_commands_df = pd.DataFrame(non_matching_commands)
        
        st.success(f"✅ Parsed {len(commands)} commands. Found {len(matching_commands)} matching flight info.")
        
    except Exception as e:
        st.error(f"❌ Error parsing commands: {e}")
        st.text(traceback.format_exc())


def show_timeline_view(processor: CommandProcessor):
    """Show command timeline view"""
    st.subheader("📅 Command Timeline View")
    try:
        commands_data = processor.get_all_commands_data()
        if not commands_data:
            st.info("ℹ️ No command data found.")
            return
        
        command_options = [cmd['command_full'] for cmd in commands_data]
        selected_command = st.selectbox("Select Command to View Timeline:", command_options)
        
        if selected_command:
            show_command_timeline(processor, selected_command)
            
    except Exception as e:
        st.error(f"❌ Error in timeline view: {e}")
        st.text(traceback.format_exc())


def show_command_timeline(processor: CommandProcessor, command_full: str):
    """Show timeline for a specific command"""
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
                    st.text_area("Content", version_data['content'], height=200, disabled=True, key=f"content_v{version_data['version']}")

    except Exception as e:
        st.error(f"❌ Error showing timeline: {e}")


def restore_command_version(processor: CommandProcessor, command_full: str, version_num: int):
    """Restore a specific version of a command"""
    try:
        processor.restore_version(command_full, version_num)
        trigger_auto_save()
        st.success(f"✅ Version {version_num} restored successfully!")
        st.rerun()
    except Exception as e:
        st.error(f"❌ Error restoring version: {e}")


def show_view_data(processor: CommandProcessor):
    """Show command data viewing interface"""
    st.subheader("📊 View Command Data")
    try:
        commands_data = processor.get_all_commands_data()
        if not commands_data:
            st.info("ℹ️ No command data found.")
            return

        df = pd.DataFrame(commands_data)
        st.dataframe(df, use_container_width=True, height=400)

    except Exception as e:
        st.error(f"❌ Error viewing data: {e}")


def show_manual_command_input(processor: CommandProcessor, create_table_if_needed: bool = False):
    """显示手动命令输入界面"""
    st.markdown("### Manually Add New Command")
    if not processor.flight_info:
        st.warning("⚠️ No flight information found in selected database")
        return

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
    """保存手动输入的命令，支持版本控制"""
    try:
        command_info = processor.parse_single_command(raw_input)
        if not command_info:
            st.error("❌ Could not parse a valid command from the input.")
            return

        stats = processor.store_commands([command_info])
        if stats.get('new', 0) > 0 or stats.get('updated', 0) > 0:
            st.success(f"✅ Command '{command_info['command_full']}' saved successfully.")
            trigger_auto_save()
            st.rerun()
        else:
            st.error("❌ Failed to save command.")
    except Exception as e:
        st.error(f"❌ Error saving command: {e}")


def show_edit_data(processor: CommandProcessor):
    """Show command data editing interface"""
    st.subheader("✏️ Edit Command Data")
    try:
        commands_data = processor.get_all_commands_data()
        if not commands_data:
            st.info("ℹ️ No command data found. You can manually add commands below.")
            show_manual_command_input(processor, create_table_if_needed=True)
            return

        df = pd.DataFrame(commands_data)
        command_options = df['command_full'].tolist()
        selected_command = st.selectbox("Select Command to Edit:", command_options)
        
        record = df[df['command_full'] == selected_command].iloc[0]
        
        with st.form("edit_command_form"):
            edited_raw_input = st.text_area("Full command content:", value=record.get('content', ''), height=375)
            
            col1, col2 = st.columns(2)
            with col1:
                if st.form_submit_button("💾 Save Changes", use_container_width=True):
                    save_edited_data(processor, selected_command, edited_raw_input)
            with col2:
                if st.form_submit_button("🗑️ Delete Record", use_container_width=True, type="secondary"):
                    delete_command_record(processor, selected_command)

    except Exception as e:
        st.error(f"❌ Error in edit interface: {e}")


def save_edited_data(processor: CommandProcessor, original_command_full: str, edited_raw_input: str):
    """Save edited command data with versioning support"""
    try:
        new_command_info = processor.parse_single_command(edited_raw_input)
        if not new_command_info:
            st.error("❌ Could not parse a valid command from the edited input.")
            return
        
        if new_command_info['command_full'] != original_command_full:
            st.info("Command line was changed. Deleting old record and creating a new one.")
            processor.delete_command(original_command_full)

        processor.store_commands([new_command_info])
        trigger_auto_save()
        st.success(f"✅ Command '{new_command_info['command_full']}' saved.")
        st.rerun()
    except Exception as e:
        st.error(f"❌ Error saving changes: {e}")


def delete_command_record(processor: CommandProcessor, command_full: str):
    """Delete a command record"""
    try:
        if processor.delete_command(command_full):
            trigger_auto_save()
            st.success(f"✅ Record '{command_full}' deleted.")
            st.rerun()
        else:
            st.warning("⚠️ Record not found.")
    except Exception as e:
        st.error(f"❌ Error deleting record: {e}")


def show_command_settings(processor: CommandProcessor):
    """Show command analysis settings"""
    st.subheader("🗃️ Maintain Commands")
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🔄 Migrate to Timeline Schema", use_container_width=True, help="Adds versioning support to an old database."):
            try:
                if processor.migrate_to_timeline():
                    st.success("✅ Migration completed successfully!")
                else:
                    st.info("ℹ️ Database schema is already up to date.")
            except Exception as e:
                st.error(f"❌ Migration failed: {e}")

    with col2:
        if 'confirm_clear' not in st.session_state:
            st.session_state.confirm_clear = False
            
        if st.button("🗑️ Clear All Command Data", use_container_width=True):
            if st.session_state.confirm_clear:
                try:
                    processor.erase_commands_table()
                    trigger_auto_save()
                    st.success("✅ All command data cleared!")
                    st.session_state.confirm_clear = False
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ Error clearing data: {e}")
            else:
                st.session_state.confirm_clear = True
                st.warning("⚠️ Click again to confirm deletion.")
        
        if st.session_state.confirm_clear:
            st.error("Confirmation required. Click 'Clear All' again.")

