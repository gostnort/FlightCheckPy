#!/usr/bin/env python3
"""
Edit a HBPR tab for Process Records page - Edit individual HBPR records
"""

import streamlit as st
import re
from ui.common import is_db_available, get_hbpr_database_client
from ui.process_records.add_edit_record import _process_replace_record, apply_font_settings


def show_edit_hbpr_tab():
    """Show Edit a HBPR tab - current Add/Edit functionality without duplicate records section"""
    st.subheader("✏️ Edit a HBPR")
    show_add_edit_record_without_duplicates()


def show_add_edit_record_without_duplicates():
    """Modified version of show_add_edit_record without the duplicate records section"""
    if not is_db_available():
        st.warning("⚠️ Please select a database from the sidebar to begin.")
        return

    try:
        db = get_hbpr_database_client()
        if not db:
            st.error("❌ Database connection is not available.")
            return

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
                edited_content = st.text_area("Raw Content:", content, height=300, disabled=False, key=f"edit_content_{selected_record}")
                # 添加替换记录按钮
                if st.button("🔍 Replace the Record", use_container_width=True, key=f"replace_{selected_record}"):
                    _process_replace_record(db, edited_content)
            except Exception as e:
                st.error(f"❌ Error retrieving record: {str(e)}")

    except Exception as e:
        st.error(f"❌ Error accessing database: {str(e)}")
