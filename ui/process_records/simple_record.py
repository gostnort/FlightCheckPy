#!/usr/bin/env python3
"""
Simple Record functionality for HBPR UI - Simple HBNB record creation and management
"""

import streamlit as st
import pandas as pd
from scripts.hbpr_info_processor import HbprDatabase
from ui.common import parse_hbnb_input, get_current_database


def show_simple_record():
    """简单记录处理""" 
    # 搜索根目录中的数据库文件
    try:
        # 获取当前选中的数据库
        selected_db_file = get_current_database()
        if not selected_db_file:
            st.error("❌ No database selected! Please select a database from the sidebar or build one first.")
            st.info("💡 Tip: Consider creating a 'databases' folder to organize your database files.")
            return
        # 使用选中的数据库
        db = HbprDatabase(selected_db_file)
        # 只保留简单HBNB记录功能
        _handle_simple_record_input(db)
        # 显示记录列表区域 - 只显示简单记录视图
        _show_simple_records_only(db)
    except Exception as e:
        st.error(f"❌ Error accessing databases: {str(e)}")
        st.info("💡 Please build a database first in the Database Management page.")


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


def _show_simple_records_only(db):
    """显示简单记录列表区域（仅用于简单记录标签页）"""
    st.subheader("📋 Simple Records in Database")
    try:
        _show_simple_records_view(db)
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


def _update_missing_numbers(db):
    """更新missing_numbers表"""
    try:
        db.update_missing_numbers_table()
        st.info("🔄 Updated missing numbers table")
    except Exception as e:
        st.warning(f"⚠️ Warning: Could not update missing numbers table: {str(e)}")

