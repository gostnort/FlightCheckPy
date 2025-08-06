#!/usr/bin/env python3
"""
Process Records page for HBPR UI - Record processing and validation interface
"""

import streamlit as st
import pandas as pd
import os
import sqlite3
import re
from datetime import datetime
from scripts.hbpr_info_processor import CHbpr, HbprDatabase
from scripts.hbpr_list_processor import HBPRProcessor
from ui.common import apply_global_settings, parse_hbnb_input, get_current_database
import traceback


def show_process_records():
    """显示记录处理页面"""
    # Apply settings
    apply_global_settings()
    
    st.header("🔍 Process HBPR Records")
    
    try:
        db = HbprDatabase()
        db.find_database()
        
        tab1, tab2, tab3 = st.tabs(["🚀 Process All Records", "👀 View Record", "📄 Manual Input"])
        
        with tab1:
            process_all_records(db)
        
        with tab2:
            view_single_record(db)
        
        with tab3:
            process_manual_input()
        
    except Exception as e:
        st.error(f"❌ Database not available: {str(e)}")
        st.info("💡 Please build a database first in the Database Management page.")


def process_all_records(db):
    """处理所有记录并显示错误信息"""
    st.subheader("🚀 Process All Records")
    
    try:
        # 获取当前选中的数据库
        selected_db_file = get_current_database()
        
        if not selected_db_file:
            st.error("❌ No database selected! Please select a database from the sidebar.")
            return
        
        # 显示当前使用的数据库
        st.info(f"Using database: `{os.path.basename(selected_db_file)}`")
        
        # 如果选择了不同的数据库，重新初始化
        if selected_db_file != db.db_file:
            db = HbprDatabase(selected_db_file)
        st.markdown("**Processing Options:**")
        # 处理控制
        col1, col2 = st.columns(2)
        with col1: 
            if st.button("🚀 Start Processing", use_container_width=True):
                    start_processing_all_records(db, None)  # Always process all records
        with col2:
            if st.button("🧹 Erase Result", use_container_width=True):
                erase_splited_records(db)
        
        # 显示错误分组统计
        show_error_summary(db)
        # 显示错误信息
        show_error_messages(db)
        
    except Exception as e:
        st.error(f"❌ Error accessing database: {str(e)}")


def view_single_record(db):
    """查看单个记录"""
    try:
        # 获取当前选中的数据库
        selected_db_file = get_current_database()
        
        if not selected_db_file:
            st.error("❌ No database selected! Please select a database from the sidebar.")
            return
        
        # 显示当前使用的数据库
        st.info(f"Using database: `{os.path.basename(selected_db_file)}`")
        
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
            hbnb_number = st.selectbox(
                "Select HBNB Number:",
                sorted(all_records),
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
            col1, col2 = st.columns([1,2])
            st.markdown("""
                <style>
                .fixed-height {
                    height: 45px;
                    overflow-y: auto;
                    align-items: center;
                    justify-content: center;
                    padding: 0.5rem;
                    border-radius: 0.5rem;
                    text-align: left;
                }
                </style>
            """, unsafe_allow_html=True)
            with col1:
                #st.subheader("📄 Raw HBPR Content", help="Raw HBPR Content")
                st.markdown('<div class="fixed-height" style="font-size: 20px; font-weight: bold;"> 📄 Raw HBPR Content</div>', unsafe_allow_html=True)
            with col2:
                # 显示警告信息（当选择BN或Seat时）
                if selection_method in ["Boarding Number (BN)", "Seat", "TKNE"]:
                    # 使用自定义CSS来设置警告消息的样式
                    st.markdown('<div class="fixed-height">⚠️ 剔除部分没有 #️⃣ BN or 💺 Seat or 🎫 TKNE 的记录</div>', unsafe_allow_html=True)
            try:
                content = db.get_hbpr_record(selected_record)
                # Apply dynamic font settings
                apply_font_settings()
                st.text_area("Raw Content:", content, height=300, disabled=True)         
            except Exception as e:
                st.error(f"❌ Error retrieving record: {str(e)}")
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


def start_processing_all_records(db, batch_size):
    """开始处理所有记录"""
    try:
        # 获取所有记录
        conn = sqlite3.connect(db.db_file)
        cursor = conn.cursor()
        cursor.execute("SELECT hbnb_number FROM hbpr_full_records ORDER BY hbnb_number")
        records = [row[0] for row in cursor.fetchall()]
        conn.close()
        
        if not records:
            st.info("ℹ️ No records found.")
            return
        
        results_container = st.container()
        
        processed_count = 0
        valid_count = 0
        error_count = 0
        
        # 使用spinner显示处理状态
        with st.spinner(f"🔄 Processing {len(records)} records..."):
            for hbnb_number in records:
                try:
                    # 处理记录
                    content = db.get_hbpr_record(hbnb_number)
                    chbpr = CHbpr()
                    chbpr.run(content)
                    
                    # 更新数据库
                    success = db.update_with_chbpr_results(chbpr)
                    
                    if success:
                        processed_count += 1
                        if chbpr.is_valid():
                            valid_count += 1
                        else:
                            error_count += 1
                    
                except Exception as e:
                    # 静默处理错误，不显示具体错误信息
                    pass
        
        # 显示结果总结
        with results_container:
            st.success(f"🎉 Processed {processed_count} records")
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("Total Processed", processed_count)
            with col2:
                st.metric("Valid Records", valid_count)
            with col3:
                st.metric("Records with Errors", error_count)
        
        # 自动刷新页面以显示新的错误信息
        st.rerun()
    
    except Exception as e:
        st.error(f"❌ Processing error: {str(e)}")


def erase_splited_records(db):
    """清除所有处理结果，重置hbpr_full_records表中的处理字段"""
    try:
        # 显示确认对话框
        if st.button("⚠️ Confirm Erase", type="primary"):
            with st.spinner("🧹 Erasing all processing results..."):
                # 调用数据库类的erase_splited_records方法
                success = db.erase_splited_records()
                
                if success:
                    st.success("✅ Successfully erased all processing results!")
                    st.info("ℹ️ All processing fields have been reset. Only HBNB numbers and raw content remain.")
                    
                    # 自动刷新页面以显示更新后的状态
                    st.rerun()
                else:
                    st.error("❌ Failed to erase processing results.")
        
        else:
            st.warning("⚠️ This will permanently remove ALL processing results from the database.")
            st.info("💡 Only HBNB numbers and raw content will be preserved. Click 'Confirm Erase' to proceed.")
    
    except Exception as e:
        st.error(f"❌ Error during cleanup: {str(e)}")


def show_error_summary(db):
    """显示错误分组统计"""
    try:
        conn = sqlite3.connect(db.db_file)
        # 查询有错误的记录
        df = pd.read_sql_query("""
            SELECT error_baggage, error_passport, error_name, error_visa, error_other
            FROM hbpr_full_records 
            WHERE is_validated = 1 AND is_valid = 0 AND error_count > 0
        """, conn)
        conn.close()
        
        if df.empty:
            st.info("ℹ️ No error messages found. All processed records are valid!")
            return
        
        # 统计每种错误类型的数量
        error_types = ['error_baggage', 'error_passport', 'error_name', 'error_visa', 'error_other']
        error_labels = ['Baggage', 'Passport', 'Name', 'Visa', 'Other']
        error_counts = {}
        
        for error_type, label in zip(error_types, error_labels):
            # 计算非空错误的数量
            count = df[df[error_type].notna() & (df[error_type] != '')].shape[0]
            error_counts[label] = count
        
        # 显示错误统计
        total_records_with_errors = len(df)
        st.write(f"📊 **Total records with errors: {total_records_with_errors}**")
        
        labels = {'Baggage': '🧳',
                   'Passport': '🪪', 'Name': '👤', 'Visa': '🛂', 'Other': '🔧'}

        # 使用列显示每种错误类型的统计
        cols = st.columns(5)
        for i, (label, count) in enumerate(error_counts.items()):
            with cols[i]:
                st.metric(
                    label=f"{labels[label]} {label}",
                    value=count
                )
        st.markdown("---")
    except Exception as e:
        st.error(f"❌ Error loading error summary: {str(e)}")


def show_error_messages(db):
    """显示错误信息"""
    try:
        conn = sqlite3.connect(db.db_file)
        # 查询有错误的记录
        df = pd.read_sql_query("""
            SELECT hbnb_number, name, error_count, error_baggage, error_passport, error_name, error_visa, error_other, validated_at
            FROM hbpr_full_records 
            WHERE is_validated = 1 AND is_valid = 0 AND error_count > 0
            ORDER BY validated_at DESC, hbnb_number
        """, conn)
        conn.close()
        
        if df.empty:
            st.info("ℹ️ No error messages found. All processed records are valid!")
            return
        
        # 添加错误类型过滤下拉框
        error_types = ['All', 'Baggage', 'Passport', 'Name', 'Visa', 'Other']
        selected_error_type = st.selectbox(
            "🔍 Filter by Error Type:",
            error_types
        )
        
        # 根据选择的错误类型过滤记录
        if selected_error_type != 'All':
            error_field_map = {
                'Baggage': 'error_baggage',
                'Passport': 'error_passport', 
                'Name': 'error_name',
                'Visa': 'error_visa',
                'Other': 'error_other'
            }
            error_field = error_field_map[selected_error_type]
            df = df[df[error_field].notna() & (df[error_field] != '')]
            
            if df.empty:
                st.info(f"ℹ️ No {selected_error_type} error messages found!")
                return
        
        # 显示错误统计
        total_errors = len(df)
        st.write(f"**Found {total_errors} records with errors:**")
        
        # 分页显示错误信息
        items_per_page = 10
        total_pages = (total_errors + items_per_page - 1) // items_per_page
        if total_pages > 1:
            page = st.selectbox("Page:", range(1, total_pages + 1), key="error_page")
            start_idx = (page - 1) * items_per_page
            end_idx = min(start_idx + items_per_page, total_errors)
            page_df = df.iloc[start_idx:end_idx]
        else:
            page_df = df
        
        # 初始化session state用于跟踪哪个记录显示弹窗
        if 'show_popup_for' not in st.session_state:
            st.session_state.show_popup_for = None
        
        # 显示错误记录
        for _, row in page_df.iterrows():
            with st.expander(f"🚫 HBNB {row['hbnb_number']} - {row['name'] or 'Unknown'} ({row['error_count']} errors)"):
                st.write(f"**Validated at:** {row['validated_at']}")
                
                # 添加查看记录的弹出窗口
                col1, col2 = st.columns([3, 1])
                with col1:
                    st.write("**Quick Actions:**")
                with col2:
                    # 根据当前状态显示不同的按钮样式
                    is_viewing = st.session_state.show_popup_for == row['hbnb_number']
                    button_text = "❌ Close" if is_viewing else "👀 View"
                    
                    if st.button(button_text, key=f"view_{row['hbnb_number']}", use_container_width=True):
                        if is_viewing:
                            st.session_state.show_popup_for = None
                        else:
                            st.session_state.show_popup_for = row['hbnb_number']
                        st.rerun()
                
                # 如果当前记录需要显示弹窗，则显示弹窗内容
                if st.session_state.show_popup_for == row['hbnb_number']:
                    show_record_popup(db, row['hbnb_number'])
                
                # 解析并显示错误信息
                if selected_error_type == 'All':
                    # 显示所有错误类型
                    error_types = ['error_baggage', 'error_passport', 'error_name', 'error_visa', 'error_other']
                    error_labels = ['Baggage', 'Passport', 'Name', 'Visa', 'Other']
                    
                    for error_type, label in zip(error_types, error_labels):
                        if row[error_type] and row[error_type].strip():
                            # 使用markdown来支持换行显示
                            error_text = row[error_type].replace('\n', '<br>')
                            st.markdown(f"🔴 **{label}:** {error_text}", unsafe_allow_html=True)
                else:
                    # 只显示选中的错误类型
                    error_field_map = {
                        'Baggage': 'error_baggage',
                        'Passport': 'error_passport', 
                        'Name': 'error_name',
                        'Visa': 'error_visa',
                        'Other': 'error_other'
                    }
                    error_field = error_field_map[selected_error_type]
                    if row[error_field] and row[error_field].strip():
                        # 使用markdown来支持换行显示
                        error_text = row[error_field].replace('\n', '<br>')
                        st.markdown(f"🔴 **{selected_error_type}:** {error_text}", unsafe_allow_html=True)
        
        if total_pages > 1:
            st.info(f"Showing page {page} of {total_pages} ({len(page_df)} of {total_errors} records)")
    except Exception as e:
        st.error(f"❌ Error loading error messages: {str(e)}")


def show_record_popup(db, hbnb_number):
    """显示记录的弹出窗口"""
    try:
        # 获取原始内容
        content = db.get_hbpr_record(hbnb_number)
        # Apply dynamic font settings
        apply_font_settings()
        # 显示原始内容，使用全宽度
        st.text_area(
            "Raw Content:",
            content,
            height=400,
            disabled=True,
            key=f"popup_content_{hbnb_number}",
        )
    except Exception as e:
        st.error(f"❌ Error retrieving record: {str(e)}")


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
    
    # 乘客信息
    st.subheader("👤 Passenger Information")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("HBNB Number", data['hbnb_number'])
        st.metric("Boarding Number", data['boarding_number'] or "N/A")
        st.metric("PNR", data['PNR'] or "N/A")
    
    with col2:
        st.metric("Name", data['NAME'] or "N/A")
        st.metric("Passport Name", data['PSPT_NAME'] or "N/A")
        st.metric("Seat", data['SEAT'] or "N/A")
    
    with col3:
        st.metric("Class", data['CLASS'] or "N/A")
        st.metric("Destination", data['DESTINATION'] or "N/A")
        st.metric("FF Number", data['FF'] or "N/A")
    
    # 行李信息
    st.subheader("🧳 Baggage Information")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Checked Pieces", data['BAG_PIECE'])
        st.metric("Checked Weight", f"{data['BAG_WEIGHT']} kg")
    
    with col2:
        st.metric("EXPC Pieces", data['EXPC_PIECE'])
        st.metric("EXPC Weight", f"{data['EXPC_WEIGHT']} kg")
    
    with col3:
        st.metric("ASVC Pieces", data['ASVC_PIECE'])
        st.metric("FBA Pieces", data['FBA_PIECE'])
    
    with col4:
        st.metric("Allowance", data['BAG_ALLOWANCE'])
        st.metric("Flyer Benefit", data['FLYER_BENEFIT'])
    
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


def process_manual_input():
    """手动输入处理"""
    st.subheader("📄 Manual HBPR Input")
    
    # 搜索根目录中的数据库文件
    try:
        # 显示数据库文件夹建议
        if not os.path.exists("databases"):
            with st.expander("💡 Database Organization Suggestion"):
                st.write("Consider creating a 'databases' folder to organize your database files:")
                if st.button("📁 Create 'databases' folder"):
                    try:
                        os.makedirs("databases", exist_ok=True)
                        st.success("✅ 'databases' folder created!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"❌ Error creating folder: {str(e)}")
        
        # 获取当前选中的数据库
        selected_db_file = get_current_database()
        
        if not selected_db_file:
            st.error("❌ No database selected! Please select a database from the sidebar or build one first.")
            st.info("💡 Tip: Consider creating a 'databases' folder to organize your database files.")
            return
        
        # 将子标题和状态指示器放在同一行
        col1, col2 = st.columns([4, 1])
        
        with col1:
            st.markdown("### 🗄️ Database Selected")
            # 显示当前选中的数据库名称
            st.markdown(f"**Current Database:** `{os.path.basename(selected_db_file)}`")
        
        with col2:
            # 状态指示器
            try:
                temp_db = HbprDatabase(selected_db_file)
                flight_info = temp_db.get_flight_info()
                if flight_info:
                    st.markdown("✅")
                else:
                    st.markdown("⚠️")
            except:
                st.markdown("⚠️")
        
        # 使用选中的数据库
        db = HbprDatabase(selected_db_file)
        st.markdown("---")
        
        # 输入类型选择
        input_type = st.radio(
            "📝 Input Type:",
            ["Full HBPR Record", "Simple HBNB Record"],
            horizontal=True,
            help="Full HBPR Record: Complete HBPR content with passenger details\nSimple HBNB Record: Just HBNB number for placeholder"
        )
        
        if input_type == "Full HBPR Record":
            _handle_full_record_input(db)
        else:
            _handle_simple_record_input(db)
        
        # 显示记录列表区域
        _show_records_list(db)
    
    except Exception as e:
        st.error(f"❌ Error accessing databases: {str(e)}")
        st.info("💡 Please build a database first in the Database Management page.")


def _handle_full_record_input(db):
    """处理完整HBPR记录输入"""
    st.subheader("📄 Full HBPR Record Input")
    
    hbpr_content = st.text_area(
        "Paste full HBPR content here:",
        height=300,
        placeholder="Paste your complete HBPR record content here...\nExample: >HBPR: CA984/25JUL25*LAX,12345\n...",
        key="manual_input_hbpr_content"
    )
    
    # Add two buttons side by side
    col1, col2 = st.columns([3, 1])
    
    with col1:
        replace_clicked = st.button("🔍 Replace the Record", use_container_width=True)
    
    with col2:
        duplicate_clicked = st.button("📋 Create a Duplicate Record", use_container_width=True)
    
    if replace_clicked:
        _process_replace_record(db, hbpr_content)
    
    if duplicate_clicked:
        _process_duplicate_record(db, hbpr_content)


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


def _handle_simple_record_input(db):
    """处理简单HBNB记录输入"""
    st.subheader("🔢 Simple HBNB Record Input")
    
    hbnb_input = st.text_input(
        "HBNB Numbers:",
        placeholder="e.g., 400-410,412,415-420",
        help="Enter HBNB numbers to create simple records. Supports:\n• Single number: 400\n• Range: 400-410\n• Comma-separated list: 400,412,415\n• Mixed: 400-410,412,415-420"
    )
    
    # 解析HBNB输入
    hbnb_numbers = []
    if hbnb_input.strip():
        try:
            hbnb_numbers = parse_hbnb_input(hbnb_input)
            if not hbnb_numbers:
                st.warning("⚠️ No valid HBNB numbers found in input")
        except ValueError as e:
            st.error(f"❌ Invalid input format: {str(e)}")
    
    # 显示HBNB状态预览（仅显示前5个）
    if hbnb_numbers:
        st.subheader("📋 HBNB Status Preview")
        preview_numbers = hbnb_numbers[:5]
        for hbnb_num in preview_numbers:
            hbnb_exists = db.check_hbnb_exists(hbnb_num)
            if hbnb_exists['exists']:
                if hbnb_exists['full_record']:
                    st.error(f"❌ HBNB {hbnb_num}: Full record exists")
                else:
                    st.warning(f"⚠️ HBNB {hbnb_num}: Simple record exists")
            else:
                st.success(f"✅ HBNB {hbnb_num}: Available")
        
        if len(hbnb_numbers) > 5:
            st.info(f"ℹ️ ... and {len(hbnb_numbers) - 5} more HBNB numbers")
    
    # 创建简单记录的按钮
    if st.button("➕ Create Simple Records", use_container_width=True):
        _create_simple_records(db, hbnb_numbers)


def _create_simple_records(db, hbnb_numbers):
    """创建简单记录"""
    if not hbnb_numbers:
        st.warning("⚠️ Please enter valid HBNB numbers first")
        return
    
    try:
        # 获取当前数据库的flight_info
        flight_info = db.get_flight_info()
        
        # 显示处理前的状态信息
        st.subheader("📋 Processing Information")
        col1, col2 = st.columns(2)
        
        with col1:
            st.write("**Database Flight Info:**")
            if flight_info:
                st.write(f"Flight: {flight_info['flight_number']}")
                st.write(f"Date: {flight_info['flight_date']}")
            else:
                st.write("No flight info available")
        
        with col2:
            st.write(f"**HBNB Numbers to Process:** {len(hbnb_numbers)}")
        
        # 处理每个HBNB数字
        created_count = 0
        skipped_count = 0
        error_count = 0
        
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        for i, hbnb_num in enumerate(hbnb_numbers):
            status_text.text(f"Processing HBNB {hbnb_num}... ({i+1}/{len(hbnb_numbers)})")
            
            try:
                # 检查HBNB是否存在
                hbnb_exists = db.check_hbnb_exists(hbnb_num)
                
                if hbnb_exists['exists']:
                    if hbnb_exists['full_record']:
                        st.warning(f"⚠️ Skipped HBNB {hbnb_num}: Full record already exists")
                        skipped_count += 1
                    else:
                        st.info(f"ℹ️ Skipped HBNB {hbnb_num}: Simple record already exists")
                        skipped_count += 1
                else:
                    # 创建简单记录
                    record_line = f"HBPR *,{hbnb_num}"
                    db.create_simple_record(hbnb_num, record_line)
                    st.success(f"✅ Created simple record for HBNB {hbnb_num}")
                    created_count += 1
            
            except Exception as e:
                st.error(f"❌ Error processing HBNB {hbnb_num}: {str(e)}")
                error_count += 1
            
            # 更新进度条
            progress_bar.progress((i + 1) / len(hbnb_numbers))
        
        # 显示最终结果
        st.subheader("📊 Processing Summary")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Created", created_count, delta=f"+{created_count}")
        with col2:
            st.metric("Skipped", skipped_count)
        with col3:
            st.metric("Errors", error_count, delta=f"-{error_count}" if error_count > 0 else None)
        
        if created_count > 0:
            st.success(f"✅ Successfully created {created_count} simple records!")
            
            # 更新missing_numbers表
            _update_missing_numbers(db)
            
            # 设置刷新标志
            st.session_state.refresh_home = True
        
    except Exception as e:
        st.error(f"❌ Error creating simple records: {str(e)}")
        st.error(traceback.format_exc())


def _show_records_list(db):
    """显示记录列表区域"""
    st.markdown("---")
    st.subheader("📋 Records in Database")
    
    # 添加视图类型选择
    view_type = st.radio(
        "Select view type:",
        ["Simple Records", "Duplicate Records"],
        horizontal=True,
        help="Simple Records: Regular HBPR records\nDuplicate Records: Records with duplicates"
    )
    
    try:
        if view_type == "Simple Records":
            _show_simple_records_view(db)
        else:
            _show_duplicate_records_view(db)
    except Exception as e:
        st.error(f"❌ Error loading records: {str(e)}")


def _show_simple_records_view(db):
    """显示简单记录视图"""
    simple_records = db.get_simple_records()
    if simple_records:
        # 创建DataFrame显示简单记录
        simple_df = pd.DataFrame(simple_records)
        st.dataframe(simple_df, use_container_width=True, height=200)
        
        # 显示统计信息
        summary = db.get_record_summary()
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total Records", summary['total_records'])
        with col2:
            st.metric("Full Records", summary['full_records'])
        with col3:
            st.metric("Simple Records", summary['simple_records'])
        with col4:
            st.metric("Validated Records", summary['validated_records'])
    else:
        st.info("ℹ️ No simple records found in database.")


def _show_duplicate_records_view(db):
    """显示重复记录视图"""
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
                help="Select an HBNB number to view its duplicate records"
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