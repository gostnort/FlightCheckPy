#!/usr/bin/env python3
"""
HBPR tab for Database page - HBPR file processing and database operations
"""

import os
import sqlite3
import streamlit as st
from scripts.hbpr_info_processor import CHbpr
from scripts.hbpr_list_processor import HBPRProcessor, parse_flight_id_from_content
from ui.common import (
    get_hbpr_database_client,
    is_db_available,
    get_database_name,
    trigger_auto_save,
    load_database,
)


def start_processing_all_records(db, batch_size):
    """开始处理所有记录"""
    try:
        # 获取所有记录（内存连接）
        conn = db.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT hbnb_number FROM hbpr_full_records ORDER BY hbnb_number")
        records = [row[0] for row in cursor.fetchall()]
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
                        # 只有有BN号的记录才计入错误统计
                        if chbpr.BoardingNumber > 0:
                            if chbpr.is_valid():
                                valid_count += 1
                            else:
                                error_count += 1
                        else:
                            # 无BN号的记录标记为已处理但不计入错误统计
                            st.write(f"ℹ️ HBNB {hbnb_number}: No boarding number, processed but not counted in error stats")
                except Exception:
                    # 静默处理错误，不显示具体错误信息
                    pass
        # 显示结果总结
        with results_container:
            st.success(f"🎉 Processed {processed_count} records")
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Total Processed", processed_count)
            with col2:
                st.metric("Valid Records (with BN)", valid_count)
            with col3:
                st.metric("Records with Errors (with BN)", error_count)
        # 自动刷新页面以显示新的错误信息
        st.rerun()
    except Exception as e:
        st.error(f"❌ Processing error: {str(e)}")


def erase_splited_records(db):
    """清除所有处理结果，重置hbpr_full_records表中的处理字段"""
    try:
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
    except Exception as e:
        st.error(f"❌ Error during cleanup: {str(e)}")


def show_hbpr_operations():
    """Show HBPR operations tab"""
    st.subheader("HBPR Operations")
    if not is_db_available():
        st.warning("⚠️ No database loaded. Please select one from the sidebar.")
        return
    db_name = get_database_name()
    st.info(f"Current Database: ***{db_name}***")
    # HBPR operations buttons
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        if st.button("📥 Create from HBPR", use_container_width=True, help="Build a new database from HBPR list file"):
            st.session_state.create_hbpr_triggered = True
    with col2:
        if st.button("🔄 Process Again", use_container_width=True, help="Run processing on existing records"):
            db = get_hbpr_database_client()
            if db:
                start_processing_all_records(db, None)
    with col3:
        if st.button("🧹 Erase Processed Results", use_container_width=True, help="Clear all processing results"):
            db = get_hbpr_database_client()
            if db:
                erase_splited_records(db)
    with col4:
        if st.button("💾 Save DB", use_container_width=True, help="Save database to disk"):
            if trigger_auto_save():
                st.success(f"✅ Database `{db_name}` saved successfully.")
            else:
                st.error("❌ Failed to save database.")
    # Handle Create from HBPR
    if st.session_state.get('create_hbpr_triggered', False):
        # We don't reset the trigger here, but in the component, 
        # to allow it to persist across reruns until the upload is complete or cancelled.
        show_create_from_hbpr()


def show_create_from_hbpr():
    """Handle Create from HBPR functionality with auto-processing"""
    st.subheader("📥 Create from HBPR")
    uploaded_file = st.file_uploader(
        "Upload an HBPR List file (e.g., sample_hbpr_list.txt)",
        type=["txt"],
        help="This will create a new database, load it, process the file, and auto-validate.",
        key="hbpr_upload"
    )

    if uploaded_file is not None:
        file_content = uploaded_file.getvalue().decode("utf-8")
        
        with st.spinner("Creating new database from file..."):
            try:
                # 1. Parse flight ID to name the new database
                flight_id = parse_flight_id_from_content(file_content)
                if not flight_id:
                    st.error("❌ Could not determine Flight ID from file content. Cannot create database.")
                    return

                db_folder = "databases"
                os.makedirs(db_folder, exist_ok=True)
                new_db_path = os.path.join(db_folder, f"{flight_id}.db")

                if os.path.exists(new_db_path):
                    st.warning(f"⚠️ Database '{new_db_path}' already exists. Overwriting is not implemented. Please remove it manually if you want to re-create it.")
                    return

                # 2. Create a new empty database file locally
                conn = sqlite3.connect(new_db_path)
                conn.close()
                st.info(f"📄 Created new database file: {new_db_path}")

                # 3. Load the new (empty) database into the remote server
                if not load_database(new_db_path):
                    st.error("❌ Failed to load the new database into the server.")
                    os.remove(new_db_path) # Clean up empty file
                    return
                st.info(f"🧠 Loaded '{new_db_path}' into memory.")
                
                # 4. Process the HBPR file content into the now-loaded database
                db_client = get_hbpr_database_client()
                if not db_client:
                    st.error("Database service is not available. Please log in again.")
                    return
                
                conn = db_client.get_connection()
                processor = HBPRProcessor(conn)
                processor.process(file_content)
                st.success("✅ HBPR data processed and loaded into the current in-memory database.")

                # 5. Save the populated in-memory database back to the file
                if trigger_auto_save():
                    st.toast("Database changes have been saved to disk.")
                else:
                    st.error("Failed to save processed data to disk.")

                # 6. Auto-run processing after successful HBPR creation
                st.info("🔄 Auto-starting record processing...")
                start_processing_all_records(db_client, None)

            except Exception as e:
                st.error(f"❌ Error processing file: {e}")
            finally:
                # Reset the trigger to hide the uploader and prevent re-running on refresh
                st.session_state.create_hbpr_triggered = False
                st.rerun()

