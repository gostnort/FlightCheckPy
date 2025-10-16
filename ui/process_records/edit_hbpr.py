#!/usr/bin/env python3
"""
Edit HBPR Records tab for Process Records page - Edit individual HBPR records with duplicate management
"""

import streamlit as st
import pandas as pd
import re
from scripts.record_processor import process_hbpr_record
from scripts.pr_processor import (
    validate_pr_content,
    convert_pr_to_hbpr
)
from scripts.data_cleaner import clean_text_for_input
from ui.common import (
    get_hbpr_database_client,
    is_db_available
)


def select_hbpr_record(db, selection_label="👀 View Record 🧺🧺🧺🧺 Sorting by:"):
    """
    共享函数用于按各种条件选择HBPR记录
    返回选定的HBNB号码或None（如果未进行选择）
    """
    conn = db.get_connection()
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

    if not all_records:
        st.warning("⚠️ No HBPR records found in database.")
        return None

    # 选择记录的方式
    selection_method = st.radio(
        selection_label,
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
                return None
        else:
            st.warning("⚠️ No processed records found. Please process records first.")
            return None

    elif selection_method == "Seat":
        # 座位选择（按行号从小到大，然后按座位号A-Z排序）
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
                return None
        else:
            st.warning("⚠️ No processed records found. Please process records first.")
            return None

    elif selection_method == "Name":
        # 姓名选择（按字母A-Z排序）
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
                return None
        else:
            st.warning("⚠️ No processed records found. Please process records first.")
            return None

    elif selection_method == "TKNE":
        # TKNE选择
        if processed_records:
            # 获取TKNE数据
            conn = db.get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT hbnb_number, tkne
                FROM hbpr_full_records
                WHERE is_validated = 1 AND tkne IS NOT NULL AND tkne != ''
                ORDER BY tkne
            """)
            tkne_records = cursor.fetchall()
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
                return None
        else:
            st.warning("⚠️ No processed records found. Please process records first.")
            return None

    return selected_record


def apply_font_settings():
    """从会话状态应用动态字体设置"""
    # 从会话状态获取字体设置
    font_family = st.session_state.get('settings', {}).get('font_family', 'Courier New')
    font_size_percent = st.session_state.get('settings', {}).get('font_size_percent', 100)
    # 计算字体大小（假设默认值为14px）
    font_size_px = int(14 * font_size_percent / 100)
    # 使用CSS应用字体设置
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


def _handle_record_input(db, content, is_duplicate=False):
    """
    处理记录输入（UI层）- 先检测PR并转换，然后处理HBPR
    参数:
        db: 数据库实例
        content: 输入内容（可能是PR或HBPR）
        is_duplicate: 是否创建重复记录
    返回:
        dict: {'success': bool, 'message': str, 'hbnb_number': int or None}
    """
    result = {
        'success': False,
        'message': '',
        'hbnb_number': None
    }
    if not content.strip():
        result['message'] = "⚠️ Please enter content first."
        return result
    # 清理内容
    cleaned_content = clean_text_for_input(content)
    # 第一步：检测是否为PR命令
    pr_validation = validate_pr_content(cleaned_content)
    if pr_validation['is_pr_command']:
        # 这是PR命令，需要转换
        if not pr_validation['is_valid']:
            result['message'] = f"❌ PR Command Validation Failed: {'; '.join(pr_validation['errors'])}"
            return result
        st.info("🔄 Detected PR command, converting to HBPR format...")
        # 转换PR到HBPR
        conversion_result = convert_pr_to_hbpr(cleaned_content, db)
        if not conversion_result['success']:
            result['message'] = f"❌ PR Conversion Failed: {conversion_result['error']}"
            return result
        # 转换成功，使用转换后的HBPR内容
        hbpr_content = conversion_result['converted_content']
        matched_hbnb = conversion_result['hbnb_number']
        st.success(f"✅ PR converted to HBPR format (HBNB {matched_hbnb})")
        st.info("ℹ️ Using original HBPR header from database")
        # 使用转换后的HBPR内容
        cleaned_content = hbpr_content
    # 第二步：处理HBPR记录（无论是原始HBPR还是转换后的HBPR）
    return process_hbpr_record(db, cleaned_content, is_duplicate=is_duplicate)


def _process_replace_record(db, content):
    """
    处理记录替换 - 带结果处理的_handle_record_input包装器
    """
    result = _handle_record_input(db, content, is_duplicate=False)
    if result['success']:
        st.success(result['message'])
        st.rerun()
    else:
        st.error(result['message'])


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
        'Record ID': 0,  # 使用0表示原始记录以保持整数类型
        'Created At': 'Original Record'
    })
    # 添加重复记录（按创建时间排序）
    for dup in duplicate_records:
        display_data.append({
            'Type': 'Duplicate',
            'Record ID': int(dup['id']),  # 确保整数类型
            'Created At': dup['created_at']
        })
    # 显示DataFrame
    if display_data:
        records_df = pd.DataFrame(display_data)
        # 确保正确的数据类型
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


def show_edit_hbpr_tab():
    """显示编辑HBPR标签页 - 支持替换和重复记录管理"""
    st.subheader("✏️ Edit HBPR Records")

    if not is_db_available():
        st.warning("⚠️ Please select a database from the sidebar to begin.")
        return

    try:
        db = get_hbpr_database_client()
        if not db:
            st.error("❌ Database connection is not available.")
            return

        # 创建标签页来分离功能
        tab1, tab2 = st.tabs(["✏️ Edit Record", "📋 Manage Duplicates"])

        with tab1:
            # 使用共享记录选择函数
            selected_record = select_hbpr_record(db)

            # 显示记录预览和编辑界面
            if selected_record:
                try:
                    content = db.get_hbpr_record(selected_record)
                    # 应用动态字体设置
                    apply_font_settings()
                    edited_content = st.text_area(
                        "Raw Content:",
                        content,
                        height=300,
                        disabled=False,
                        key=f"edit_content_{selected_record}"
                    )
                    # 添加替换和重复记录按钮
                    col1, col2 = st.columns([3, 2])
                    with col1:
                        if st.button("🔍 Replace the Record", use_container_width=True, key=f"replace_{selected_record}"):
                            _process_replace_record(db, edited_content)
                    with col2:
                        if st.button("📋 Create Duplicate", use_container_width=True, key=f"duplicate_{selected_record}"):
                            result = _handle_record_input(db, edited_content, is_duplicate=True)
                            if result['success']:
                                st.success(result['message'])
                                st.rerun()
                            else:
                                st.error(result['message'])
                except Exception as e:
                    st.error(f"❌ Error retrieving record: {str(e)}")

        with tab2:
            st.subheader("📋 Duplicate Records Management")
            _show_duplicate_records_section(db)

    except Exception as e:
        st.error(f"❌ Error accessing database: {str(e)}")
