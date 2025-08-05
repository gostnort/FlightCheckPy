#!/usr/bin/env python3
"""
Command analysis page for airline command processing
"""

import streamlit as st
import pandas as pd
import os
import traceback
import io
from datetime import datetime
from ui.common import apply_global_settings
from scripts.command_processor import CommandProcessor
import sqlite3


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
    apply_global_settings()
    
    # 页面加载时清理文件
    cleanup_command_files()
    
    st.header("📋 Command Analysis")
    
    # Initialize command processor
    selected_db = st.session_state.get('selected_database', None)
    
    # Debug: Show the database path being used
    if selected_db:
        st.info(f"🔍 Using database: {selected_db}")
    else:
        st.error("❌ No database selected")
    
    processor = CommandProcessor(selected_db)
    
    # Create tabs
    tab1, tab2, tab3, tab4 = st.tabs(["📥 Import Commands", "📊 View Data", "✏️ Edit Data", "🗃️ Statistics"])
    
    with tab1:
        show_import_commands(processor)
    
    with tab2:
        show_view_data(processor)
    
    with tab3:
        show_edit_data(processor)
    
    with tab4:
        show_command_settings(processor)


def show_import_commands(processor: CommandProcessor):
    """Show command import interface"""
    st.subheader("📥 Import Commands from Text File")
    # Show current flight info if available
    if processor.flight_info:
        flight_info = processor.flight_info
        st.info(f"🛫 Current Database Flight: {flight_info['flight_number']}/{flight_info['flight_date']}")
    else:
        st.warning("⚠️ No flight information found in selected database")
    
    # 清理之前的文件
    cleanup_command_files()
    
    # File upload
    uploaded_file = st.file_uploader(
        "Choose command text file:",
        type=['txt'],
        help="Upload your command text file (e.g., sample_commands.txt)"
    )
    if uploaded_file is not None:
        # Save uploaded file
        file_path = "uploaded_commands.txt"
        with open(file_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
        
        # Preview file content
        with st.expander("📖 Preview File Content (first 50 lines)"):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    lines = f.readlines()[:50]
                    preview_text = ''.join(lines)
                    st.text(preview_text)
                    if len(lines) == 50:
                        st.info("... (file continues)")
            except Exception as e:
                st.error(f"Error reading file: {e}")
    col_1, col_2, col_3 = st.columns(3)
    not_match_dataframe = None
    with col_1:
        # Process commands button
        if st.button("🔄 Parse and Analyze Commands", use_container_width=True):
            not_match_dataframe = parse_commands_from_file(processor, file_path)
    with col_2:
        if st.button("💾 Store Commands in Database", use_container_width=True, type="primary"):
            stats = processor.store_commands(st.session_state.matching_commands)
            st.success(f"✅ Stored {stats['new']} new, {stats['updated']} updated, {stats['skipped']} skipped")
            # 存储完成后清理文件
            cleanup_command_files()
    with col_3:
        if st.button("🗑️ Clear", use_container_width=True):
            processor.erase_commands_table()
            # 清除完成后清理文件
            cleanup_command_files()
    if not_match_dataframe is not None:
        with st.expander("📋 Not Match Commands", expanded=True):
            st.dataframe(not_match_dataframe, use_container_width=True)


def parse_commands_from_file(processor: CommandProcessor, file_path: str):
    """Parse commands from uploaded file"""
    try:
        # Read file content
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        with st.spinner("Parsing commands..."):
            # Parse commands
            commands = processor.parse_commands_from_text(content)
        if not commands:
            st.warning("⚠️ No commands found in the file")
            return
        # 验证航班信息
        matching_commands = []
        non_matching_commands = []
        for cmd in commands:
            if processor.validate_flight_info(cmd['flight_number'], cmd['flight_date']):
                matching_commands.append(cmd)
            else:
                non_matching_commands.append(cmd)
        # Display summary table
        st.session_state.matching_commands = matching_commands
        df_summary = pd.DataFrame(non_matching_commands)
        # 解析完成后清理文件
        cleanup_command_files()
        return df_summary
    except Exception as e:
        st.error(f"❌ Error parsing commands: {e}")
        st.text(traceback.format_exc())
        return 


def show_view_data(processor: CommandProcessor):
    """Show command data viewing interface"""
    st.subheader("📊 View Command Data")
    
    try:
        # Get all commands data
        commands_data = processor.get_all_commands_data()
        
        if not commands_data:
            st.info("ℹ️ No command data found. Import some commands first.")
            return
        
        # Convert to DataFrame
        df = pd.DataFrame(commands_data)
        
        # Basic info
        st.info(f"📈 Total records: {len(df)}")
        
        # Command type filter
        command_types = processor.get_command_types()
        
        if command_types:
            selected_commands = st.multiselect(
                "Select command types to view:",
                command_types,
                default=command_types[:5] if len(command_types) > 5 else command_types
            )
            
            # Filter data by selected command types
            if selected_commands:
                filtered_data = []
                for cmd in commands_data:
                    cmd_type = cmd.get('command_type', '')
                    if cmd_type in selected_commands:
                        filtered_data.append(cmd)
                
                if filtered_data:
                    display_df = pd.DataFrame(filtered_data)
                    
                    # Format for better display
                    if 'created_at' in display_df.columns:
                        display_df['created_at'] = pd.to_datetime(display_df['created_at']).dt.strftime('%Y-%m-%d %H:%M')
                    if 'updated_at' in display_df.columns:
                        display_df['updated_at'] = pd.to_datetime(display_df['updated_at']).dt.strftime('%Y-%m-%d %H:%M')
                    
                    st.dataframe(display_df, use_container_width=True, height=400)
                    
                    # Export options
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        if st.button("📥 Export to CSV", use_container_width=True):
                            csv = display_df.to_csv(index=False)
                            st.download_button(
                                label="Download CSV",
                                data=csv,
                                file_name="command_data.csv",
                                mime="text/csv"
                            )
                    
                    with col2:
                        if st.button("📊 Export to Excel", use_container_width=True):
                            # Create Excel file in memory
                            output = io.BytesIO()
                            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                                display_df.to_excel(writer, sheet_name='Command Data', index=False)
                            
                            output.seek(0)
                            st.download_button(
                                label="Download Excel",
                                data=output.getvalue(),
                                file_name="command_data.xlsx",
                                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                            )
                else:
                    st.warning("⚠️ No data to display with selected filters")
            else:
                st.warning("⚠️ Please select at least one command type")
        else:
            st.info("ℹ️ No command types found in database")
    
    except Exception as e:
        st.error(f"❌ Error viewing data: {e}")
        st.text(traceback.format_exc())


def show_edit_data(processor: CommandProcessor):
    """Show command data editing interface"""
    st.subheader("✏️ Edit Command Data")
    
    try:
        # Get all commands data
        commands_data = processor.get_all_commands_data()
        
        if not commands_data:
            st.info("ℹ️ No command data found. Import some commands first.")
            return
        
        # Record selection
        df = pd.DataFrame(commands_data)
        
        # Command selection
        command_options = df['command_full'].tolist()
        selected_command = st.selectbox("Select Command to Edit:", command_options)
        
        # Get record for editing
        record = df[df['command_full'] == selected_command]
        
        if not record.empty:
            record = record.iloc[0]
            
            st.write(f"**Editing command:** {selected_command}")
            
            # Edit form
            with st.form("edit_command_form"):
                st.write("**Command Content:**")
                
                current_content = record.get('content', '')
                edited_content = st.text_area(
                    "Content:",
                    value=current_content,
                    height=400,
                    key="edit_content"
                )
                
                # Submit button
                if st.form_submit_button("💾 Save Changes", use_container_width=True):
                    save_edited_data(processor, selected_command, edited_content)
        else:
            st.warning("⚠️ No record found for selected command")
    
    except Exception as e:
        st.error(f"❌ Error in edit interface: {e}")
        st.text(traceback.format_exc())


def save_edited_data(processor: CommandProcessor, command_full: str, edited_content: str):
    """Save edited command data"""
    try:
        if not processor.db_file:
            st.error("❌ No database file specified")
            return
        
        # Update database with edited data
        conn = sqlite3.connect(processor.db_file)
        conn.execute(
            "UPDATE commands SET content = ?, updated_at = CURRENT_TIMESTAMP WHERE command_full = ?",
            (edited_content, command_full)
        )
        conn.commit()
        conn.close()
        
        st.success("✅ Changes saved successfully!")
        st.rerun()
    
    except Exception as e:
        st.error(f"❌ Error saving changes: {e}")


def show_command_settings(processor: CommandProcessor):
    """Show command analysis settings"""
    # Database info
    st.write("**Database Information:**")
    if processor.flight_info:
        flight_info = processor.flight_info
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Flight ID", flight_info['flight_id'])
        with col2:
            st.metric("Flight Number", flight_info['flight_number'])
        with col3:
            st.metric("Flight Date", flight_info['flight_date'])
    else:
        st.warning("⚠️ No flight information available")
    
    # Commands database stats
    st.write("**Commands Database Statistics:**")
    try:
        commands_data = processor.get_all_commands_data()
        command_types = processor.get_command_types()
        
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Total Records", len(commands_data))
        with col2:
            st.metric("Command Types", len(command_types))
        
        if command_types:
            st.write("**Available Command Types:**")
            # Display command types in columns
            cols = st.columns(10)
            for i, cmd_type in enumerate(sorted(command_types)):
                with cols[i % 10]:
                    st.text(f"• {cmd_type}")
    
    except Exception as e:
        st.error(f"❌ Error getting statistics: {e}")
    
    # Maintenance operations
    st.markdown("---")
    st.write("**Maintenance Operations:**")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("🗑️ Clear All Command Data", use_container_width=True):
            if st.session_state.get('confirm_clear', False):
                try:
                    if processor.db_file:
                        conn = sqlite3.connect(processor.db_file)
                        conn.execute("DELETE FROM commands")
                        conn.commit()
                        conn.close()
                        st.success("✅ All command data cleared!")
                        st.session_state.confirm_clear = False
                        # 清除数据后清理文件
                        cleanup_command_files()
                        st.rerun()
                    else:
                        st.error("❌ No database file specified")
                except Exception as e:
                    st.error(f"❌ Error clearing data: {e}")
            else:
                st.session_state.confirm_clear = True
                st.warning("⚠️ Click again to confirm deletion of all command data")
    
    with col2:
        if st.button("📊 Refresh Statistics", use_container_width=True):
            st.rerun()
    
    # Reset confirmation flag if user clicks elsewhere
    if st.session_state.get('confirm_clear', False):
        st.warning("⚠️ Confirmation pending for data deletion")