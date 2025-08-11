#!/usr/bin/env python3
"""
Command analysis page for airline command processing
"""

import streamlit as st
import pandas as pd
import os
import traceback
import io
import re
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
    
    # Initialize command processor
    selected_db = st.session_state.get('selected_database', None)
    
    if not selected_db:
        st.error("❌ No database selected")
        return
    
    processor = CommandProcessor(selected_db)
    
    # 定义标签页选项
    tab_options = ["📥 Import Commands", "✒️ Add/Edit Data", "📊 View Data", "🗃️ Statistics"]
    
    # 初始化默认选择（如果还没有设置）
    if "command_tab_selector" not in st.session_state:
        st.session_state.command_tab_selector = tab_options[0]
    
    # 处理程序化标签页切换
    if hasattr(st.session_state, 'command_analysis_tab'):
        target_tab = st.session_state.command_analysis_tab
        if target_tab in tab_options:
            st.session_state.command_tab_selector = target_tab
        del st.session_state.command_analysis_tab
    
    # 使用radio按钮来控制标签页
    selected_tab = st.radio(
        label="Navigation tabs",
        options=tab_options,
        horizontal=True,
        key="command_tab_selector",
        label_visibility="collapsed"
    )
    st.markdown("---")
    
    # 根据选择的标签页显示相应内容
    if selected_tab == "📥 Import Commands":
        # 切换到此标签页时重置通用确认标志
        if st.session_state.get('current_command_tab') != 'import':
            st.session_state.confirm_clear = False
            st.session_state.current_command_tab = 'import'
        show_import_commands(processor)
    elif selected_tab == "✒️ Add/Edit Data":
        # 切换到此标签页时重置通用确认标志
        if st.session_state.get('current_command_tab') != 'edit':
            st.session_state.confirm_clear = False
            st.session_state.current_command_tab = 'edit'
        show_edit_data(processor)
    elif selected_tab == "📊 View Data":
        # 切换到此标签页时重置通用确认标志
        if st.session_state.get('current_command_tab') != 'view':
            st.session_state.confirm_clear = False
            st.session_state.current_command_tab = 'view'
        show_view_data(processor)
    elif selected_tab == "🗃️ Statistics":
        # 切换到此标签页时重置通用确认标志（不影响专用的commands确认）
        if st.session_state.get('current_command_tab') != 'statistics':
            st.session_state.confirm_clear = False
            st.session_state.current_command_tab = 'statistics'
        show_command_settings(processor)


def show_import_commands(processor: CommandProcessor):
    """Show command import interface"""
    st.subheader("📥 Import Commands from Text File")
    # Show current flight info if available
    if not processor.flight_info:
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
        if st.button("🔄 Parse and Analyze", use_container_width=True):
            not_match_dataframe = parse_commands_from_file(processor, file_path)
    with col_2:
        if st.button("💾 Store Commands", use_container_width=True, type="primary"):
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
            # Edit form
            with st.form("edit_command_form"):
                # 编辑完整的原始输入（包括命令行和内容）
                # 直接使用数据库中存储的原始内容
                current_content = record.get('content', '')
                
                # 直接使用存储的内容，如果为空则回退到重构
                if current_content:
                    full_raw_input = current_content
                else:
                    # 回退：从command_full重构（用于向后兼容旧数据）
                    current_command_full = record.get('command_full', '')
                    full_raw_input = f">{current_command_full}"
                
                edited_raw_input = st.text_area(
                    "完整原始输入（包括命令行和内容）:",
                    value=full_raw_input,
                    height=375,
                    key="edit_raw_input",
                    help="包括命令行（以>开头）和后续内容。如果修改命令行，将创建新记录。"
                )
                
                # 提交按钮
                col1, col2 = st.columns([1, 1])
                with col1:
                    if st.form_submit_button("💾 保存更改", use_container_width=True):
                        save_edited_data(processor, selected_command, edited_raw_input)
                with col2:
                    if st.form_submit_button("🗑️ 删除记录", use_container_width=True, type="secondary"):
                        delete_command_record(processor, selected_command)
        else:
            st.warning("⚠️ No record found for selected command")
    
    except Exception as e:
        st.error(f"❌ Error in edit interface: {e}")
        st.text(traceback.format_exc())


def save_edited_data(processor: CommandProcessor, original_command_full: str, edited_raw_input: str):
    """Save edited command data with special character handling"""
    try:
        if not processor.db_file:
            st.error("❌ No database file specified")
            return
        
        # Step 1: 处理特殊字符替换（类似于 validate_full_hbpr_record）
        corrected_input = apply_character_corrections(edited_raw_input)
        
        # Step 2: 解析编辑后的输入以提取命令行和内容
        lines = corrected_input.split('\n')
        if not lines:
            st.error("❌ 输入为空")
            return
        
        # 找到命令行（包含命令模式的行，如 SY:, PD:, SE: 等）
        command_line = None
        
        for line in lines:
            stripped_line = line.strip()
            # 使用与 _parse_command_line 相同的逻辑检测命令
            # 检查是否包含命令模式 [A-Z]{2,4}:
            if re.search(r'[A-Z]{2,4}:', stripped_line):
                command_line = stripped_line
                break
        
        if not command_line:
            st.error("❌ 未找到有效的命令行（应包含命令模式如 SY:, PD:, SE: 等）")
            return
        
        # Step 3: 解析新的命令行
        new_command_info = processor._parse_command_line(command_line)
        if not new_command_info:
            st.error("❌ 无法解析命令行格式")
            return
        
        new_command_full = new_command_info['command_full']
        
        # Step 4: 验证航班信息
        if not processor.validate_flight_info(new_command_info['flight_number'], new_command_info['flight_date']):
            st.warning("⚠️ 警告：新命令的航班信息与数据库不匹配")
        
        # Step 5: 确定是更新还是创建新记录
        conn = sqlite3.connect(processor.db_file)
        
        if new_command_full == original_command_full:
            # 命令行未更改，更新现有记录
            conn.execute(
                "UPDATE commands SET content = ?, updated_at = CURRENT_TIMESTAMP WHERE command_full = ?",
                (corrected_input, original_command_full)  # 存储完整的原始输入（经过字符修正）
            )
            st.success("✅ 记录已更新！")
        else:
            # 命令行已更改，创建新记录并可选删除旧记录
            # 检查新命令是否已存在
            cursor = conn.execute("SELECT id FROM commands WHERE command_full = ?", (new_command_full,))
            existing = cursor.fetchone()
            
            if existing:
                st.error(f"❌ 命令 '{new_command_full}' 已存在。请选择不同的命令。")
                conn.close()
                return
            
            # 创建新记录
            conn.execute("""
                INSERT INTO commands (command_full, command_type, flight_number, flight_date, content, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """, (
                new_command_full,
                new_command_info['command_type'],
                new_command_info['flight_number'], 
                new_command_info['flight_date'],
                corrected_input  # 存储完整的原始输入（经过字符修正）
            ))
            
            # 询问是否删除旧记录
            st.success(f"✅ 已创建新记录: {new_command_full}")
            st.info(f"💡 原记录 '{original_command_full}' 仍然存在。如需删除，请使用删除按钮。")
        
        conn.commit()
        conn.close()
        st.rerun()
    
    except Exception as e:
        st.error(f"❌ Error saving changes: {e}")
        import traceback
        st.text(traceback.format_exc())


def delete_command_record(processor: CommandProcessor, command_full: str):
    """Delete a command record"""
    try:
        if not processor.db_file:
            st.error("❌ No database file specified")
            return
        
        conn = sqlite3.connect(processor.db_file)
        cursor = conn.execute("DELETE FROM commands WHERE command_full = ?", (command_full,))
        
        if cursor.rowcount > 0:
            st.success(f"✅ 已删除记录: {command_full}")
        else:
            st.warning(f"⚠️ 未找到记录: {command_full}")
        
        conn.commit()
        conn.close()
        st.rerun()
    
    except Exception as e:
        st.error(f"❌ Error deleting record: {e}")


def apply_character_corrections(raw_input: str) -> str:
    """
    Apply character corrections similar to validate_full_hbpr_record
    Handles special characters before command prefixes
    """
    corrected_input = raw_input
    
    # 处理命令行开头的特殊字符（类似于HBPR记录处理）
    # 查找并替换DLE字符(ASCII 16, \x10)
    if re.search(r'\x10[A-Z]{2,4}:', corrected_input):
        corrected_input = re.sub(r'\x10([A-Z]{2,4}:)', r'>\1', corrected_input)
        st.info("ℹ️ 检测到DLE字符 - 已自动替换为'>'")
    
    # 查找并替换DEL字符(ASCII 127, \x7f)  
    elif re.search(r'\x7f[A-Z]{2,4}:', corrected_input):
        corrected_input = re.sub(r'\x7f([A-Z]{2,4}:)', r'>\1', corrected_input)
        st.info("ℹ️ 检测到DEL字符 - 已自动替换为'>'")
    
    # 处理其他控制字符
    elif re.search(r'[\x00-\x1f\x7f][A-Z]{2,4}:', corrected_input):
        corrected_input = re.sub(r'[\x00-\x1f\x7f]([A-Z]{2,4}:)', r'>\1', corrected_input)
        st.info("ℹ️ 检测到控制字符 - 已自动替换为'>'")
    
    # 处理可见的"del"文本
    elif re.search(r'del[A-Z]{2,4}:', corrected_input, re.IGNORECASE):
        corrected_input = re.sub(r'del([A-Z]{2,4}:)', r'>\1', corrected_input, flags=re.IGNORECASE)
        st.info("ℹ️ 检测到'del'文本 - 已自动替换为'>'")
    
    # 处理没有前缀的命令行（只在明确需要时添加>前缀）
    # 只有当行严格以命令模式开始且没有其他前缀字符时才添加>
    elif re.search(r'^[A-Z]{2,4}:\s*[A-Z0-9]', corrected_input, re.MULTILINE):
        corrected_input = re.sub(r'^([A-Z]{2,4}:)', r'>\1', corrected_input, flags=re.MULTILINE)
        st.info("ℹ️ 检测到无前缀命令 - 已自动添加'>'前缀")
    
    return corrected_input


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
            if st.session_state.get('confirm_clear_commands', False):
                try:
                    if processor.db_file:
                        conn = sqlite3.connect(processor.db_file)
                        conn.execute("DELETE FROM commands")
                        conn.commit()
                        conn.close()
                        st.success("✅ All command data cleared!")
                        st.session_state.confirm_clear_commands = False
                        # 清除数据后清理文件
                        cleanup_command_files()
                        st.rerun()
                    else:
                        st.error("❌ No database file specified")
                except Exception as e:
                    st.error(f"❌ Error clearing data: {e}")
                    st.session_state.confirm_clear_commands = False
            else:
                st.session_state.confirm_clear_commands = True
                st.warning("⚠️ Click again to confirm deletion of all command data")
                st.rerun()
    
    # 显示确认状态和取消选项
    if st.session_state.get('confirm_clear_commands', False):
        st.error("🚨 Deletion confirmation pending - click 'Clear All Command Data' again to proceed")
        if st.button("❌ Cancel Deletion", use_container_width=True, key="cancel_clear"):
            st.session_state.confirm_clear_commands = False
            st.info("✅ Deletion cancelled")
            st.rerun()
    
    with col2:
        if st.button("📊 Refresh Statistics", use_container_width=True):
            st.rerun()
