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
from ui.db_management import apply_global_settings, db_manager
from scripts.command_processor import CommandProcessor
from ui.db_management import enable_auto_save_on_change


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
    if not db_manager.is_available():
        st.error("❌ No database selected")
        return
    
    try:
        db_connection = db_manager.get_database().get_connection()
        processor = CommandProcessor(db_connection)
    except Exception as e:
        st.error(f"❌ Failed to initialize Command Processor: {e}")
        st.text(traceback.format_exc())
        return

    # 定义标签页选项
    tab_options = ["✒️ Add/Edit Commands", "📥 Import Commands", "📊 View Data", "📅 Timeline", "🗃️ Maintain"]

    # 处理程序化标签页切换
    if hasattr(st.session_state, 'command_analysis_tab'):
        target_tab = st.session_state.command_analysis_tab
        # Remap old tab name for compatibility
        if target_tab == "✒️ Add/Edit Data":
            target_tab = "✒️ Add/Edit Commands"
        try:
            default_index = tab_options.index(target_tab)
        except ValueError:
            default_index = 0
        del st.session_state.command_analysis_tab
    else:
        default_index = 0

    # 使用tabs来控制页面
    tab1, tab2, tab3, tab4, tab5 = st.tabs(tab_options)

    with tab1:
        # 切换到此标签页时重置通用确认标志
        if st.session_state.get('current_command_tab') != 'edit':
            st.session_state.confirm_clear = False
            st.session_state.current_command_tab = 'edit'
        show_edit_data(processor)
    with tab2:
        # 切换到此标签页时重置通用确认标志
        if st.session_state.get('current_command_tab') != 'import':
            st.session_state.confirm_clear = False
            st.session_state.current_command_tab = 'import'
        show_import_commands(processor)
    with tab3:
        # 切换到此标签页时重置通用确认标志
        if st.session_state.get('current_command_tab') != 'view':
            st.session_state.confirm_clear = False
            st.session_state.current_command_tab = 'view'
        show_view_data(processor)
    with tab4:
        # 切换到此标签页时重置通用确认标志
        if st.session_state.get('current_command_tab') != 'timeline':
            st.session_state.confirm_clear = False
            st.session_state.current_command_tab = 'timeline'
        show_timeline_view(processor)
    with tab5:
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
            enable_auto_save_on_change()  # 触发自动保存
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


def show_timeline_view(processor: CommandProcessor):
    """Show command timeline view"""
    st.subheader("📅 Command Timeline View")
    try:
        # Get all commands data (latest versions only for selection)
        commands_data = processor.get_all_commands_data()
        if not commands_data:
            st.info("ℹ️ No command data found. Import some commands first.")
            return
        # Command selection
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
        # Get timeline data for the selected command
        timeline_data = processor.get_command_timeline(command_full)
        if not timeline_data:
            st.warning("⚠️ No timeline data found for this command")
            return
        st.markdown(f"### 📅 Timeline for: **{command_full}**")
        # Show version count
        version_count = len(timeline_data)
        st.info(f"📊 Total versions: {version_count}")
        # Show timeline
        for i, version_data in enumerate(timeline_data):
            version_id = version_data['id']
            version_num = version_data['version']
            content = version_data['content']
            created_at = version_data['created_at']
            updated_at = version_data['updated_at']
            is_latest = version_data['is_latest']
            # Create expander for each version
            with st.expander(f"Version {version_num} {'(Latest)' if is_latest else ''}", expanded=is_latest):
                col1, col2, col3 = st.columns([1, 2, 1])
                with col1:
                    st.metric("Version", version_num)
                    if is_latest:
                        st.success("Latest")
                    else:
                        st.info(f"v{version_num}")
                with col2:
                    st.text_area("Content", content, height=200, disabled=True, key=f"content_v{version_num}")
                with col3:
                    # Format timestamps properly
                    if created_at:
                        created_display = created_at[:19] if len(created_at) > 19 else created_at
                        st.metric("Created", created_display)
                    else:
                        st.metric("Created", "N/A")
                    if updated_at:
                        updated_display = updated_at[:19] if len(updated_at) > 19 else updated_at
                        st.metric("Updated", updated_display)
                    else:
                        st.metric("Updated", "N/A")
                    if not is_latest:
                        if st.button(f"🔄 Restore v{version_num}", key=f"restore_{version_id}"):
                            restore_command_version(processor, command_full, version_num)
        # Show version comparison if multiple versions exist
        if len(timeline_data) > 1:
            st.markdown("---")
            st.markdown("### 🔍 Version Comparison")
            col1, col2 = st.columns(2)
            with col1:
                version1 = st.selectbox("Select first version:", 
                                      [f"v{v['version']}" for v in timeline_data], 
                                      key="compare_v1")
            with col2:
                version2 = st.selectbox("Select second version:", 
                                      [f"v{v['version']}" for v in timeline_data], 
                                      key="compare_v2")
            if version1 != version2:
                v1_num = int(version1[1:])
                v2_num = int(version2[1:])
                v1_data = next(v for v in timeline_data if v['version'] == v1_num)
                v2_data = next(v for v in timeline_data if v['version'] == v2_num)
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown(f"**{version1}**")
                    st.text_area("Content", v1_data['content'], height=300, disabled=True)
                with col2:
                    st.markdown(f"**{version2}**")
                    st.text_area("Content", v2_data['content'], height=300, disabled=True)
    except Exception as e:
        st.error(f"❌ Error showing timeline: {e}")
        st.text(traceback.format_exc())


def restore_command_version(processor: CommandProcessor, command_full: str, version_num: int):
    """Restore a specific version of a command"""
    try:
        # Get the specific version data
        timeline_data = processor.get_command_timeline(command_full)
        target_version = next((v for v in timeline_data if v['version'] == version_num), None)
        if not target_version:
            st.error(f"❌ Version {version_num} not found")
            return
        # Mark current latest as not latest
        conn = processor.conn
        # Update current latest version
        conn.execute("""
            UPDATE commands 
            SET is_latest = FALSE 
            WHERE command_full = ? AND is_latest = TRUE
        """, (command_full,))
        # Mark target version as latest
        conn.execute("""
            UPDATE commands 
            SET is_latest = TRUE, updated_at = CURRENT_TIMESTAMP 
            WHERE id = ?
        """, (target_version['id'],))
        conn.commit()
        enable_auto_save_on_change()  # 触发自动保存
        st.success(f"✅ Version {version_num} restored successfully!")
        st.rerun()
    except Exception as e:
        st.error(f"❌ Error restoring version: {e}")
        st.text(traceback.format_exc())


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
        # Show version information if available
        if 'version' in df.columns:
            version_counts = df['version'].value_counts()
            if len(version_counts) > 1:
                st.info(f"📊 Versions: {', '.join([f'v{v} ({c})' for v, c in version_counts.items()])}")
                st.info("💡 Use the Timeline tab to view version history and compare changes")
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
                    col1, col2, col3 = st.columns(3)
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
                    with col3:
                        if st.button("📅 View Timeline", use_container_width=True):
                            st.session_state.command_tab_selector = "📅 Timeline"
                            st.rerun()
                else:
                    st.warning("⚠️ No data to display with selected filters")
            else:
                st.warning("⚠️ Please select at least one command type")
        else:
            st.info("ℹ️ No command types found in database")
    except Exception as e:
        st.error(f"❌ Error viewing data: {e}")
        st.text(traceback.format_exc())


def show_manual_command_input(processor: CommandProcessor, create_table_if_needed: bool = False):
    """显示手动命令输入界面"""
    st.markdown("### 手动添加新命令")
    # 检查是否有航班信息
    if not processor.flight_info:
        st.warning("⚠️ No flight information found in selected database")
        return
    # 显示当前航班信息
    flight_info = processor.flight_info
    st.info(f"✈️ 当前航班: {flight_info['flight_number']} - {flight_info['flight_date']}")
    # 手动输入表单
    with st.form("manual_command_form"):
        st.markdown("**输入完整的命令内容:**")
        raw_input = st.text_area(
            "完整原始输入（包括命令行和内容）:",
            height=300,
            key="manual_raw_input",
            help="请输入完整的命令内容，包括命令行（以>开头）和后续内容。例如：\n>SY:CA988/25JUL\nSOME COMMAND CONTENT",
            placeholder=f">SY:{flight_info['flight_number']}/{flight_info['flight_date']}\n"
        )
        # 提交按钮
        if st.form_submit_button("💾 添加命令", use_container_width=True, type="primary"):
            if raw_input.strip():
                save_manual_command(processor, raw_input.strip(), create_table_if_needed)
            else:
                st.error("❌ 请输入命令内容")


def save_manual_command(processor: CommandProcessor, raw_input: str, create_table_if_needed: bool = False):
    """保存手动输入的命令，支持版本控制"""
    try:
        # 应用字符修正
        corrected_input = apply_character_corrections(raw_input)
        # 解析命令行
        lines = corrected_input.split('\n')
        command_line = None
        for line in lines:
            stripped_line = line.strip()
            # 检查是否包含命令模式 [A-Z]{2,4}:
            if re.search(r'[A-Z]{2,4}:', stripped_line):
                command_line = stripped_line
                break
        if not command_line:
            st.error("❌ 未找到有效的命令行（应包含命令模式如 SY:, PD:, SE: 等）")
            return
        # 解析命令信息
        command_info = processor._parse_command_line(command_line)
        if not command_info:
            st.error("❌ 无法解析命令行格式")
            return
        # 验证航班信息
        if not processor.validate_flight_info(command_info['flight_number'], command_info['flight_date']):
            st.warning("⚠️ 警告：命令的航班信息与数据库不匹配")
        # 使用CommandProcessor的store_commands方法（自动创建表）
        command_data = {
            'command_full': command_info['command_full'],
            'command_type': command_info['command_type'],
            'flight_number': command_info['flight_number'],
            'flight_date': command_info['flight_date'],
            'content': corrected_input
        }
        # 检查命令是否已存在（现在支持版本控制）
        existing_commands = processor.get_all_commands_data()
        command_exists = any(existing.get('command_full') == command_info['command_full'] for existing in existing_commands)
        if command_exists:
            st.info(f"ℹ️ 命令 '{command_info['command_full']}' 已存在，将创建新版本")
        # 存储命令（CommandProcessor会自动创建表和新版本）
        stats = processor.store_commands([command_data])
        if stats['new'] > 0:
            st.success(f"✅ 命令已成功添加: {command_info['command_full']}")
            if create_table_if_needed:
                st.info("ℹ️ Commands table was automatically created")
            enable_auto_save_on_change()  # 触发自动保存
            st.rerun()
        elif stats['updated'] > 0:
            st.success(f"✅ 命令已更新为新版本: {command_info['command_full']}")
            st.info("💡 旧版本已保存在时间线中")
            enable_auto_save_on_change()  # 触发自动保存
            st.rerun()
        else:
            st.error("❌ 命令添加失败")
    except Exception as e:
        st.error(f"❌ Error saving command: {e}")
        import traceback
        st.text(traceback.format_exc())


def show_edit_data(processor: CommandProcessor):
    """Show command data editing interface"""
    st.subheader("✏️ Edit Command Data")
    try:
        # Get all commands data
        commands_data = processor.get_all_commands_data()
        if not commands_data:
            st.info("ℹ️ No command data found. You can manually add commands below.")
            show_manual_command_input(processor, create_table_if_needed=True)
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
    """Save edited command data with versioning support"""
    try:
        if not processor.conn:
            st.error("❌ No database connection available")
            return
        # Step 1: 处理特殊字符替换
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
        # Step 5: 使用版本控制系统保存命令
        conn = processor.conn
        try:
            if new_command_full == original_command_full:
                # 命令行未更改，检查内容是否改变
                cursor = conn.execute("""
                    SELECT id, version, content FROM commands 
                    WHERE command_full = ? AND is_latest = TRUE
                """, (original_command_full,))
                existing = cursor.fetchone()
                if existing and existing[2] != corrected_input:
                    # 内容改变，创建新版本
                    existing_id, existing_version = existing[0], existing[1]
                    # 标记旧版本为不是最新
                    conn.execute("""
                        UPDATE commands SET is_latest = FALSE WHERE id = ?
                    """, (existing_id,))
                    # 插入新版本
                    new_version = existing_version + 1
                    conn.execute("""
                        INSERT INTO commands (
                            command_full, command_type, flight_number, flight_date, 
                            content, version, parent_id, is_latest, created_at, updated_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, TRUE, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                    """, (
                        new_command_full, new_command_info['command_type'],
                        new_command_info['flight_number'], new_command_info['flight_date'],
                        corrected_input, new_version, existing_id
                    ))
                    st.success(f"✅ 命令内容已更新，创建新版本 v{new_version}")
                    st.info("💡 旧版本已保存在时间线中")
                else:
                    # 内容相同，只更新时间戳
                    conn.execute("""
                        UPDATE commands SET updated_at = CURRENT_TIMESTAMP 
                        WHERE command_full = ? AND is_latest = TRUE
                    """, (original_command_full,))
                    st.success("✅ 记录已更新（内容未改变）")
            else:
                # 命令行已更改，创建新命令记录
                # 检查新命令是否已存在
                cursor = conn.execute("""
                    SELECT id FROM commands WHERE command_full = ? AND is_latest = TRUE
                """, (new_command_full,))
                existing = cursor.fetchone()
                if existing:
                    st.error(f"❌ 命令 '{new_command_full}' 已存在。请选择不同的命令。")
                    return
                # 创建新命令记录
                conn.execute("""
                    INSERT INTO commands (
                        command_full, command_type, flight_number, flight_date, 
                        content, version, is_latest, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, 1, TRUE, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                """, (
                    new_command_full, new_command_info['command_type'],
                    new_command_info['flight_number'], new_command_info['flight_date'],
                    corrected_input
                ))
                st.success(f"✅ 已创建新命令记录: {new_command_full}")
                st.info(f"💡 原命令 '{original_command_full}' 仍然存在")
            conn.commit()
            enable_auto_save_on_change()  # 触发自动保存
        except Exception as e:
            conn.rollback()
            raise e
        st.rerun()
    except Exception as e:
        st.error(f"❌ Error saving changes: {e}")
        import traceback
        st.text(traceback.format_exc())


def delete_command_record(processor: CommandProcessor, command_full: str):
    """Delete a command record"""
    try:
        if not processor.conn:
            st.error("❌ No database connection available")
            return
        conn = processor.conn
        cursor = conn.execute("DELETE FROM commands WHERE command_full = ?", (command_full,))
        if cursor.rowcount > 0:
            st.success(f"✅ 已删除记录: {command_full}")
            enable_auto_save_on_change()  # 触发自动保存
        else:
            st.warning(f"⚠️ 未找到记录: {command_full}")
        conn.commit()
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


def migrate_commands_table(processor: CommandProcessor):
    """迁移现有commands表到支持时间线的版本"""
    try:
        if not processor.conn:
            st.error("❌ No database connection available")
            return False
        conn = processor.conn
        # 检查是否已经迁移过
        cursor = conn.execute("PRAGMA table_info(commands)")
        columns = [col[1] for col in cursor.fetchall()]
        if 'version' in columns and 'parent_id' in columns and 'is_latest' in columns:
            st.info("ℹ️ Commands table already supports timeline")
            return True
        # 备份现有数据
        existing_commands = conn.execute("SELECT * FROM commands").fetchall()
        if not existing_commands:
            st.info("ℹ️ No existing commands to migrate")
            return True
        # 创建新表结构
        conn.execute("""
            CREATE TABLE commands_new (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                command_full TEXT NOT NULL,
                command_type TEXT,
                flight_number TEXT,
                flight_date TEXT,
                content TEXT,
                version INTEGER DEFAULT 1,
                parent_id INTEGER,
                is_latest BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        # 迁移现有数据
        for cmd in existing_commands:
            # 假设现有表结构：id, command_full, command_type, flight_number, flight_date, content, created_at, updated_at
            if len(cmd) >= 7:  # 确保有足够的列
                conn.execute("""
                    INSERT INTO commands_new (
                        id, command_full, command_type, flight_number, flight_date, 
                        content, version, is_latest, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, 1, TRUE, ?, ?)
                """, (cmd[0], cmd[1], cmd[2], cmd[3], cmd[4], cmd[5], cmd[6], cmd[7]))
        # 删除旧表并重命名新表
        conn.execute("DROP TABLE commands")
        conn.execute("ALTER TABLE commands_new RENAME TO commands")
        # 创建索引
        conn.execute("CREATE INDEX idx_commands_timeline ON commands(command_full, version)")
        conn.execute("CREATE INDEX idx_commands_parent ON commands(parent_id)")
        conn.execute("CREATE INDEX idx_commands_latest ON commands(command_full, is_latest)")
        conn.commit()
        st.success(f"✅ Successfully migrated {len(existing_commands)} commands to timeline system!")
        return True
    except Exception as e:
        st.error(f"❌ Error migrating commands table: {e}")
        import traceback
        st.error(f"❌ Full error details: {traceback.format_exc()}")
        return False


def show_command_settings(processor: CommandProcessor):
    """Show command analysis settings"""
    # Check if database file exists and show file info
    if not processor.conn:
        st.error("❌ Database not connected.")
        return

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
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Records", len(commands_data))
        with col2:
            st.metric("Command Types", len(command_types))
        with col3:
            try:
                # Get total versions including all historical versions
                all_versions = processor.get_all_commands_with_versions()
                total_versions = len(all_versions)
                st.metric("Total Versions", total_versions)
            except AttributeError:
                st.metric("Total Versions", "N/A")
                st.warning("⚠️ Timeline methods not available - migration needed")
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
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("🔄 Migrate to Timeline", use_container_width=True, key="migrate_timeline"):
            success = migrate_commands_table(processor)
            if success:
                st.success("✅ Migration completed! Please refresh the page.")
                st.rerun()
            else:
                st.error("❌ Migration failed. Check the error messages above.")
    with col2:        
        if st.button("🗑️ Clear All Command Data", use_container_width=True):
            if st.session_state.get('confirm_clear_commands', False):
                try:
                    if processor.conn:
                        conn = processor.conn
                        conn.execute("DELETE FROM commands")
                        conn.commit()
                        enable_auto_save_on_change()  # 触发自动保存
                        st.success("✅ All command data cleared!")
                        st.session_state.confirm_clear_commands = False
                        # 清除数据后清理文件
                        cleanup_command_files()
                        st.rerun()
                    else:
                        st.error("❌ No database connection available")
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
    with col3:
        if st.button("📊 Refresh Statistics", use_container_width=True):
            st.rerun()

