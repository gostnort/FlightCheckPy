#!/usr/bin/env python3
"""
Add/Edit Record functionality for HBPR UI - Single record editing and validation
"""

import streamlit as st
import pandas as pd
import sqlite3
import re
import traceback
from scripts.hbpr_info_processor import CHbpr, HbprDatabase
from scripts.hbpr_list_processor import HBPRProcessor
from ui.common import get_current_database


def show_add_edit_record():
    """查看单个记录"""
    try:
        db = HbprDatabase()
        db.find_database()
        # 获取当前选中的数据库
        selected_db_file = get_current_database()
        if not selected_db_file:
            st.error("❌ No database selected! Please select a database from the sidebar.")
            return
        # 如果选择了不同的数据库，重新初始化
        if selected_db_file != db.db_file:
            db = HbprDatabase(selected_db_file)
        conn = sqlite3.connect(db.db_file)
        cursor = conn.cursor()
        # 检查是否有已处理的记录
        cursor.execute("""
            SELECT hbnb_number, boarding_number, name, seat, tkne 
            FROM hbpr_full_records 
            WHERE is_validated = 1 AND (boarding_number IS NOT NULL OR name IS NOT NULL OR seat IS NOT NULL OR tkne IS NOT NULL)
            ORDER BY hbnb_number
        """)
        processed_records = cursor.fetchall()
        # 获取所有记录（包括未处理的）
        cursor.execute("SELECT hbnb_number FROM hbpr_full_records ORDER BY hbnb_number")
        all_records = [row[0] for row in cursor.fetchall()]
        conn.close()
        
        if not all_records:
            st.warning("⚠️ No HBPR records found in database.")
            return
        
        # 选择记录的方式
        selection_method = st.radio(
            "👀 View Record 🧺🧺🧺🧺 Sorting by:",
            ["HBNB Number", "Boarding Number (BN)", "Seat", "Name", "TKNE"],
            horizontal=True
        )
        
        selected_record = None
        
        if selection_method == "HBNB Number":
            # HBNB选择（按数字从小到大排序）
            # 检查是否有预选的HBNB号码
            default_index = 0
            sorted_records = sorted(all_records)
            if hasattr(st.session_state, 'selected_hbnb_for_edit') and st.session_state.selected_hbnb_for_edit:
                try:
                    default_index = sorted_records.index(st.session_state.selected_hbnb_for_edit)
                    # 清除session state中的预选值
                    del st.session_state.selected_hbnb_for_edit
                except ValueError:
                    # 如果预选的HBNB不在列表中，使用默认值
                    default_index = 0
            
            hbnb_number = st.selectbox(
                "Select HBNB Number:",
                sorted_records,
                index=default_index,
                help="Choose an HBNB number to view"
            )
            selected_record = hbnb_number  
        elif selection_method == "Boarding Number (BN)":
            # BN选择（按数字从小到大排序）
            if processed_records:
                # 提取有效的BN号码并排序
                bn_records = [(row[0], row[1]) for row in processed_records if row[1] is not None and row[1] > 0]
                bn_records.sort(key=lambda x: x[1])  
                # 按BN号码排序
                if bn_records:
                    bn_options = [f"{record[1]}" for record in bn_records]
                    selected_bn = st.selectbox(
                        "Select Boarding Number:",
                        bn_options,
                        help="Choose a boarding number to view"
                    )
                    # 提取HBNB号码 - find the record with matching boarding number
                    selected_record = None
                    for record in bn_records:
                        if str(record[1]) == selected_bn:
                            selected_record = record[0]
                            break
                else:
                    st.warning("⚠️ No boarding numbers found in processed records.")
                    return
            else:
                st.warning("⚠️ No processed records found. Please process records first.")
                return
         # 座位选择（按行号从小到大，然后按座位号A-Z排序）        
        elif selection_method == "Seat":
            if processed_records:
                # 提取有效的座位并排序
                seat_records = [(row[0], row[3]) for row in processed_records if row[3] is not None and row[3].strip()]
                if seat_records:
                    # 自定义座位排序函数
                    def seat_sort_key(seat_tuple):
                        seat = seat_tuple[1]
                        # 提取行号和座位号
                        match = re.match(r'(\d+)([A-Z])', seat)
                        if match:
                            row_num = int(match.group(1))
                            seat_letter = match.group(2)
                            return (row_num, seat_letter)
                        return (999, 'Z')  # 无效座位排在最后
                    
                    seat_records.sort(key=seat_sort_key)
                    seat_options = [f"{record[1]}" for record in seat_records]
                    selected_seat = st.selectbox(
                        "Select Seat:",
                        seat_options,
                        help="Choose a seat to view"
                    )
                    # 提取HBNB号码 - find the record with matching seat
                    selected_record = None
                    for record in seat_records:
                        if record[1] == selected_seat:
                            selected_record = record[0]
                            break
                else:
                    st.warning("⚠️ No seats found in processed records.")
                    return
            else:
                st.warning("⚠️ No processed records found. Please process records first.")
                return
        # 姓名选择（按字母A-Z排序）        
        elif selection_method == "Name":
            if processed_records:
                # 提取有效的姓名并排序
                name_records = [(row[0], row[2]) for row in processed_records if row[2] is not None and row[2].strip()]
                if name_records:
                    # 按姓名排序
                    name_records.sort(key=lambda x: x[1].upper())
                    name_options = [f"{record[1]}" for record in name_records]
                    selected_name = st.selectbox(
                        "Select Name:",
                        name_options,
                        help="Choose a passenger name to view"
                    )
                    # 提取HBNB号码 - find the record with matching name
                    selected_record = None
                    for record in name_records:
                        if record[1] == selected_name:
                            selected_record = record[0]
                            break
                else:
                    st.warning("⚠️ No names found in processed records.")
                    return
            else:
                st.warning("⚠️ No processed records found. Please process records first.")
                return
        
        # TKNE选择
        elif selection_method == "TKNE":
            if processed_records:
                # 获取TKNE数据
                conn = sqlite3.connect(db.db_file)
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT hbnb_number, tkne 
                    FROM hbpr_full_records 
                    WHERE is_validated = 1 AND tkne IS NOT NULL AND tkne != ''
                    ORDER BY tkne
                """)
                tkne_records = cursor.fetchall()
                conn.close()
                
                if tkne_records:
                    # 按TKNE排序
                    tkne_records.sort(key=lambda x: x[1])
                    tkne_options = [f"{record[1]}" for record in tkne_records]
                    selected_tkne = st.selectbox(
                        "Select TKNE:",
                        tkne_options,
                        help="Choose a TKNE to view"
                    )
                    # 提取HBNB号码 - find the record with matching TKNE
                    selected_record = None
                    for record in tkne_records:
                        if record[1] == selected_tkne:
                            selected_record = record[0]
                            break
                else:
                    st.warning("⚠️ No TKNE found in processed records.")
                    return
            else:
                st.warning("⚠️ No processed records found. Please process records first.")
                return
        # 显示记录预览
        if selected_record:
            try:
                content = db.get_hbpr_record(selected_record)
                # Apply dynamic font settings
                apply_font_settings()
                edited_content = st.text_area("Raw Content:", content, height=300, disabled=False, key=f"editable_content_{selected_record}")
                # 添加替换和重复记录按钮
                col1, col2 = st.columns([3, 2])
                with col1:
                    replace_clicked = st.button("🔍 Replace the Record", use_container_width=True, key=f"replace_{selected_record}")
                with col2:
                    duplicate_clicked = st.button("📋 Create Duplicate", use_container_width=True, key=f"duplicate_{selected_record}")
                if replace_clicked:
                    _process_replace_record(db, edited_content)
                if duplicate_clicked:
                    _process_duplicate_record(db, edited_content)   
            except Exception as e:
                st.error(f"❌ Error retrieving record: {str(e)}")
        # 显示重复记录区域
        st.markdown("---")
        st.subheader("📋 Duplicate Records")
        _show_duplicate_records_section(db)    
    except Exception as e:
        st.error(f"❌ Error accessing database: {str(e)}")


def apply_font_settings():
    """Apply dynamic font settings from session state"""
    # Get font settings from session state
    font_family = st.session_state.get('settings', {}).get('font_family', 'Courier New')
    font_size_percent = st.session_state.get('settings', {}).get('font_size_percent', 100)
    
    # Calculate font size in pixels (assuming default is 14px)
    font_size_px = int(14 * font_size_percent / 100)
    
    # Apply font settings using CSS
    st.markdown(f"""
    <style>
    .stTextArea textarea {{
        font-family: '{font_family}', monospace !important;
        font-size: {font_size_px}px !important;
    }}
    .stDataFrame {{
        font-family: '{font_family}', monospace !important;
        font-size: {font_size_px}px !important;
    }}
    </style>
    """, unsafe_allow_html=True)


def validate_full_hbpr_record(hbpr_content):
    """
    Validate if the input content is a valid full HBPR record
    
    Args:
        hbpr_content: String content to validate
        
    Returns:
        dict: {
            'is_valid': bool,
            'hbnb_number': int or None,
            'errors': list of error messages,
            'chbpr_errors': dict of CHbpr error messages,
            'corrected_content': str - the content with any corrections applied
        }
    """
    result = {
        'is_valid': False,
        'hbnb_number': None,
        'errors': [],
        'chbpr_errors': {},
        'corrected_content': hbpr_content
    }
    
    # Check if content is not empty
    if not hbpr_content or not hbpr_content.strip():
        result['errors'].append("Input content is empty")
        return result
    
    # Handle special character replacement before "HBPR:" if ">HBPR:" is not found
    if '>HBPR:' not in hbpr_content:
        # Look for DLE character (ASCII 16, \x10) before "HBPR:" and replace with ">"
        dle_pattern = r'\x10HBPR:'
        if re.search(dle_pattern, hbpr_content):
            hbpr_content = re.sub(dle_pattern, '>HBPR:', hbpr_content)
            st.info("ℹ️ Detected DLE character before 'HBPR:' - automatically replaced with '>'")
        # Look for del character (ASCII 127, \x7f) before "HBPR:" and replace with ">"
        elif re.search(r'\x7fHBPR:', hbpr_content):
            hbpr_content = re.sub(r'\x7fHBPR:', '>HBPR:', hbpr_content)
            st.info("ℹ️ Detected DEL character before 'HBPR:' - automatically replaced with '>'")
        # Check for other common control characters before "HBPR:"
        elif re.search(r'[\x00-\x1f\x7f]HBPR:', hbpr_content):
            hbpr_content = re.sub(r'[\x00-\x1f\x7f]HBPR:', '>HBPR:', hbpr_content)
            st.info("ℹ️ Detected control character before 'HBPR:' - automatically replaced with '>'")
        # Check for visible "del" text (in case it's displayed as text)
        elif re.search(r'delHBPR:', hbpr_content, re.IGNORECASE):
            hbpr_content = re.sub(r'delHBPR:', '>HBPR:', hbpr_content, flags=re.IGNORECASE)
            st.info("ℹ️ Detected 'del' text before 'HBPR:' - automatically replaced with '>'")
        # Handle case where HBPR: appears without any prefix character
        elif re.search(r'^HBPR:', hbpr_content, re.MULTILINE):
            hbpr_content = re.sub(r'^HBPR:', '>HBPR:', hbpr_content, flags=re.MULTILINE)
            st.info("ℹ️ Detected 'HBPR:' without prefix - automatically added '>' prefix")
    
    # Store the corrected content for further processing
    corrected_content = hbpr_content
    result['corrected_content'] = corrected_content
    
    # Step 1: Check basic regex pattern for full HBPR record
    # Must start with >HBPR: and contain flight info and HBNB number
    hbpr_pattern = r'>HBPR:\s*[^,]+,(\d+)'
    hbpr_match = re.search(hbpr_pattern, hbpr_content)
    
    if not hbpr_match:
        result['errors'].append("Input does not contain valid full HBPR record format (>HBPR: flight_info,hbnb_number)")
        return result
    
    try:
        hbnb_number = int(hbpr_match.group(1))
        result['hbnb_number'] = hbnb_number
    except ValueError:
        result['errors'].append("Invalid HBNB number format")
        return result
    
    # Step 2: Use HBPRProcessor to parse and validate the record format
    try:
        # Create a temporary file-like content for parsing (use corrected content)
        lines = corrected_content.split('\n')
        
        # Find the line that starts with >HBPR:
        hbpr_line_index = -1
        for i, line in enumerate(lines):
            if line.strip().startswith('>HBPR:'):
                hbpr_line_index = i
                break
        
        if hbpr_line_index == -1:
            result['errors'].append("No line starting with '>HBPR:' found in the content")
            return result
        
        # Create HBPRProcessor instance
        processor = HBPRProcessor("temp_input")  # We'll override the file reading
        
        # Use the public parse_full_record method starting from the HBPR line
        parsed_hbnb, parsed_content, next_index = processor.parse_full_record(lines, hbpr_line_index)
        
        if parsed_hbnb is None:
            result['errors'].append("HBPRProcessor failed to parse the full record format")
            return result
        
        if parsed_hbnb != hbnb_number:
            result['errors'].append(f"HBNB number mismatch: regex found {hbnb_number}, parser found {parsed_hbnb}")
            return result
            
    except Exception as e:
        result['errors'].append(f"HBPRProcessor validation failed: {str(e)}")
        return result
    
    # Step 3: Use CHbpr to test the record and check for errors
    try:
        chbpr = CHbpr()
        chbpr.run(corrected_content)
        
        # Store CHbpr errors for reference
        result['chbpr_errors'] = chbpr.error_msg
        
        # Check specifically for 'Other' category errors (critical errors)
        if chbpr.error_msg.get('Other'):
            result['errors'].append(f"CHbpr validation failed with critical errors: {'; '.join(chbpr.error_msg['Other'])}")
            return result
        
        # Verify HBNB number was extracted correctly
        if chbpr.HbnbNumber != hbnb_number:
            result['errors'].append(f"CHbpr HBNB number mismatch: expected {hbnb_number}, got {chbpr.HbnbNumber}")
            return result
            
    except Exception as e:
        result['errors'].append(f"CHbpr processing failed: {str(e)}")
        return result
    
    # If we reach here, all validations passed
    result['is_valid'] = True
    return result


def display_processing_results(chbpr):
    """显示处理结果"""
    data = chbpr.get_structured_data()
    
    # 验证状态
    if chbpr.is_valid():
        st.success("✅ **Validation: PASSED**")
    else:
        st.error("❌ **Validation: FAILED**")
    
    # 错误信息
    if not chbpr.is_valid():
        st.subheader("⚠️ Validation Errors")
        for error_type, error_list in chbpr.error_msg.items():
            if error_list:  # 只显示有错误的类型
                st.subheader(f"🔴 {error_type} Errors")
                for error in error_list:
                    st.error(error)
    
    # 调试信息
    with st.expander("🔧 Debug Information"):
        for debug in chbpr.debug_msg:
            st.text(debug)


def _process_replace_record(db, hbpr_content):
    """处理记录替换"""
    if not hbpr_content.strip():
        st.warning("⚠️ Please enter HBPR content first.")
        return
    
    # Step 1: Validate the full HBPR record format
    st.subheader("🔍 Validating HBPR Record")
    validation_result = validate_full_hbpr_record(hbpr_content)
    
    if not validation_result['is_valid']:
        st.error("❌ HBPR Record Validation Failed")
        for error in validation_result['errors']:
            st.error(f"• {error}")
        
        # Show CHbpr errors if available for debugging
        if validation_result['chbpr_errors']:
            with st.expander("🔧 Debug Information"):
                st.write("CHbpr Error Categories:")
                for category, errors in validation_result['chbpr_errors'].items():
                    if errors:
                        st.write(f"**{category}:** {'; '.join(errors)}")
        return
    
    # Validation passed - proceed with processing
    st.success("✅ HBPR Record Format Validation Passed")
    
    try:
        # Get the corrected content from validation result
        corrected_content = validation_result['corrected_content']
        
        # Create CHbpr instance for final processing (we know it's valid)
        chbpr = CHbpr()
        chbpr.run(corrected_content)
        
        # Verify no critical errors occurred during processing
        if chbpr.error_msg.get('Other'):
            st.error("❌ Critical errors occurred during CHbpr processing:")
            for error in chbpr.error_msg['Other']:
                st.error(f"• {error}")
            return
        
        # Process the record
        _process_record_common(db, chbpr, corrected_content, is_duplicate=False)
        
    except Exception as e:
        st.error(f"❌ Error processing full record: {str(e)}")
        st.error(traceback.format_exc())


def _process_duplicate_record(db, hbpr_content):
    """处理重复记录创建"""
    if not hbpr_content.strip():
        st.warning("⚠️ Please enter HBPR content first.")
        return
    
    # First validate and get corrected content
    validation_result = validate_full_hbpr_record(hbpr_content)
    
    if not validation_result['is_valid']:
        st.error("❌ HBPR Record Validation Failed")
        for error in validation_result['errors']:
            st.error(f"• {error}")
        return
    
    try:
        # Get the corrected content from validation result
        corrected_content = validation_result['corrected_content']
        
        # 处理HBPR记录
        chbpr = CHbpr()
        chbpr.run(corrected_content)
        
        # 获取HBNB的simple_record和full_record信息
        hbnb_exists = db.check_hbnb_exists(chbpr.HbnbNumber)
        
        # 显示处理前的状态信息
        st.subheader("📋 Duplicate Record Processing Information")
        _show_processing_info(db, chbpr.HbnbNumber, hbnb_exists)
        
        # 验证航班信息匹配
        if not _validate_flight_info(db, corrected_content):
            return
        
        # 检查原始记录是否存在
        if not hbnb_exists['full_record']:
            st.error(f"❌ Cannot create duplicate: No full record exists for HBNB {chbpr.HbnbNumber}")
            st.info("💡 Please create the original full record first using 'Replace the Record' button.")
            return
        
        # 创建重复记录
        db.create_duplicate_record(chbpr.HbnbNumber, chbpr.HbnbNumber, corrected_content)
        st.success(f"✅ Created duplicate record for HBNB {chbpr.HbnbNumber}")
        
        # 更新验证结果
        db.update_with_chbpr_results(chbpr)
        
        # 更新missing_numbers表
        _update_missing_numbers(db)
        
        st.success("✅ Duplicate record processed and stored!")
        display_processing_results(chbpr)
        
        # 设置刷新标志
        st.session_state.refresh_home = True
        
    except Exception as e:
        st.error(f"❌ Error processing duplicate record: {str(e)}")
        st.error(traceback.format_exc())


def _process_record_common(db, chbpr, hbpr_content, is_duplicate=False):
    """通用记录处理逻辑"""
    # 获取当前数据库的flight_info
    flight_info = db.get_flight_info()
    
    # 获取HBNB的simple_record和full_record信息
    hbnb_exists = db.check_hbnb_exists(chbpr.HbnbNumber)
    
    # 显示处理前的状态信息
    st.subheader("📋 Processing Information")
    _show_processing_info(db, chbpr.HbnbNumber, hbnb_exists)
    
    # 验证航班信息匹配
    if not _validate_flight_info(db, hbpr_content):
        return
    
    # All validations passed - proceed with database operations
    st.subheader("💾 Database Operations")
    
    # 处理记录替换/创建逻辑
    if hbnb_exists['exists']:
        # Auto backup existing full record before replacement
        if hbnb_exists['full_record']:
            try:
                backup_success = db.auto_backup_before_replace(chbpr.HbnbNumber)
                if backup_success:
                    st.info(f"📦 Auto-backed up original record for HBNB {chbpr.HbnbNumber} with original timestamp")
                else:
                    st.warning(f"⚠️ Original record NOT exist for HBNB {chbpr.HbnbNumber}")
            except Exception as e:
                st.warning(f"⚠️ Backup failed for HBNB {chbpr.HbnbNumber}: {str(e)}")
        
        if hbnb_exists['simple_record']:
            # 如果存在简单记录，删除它并创建完整记录
            db.delete_simple_record(chbpr.HbnbNumber)
            st.info(f"🔄 Replaced simple record for HBNB {chbpr.HbnbNumber}")
        
        # 创建或更新完整记录
        db.create_full_record(chbpr.HbnbNumber, hbpr_content)
        if hbnb_exists['full_record']:
            st.success(f"✅ Replaced full record for HBNB {chbpr.HbnbNumber} (original backed up)")
        else:
            st.success(f"✅ Updated record for HBNB {chbpr.HbnbNumber}")
    else:
        # 创建新的完整记录
        db.create_full_record(chbpr.HbnbNumber, hbpr_content)
        st.success(f"✅ Created new full record for HBNB {chbpr.HbnbNumber}")
    
    # 更新验证结果
    db.update_with_chbpr_results(chbpr)
    
    # 更新missing_numbers表
    _update_missing_numbers(db)
    
    st.success("✅ Full record processed and stored!")
    st.info("ℹ️ You can now clear the input box manually or enter new content.")
    display_processing_results(chbpr)
    
    # 设置刷新标志
    st.session_state.refresh_home = True


def _show_processing_info(db, hbnb_number, hbnb_exists):
    """显示处理信息"""
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.write("**Database Flight Info:**")
        flight_info = db.get_flight_info()
        if flight_info:
            st.write(f"Flight: {flight_info['flight_number']}")
            st.write(f"Date: {flight_info['flight_date']}")
        else:
            st.write("No flight info available")
    
    with col2:
        st.write("**HBNB Status:**")
        if hbnb_exists['exists']:
            if hbnb_exists['full_record']:
                st.write(f"HBNB {hbnb_number}: Full record exists")
            elif hbnb_exists['simple_record']:
                st.write(f"HBNB {hbnb_number}: Simple record exists")
        else:
            st.write(f"HBNB {hbnb_number}: New record")
    
    with col3:
        st.write("**Validation Status:**")
        st.success("✅ Format valid")
        st.success("✅ CHbpr test passed")


def _validate_flight_info(db, hbpr_content):
    """验证航班信息匹配"""
    flight_validation = db.validate_flight_info_match(hbpr_content)
    
    if not flight_validation['match']:
        st.error(f"❌ Flight info mismatch: {flight_validation['reason']}")
        if 'db_flight' in flight_validation and 'hbpr_flight' in flight_validation:
            col1, col2 = st.columns(2)
            with col1:
                st.write("**Database Flight:**")
                st.write(f"Number: {flight_validation['db_flight']['flight_number']}")
                st.write(f"Date: {flight_validation['db_flight']['flight_date']}")
            with col2:
                st.write("**HBPR Flight:**")
                st.write(f"Number: {flight_validation['hbpr_flight']['flight_number']}")
                st.write(f"Date: {flight_validation['hbpr_flight']['flight_date']}")
        return False
    return True


def _update_missing_numbers(db):
    """更新missing_numbers表"""
    try:
        db.update_missing_numbers_table()
        st.info("🔄 Updated missing numbers table")
    except Exception as e:
        st.warning(f"⚠️ Warning: Could not update missing numbers table: {str(e)}")


def _show_duplicate_records_section(db):
    """显示重复记录区域（可复用组件）"""
    # 获取有重复记录的HBNB号码
    duplicate_hbnbs = db.get_all_duplicate_hbnbs()
    
    if duplicate_hbnbs:
        # 创建两列布局
        left_col, right_col = st.columns([2, 3])
        
        with left_col:
            # 选择要查看的HBNB
            selected_hbnb = st.selectbox(
                "Select HBNB to view duplicates:",
                options=duplicate_hbnbs,
                help="Select an HBNB number to view its duplicate records",
                key="duplicate_records_selectbox"
            )
            
            if selected_hbnb:
                _show_duplicate_records_for_hbnb(db, selected_hbnb, left_col, right_col)
    else:
        st.info("ℹ️ No duplicate records found in database.")
        st.info("💡 Create duplicate records using the 'Create a Duplicate Record' button above.")


def _show_duplicate_records_for_hbnb(db, selected_hbnb, left_col, right_col):
    """显示特定HBNB的重复记录"""
    # 获取原始记录和重复记录
    original_record = db.get_hbpr_record(selected_hbnb)
    duplicate_records = db.get_duplicate_records(selected_hbnb)
    
    # 创建组合数据用于DataFrame显示
    display_data = []
    
    # 添加原始记录（在顶部）
    display_data.append({
        'Type': 'Original',
        'Record ID': 0,  # Use 0 for original record to maintain integer type
        'Created At': 'Original Record'
    })
    
    # 添加重复记录（按创建时间排序）
    for dup in duplicate_records:
        display_data.append({
            'Type': 'Duplicate',
            'Record ID': int(dup['id']),  # Ensure integer type
            'Created At': dup['created_at']
        })
    
    # 显示DataFrame
    if display_data:
        records_df = pd.DataFrame(display_data)
        
        # Ensure proper data types
        records_df['Record ID'] = records_df['Record ID'].astype(int)
        records_df['Type'] = records_df['Type'].astype(str)
        records_df['Created At'] = records_df['Created At'].astype(str)
        
        with left_col:
            # 使用st.dataframe创建可选择的表格
            event = st.dataframe(
                records_df,
                use_container_width=True,
                height=400,
                hide_index=True,
                on_select="rerun",
                selection_mode="single-row",
                column_config={
                    "Record ID": st.column_config.NumberColumn("Record ID", format="%d"),
                    "Type": "Type",
                    "Created At": "Created At"
                }
            )
        
        # 显示统计信息
        st.markdown("### 📊 Statistics")
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Original HBNB", selected_hbnb)
        with col2:
            st.metric("Duplicates", len(duplicate_records))
        
        with right_col:
            # Record Content区域
            st.markdown("### 📄 Record Content")
            
            if selected_hbnb and display_data:
                # 检查是否有选中的行
                if event.selection.rows:
                    selected_row_index = event.selection.rows[0]
                    selected_row = records_df.iloc[selected_row_index]
                    
                    if selected_row['Type'] == 'Original':
                        # 显示原始记录
                        record_content = original_record
                        record_label = f"Original Record (HBNB: {selected_hbnb})"
                    else:
                        # 显示重复记录
                        record_id = int(selected_row['Record ID'])
                        record_content = db.get_duplicate_record_content(record_id)
                        record_label = f"Duplicate Record (ID: {record_id})"                               
                else:
                    # 默认显示原始记录
                    record_content = original_record
                    record_label = f"Original Record (HBNB: {selected_hbnb})"
                    st.info("👈 Click on a row to view its content")
                    st.info(f"🔘 **{record_label}** (Default)")
                
                # 在文本区域显示记录内容（只读）
                st.text_area(
                    "Content:",
                    value=record_content,
                    height=422,
                    disabled=True,  # 设置为只读
                    key=f"readonly_content_{selected_hbnb}_{event.selection.rows[0] if event.selection.rows else 'default'}"
                )
            else:
                st.info("Select an HBNB from the left to view records")
