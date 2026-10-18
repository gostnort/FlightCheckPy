#!/usr/bin/env python3
import sqlite3
import tempfile

import streamlit as st
from pathlib import Path
from scripts.config_manager import get_config_value
from scripts.crypto_engine import encrypt_sqlite_payload, resolve_master_key, save_master_passphrase
from ui.common import (
    get_hbpr_database_client,
    get_database_name,
    trigger_auto_save,
    load_database
)
from scripts.hbpr_info_processor import CHbpr


def show_hbpr_operations():
    """显示HBPR操作界面"""
    pending_content = st.session_state.pop("pending_create_db_content", None)
    st.subheader("📥 HBPR Operations")
    # 显示当前数据库
    current_db = get_database_name()
    if current_db and current_db != "N/A" and current_db != "Error":
        st.info(f"📂 Current Database: **{current_db}**")
    else:
        st.warning("⚠️ No database loaded - select below or browse folders")
    # Action buttons
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("📤 Create New Database", use_container_width=True, help="Create a new database from an HBPR file"):
            st.session_state.show_create_db = True
    with col2:
        if st.button("🔄 Process All Records", use_container_width=True, help="Run CHbpr to process all records"):
            process_all_records() 
    with col3:
        if st.button("🧹 Clear Processed Results", use_container_width=True, help="Clear all processed results"):
            erase_processing_results()   
    # 处理创建新数据库
    if pending_content:
        create_db_from_content(pending_content)
    if st.session_state.get('show_create_db', False):
        create_database_from_file()


def process_all_records():
    """处理所有HBPR记录"""
    db = get_hbpr_database_client()
    if not db:
        st.error("❌ Database connection is not available.")
        return
    try:
        # 获取所有记录
        conn = db.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT hbnb_number FROM hbpr_full_records ORDER BY hbnb_number")
        records = [row[0] for row in cursor.fetchall()]
        if not records:
            st.info("ℹ️ No records found.")
            return
        # 创建进度条
        progress_bar = st.progress(0)
        status_text = st.empty()
        results_container = st.container()
        processed_count = 0
        valid_count = 0
        error_count = 0
        # Process records
        with st.spinner(f"🔄 Processing {len(records)} records..."):
            for i, hbnb_number in enumerate(records):
                try:
                    # 获取记录内容
                    content = db.get_hbpr_record(hbnb_number)
                    # 使用CHbpr处理
                    chbpr = CHbpr()
                    chbpr.run(content)
                    # 更新数据库
                    success = db.update_with_chbpr_results(chbpr)
                    if success:
                        processed_count += 1
                        # 只统计有BN号的记录
                        if chbpr.BoardingNumber > 0:
                            if chbpr.is_valid():
                                valid_count += 1
                            else:
                                error_count += 1
                        # 标记有未保存的更改
                        st.session_state.db_has_unsaved_changes = True
                    # 更新进度
                    progress = (i + 1) / len(records)
                    progress_bar.progress(progress)
                    status_text.text(f"Progress: {i + 1}/{len(records)} ({progress*100:.1f}%)")
                except Exception as e:
                    st.warning(f"⚠️ Error processing HBNB {hbnb_number}: {str(e)}")
        # Display results
        with results_container:
            st.success(f"🎉 Processing complete! Processed {processed_count} records.")
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Total Processed", processed_count)
            with col2:
                st.metric("Valid Records (with BN)", valid_count)
            with col3:
                st.metric("Error Records (with BN)", error_count)
        # Auto-save
        if trigger_auto_save():
            st.toast("✅ Database automatically saved")
    except Exception as e:
        st.error(f"❌ Processing error: {str(e)}")


def erase_processing_results():
    """清除所有处理结果"""
    db = get_hbpr_database_client()
    if not db:
        st.error("❌ Database connection is not available.")
        return
    # 确认对话框
    if not st.session_state.get('confirm_erase', False):
        st.warning("⚠️ This operation will clear all processing results. Click again to confirm.")
        st.session_state.confirm_erase = True
        return
    try:
        with st.spinner("🧹 Clearing processing results..."):
            success = db.erase_splited_records()
            if success:
                st.success("✅ Processing results cleared")
                st.info("ℹ️ All processed fields have been reset. Only HBNB numbers and raw contents are retained.")
                # Mark unsaved changes
                st.session_state.db_has_unsaved_changes = True
                # 保存更改
                if trigger_auto_save():
                    st.toast("✅ Changes saved")
                # Reset confirmation state
                st.session_state.confirm_erase = False
                st.rerun()
            else:
                st.error("❌ Failed to clear")
    except Exception as e:
        st.error(f"❌ Error: {str(e)}")


def create_database_from_file():
    """从HBPR列表文件创建数据库"""
    with st.expander("📤 Create New Database from HBPR File", expanded=True):
        uploaded_file = st.file_uploader(
            "Select HBPR file",
            type=["txt"],
            help="Upload an HBPR file (e.g., sample_hbpr.txt)",
            key="hbpr_uploader"
        )
        col1, col2 = st.columns(2)
        with col2:
            if st.button("❌ Cancel", use_container_width=True):
                st.session_state.show_create_db = False
                st.rerun()
        if uploaded_file is not None:
            file_content = uploaded_file.getvalue().decode("utf-8")
            with col1:
                if st.button("✅ Create Database", use_container_width=True, type="primary"):
                    if _encrypted_create_needs_password():
                        _ask_master_password(file_content)
                    else:
                        create_db_from_content(file_content)


def _encrypted_create_needs_password() -> bool:
    mode = get_config_value("db_preferences", "default_mode", "encrypted")
    if mode == "plain":
        return False
    try:
        return not resolve_master_key()
    except PermissionError:
        return True


@st.dialog("Master password")
def _ask_master_password(file_content: str):
    st.caption("This password encrypts the database. An encrypted database can only be opened with its original password. After the server restarts, the new password is used for later encryption and decryption.")
    passphrase = st.text_input("Master password", type="password", key="create_db_master_password")
    if st.button("Save and create", type="primary"):
        if not passphrase.strip():
            st.error("❌ Enter a master password.")
            return
        try:
            save_master_passphrase(passphrase)
        except (PermissionError, ValueError) as exc:
            st.error(f"❌ Master password was not saved: {exc}")
            return
        st.session_state.pending_create_db_content = file_content
        st.rerun()


def create_db_from_content(file_content: str):
    """从文件内容创建数据库"""
    try:
        # 解析航班号
        from scripts.hbpr_file_processor import parse_flight_id_from_content, HbprProcessor
        flight_id = parse_flight_id_from_content(file_content)
        if not flight_id:
            st.error("❌ Failed to parse flight ID from file content")
            return
        db_folder = Path(st.session_state.get("custom_db_folder", "databases"))
        db_folder.mkdir(parents=True, exist_ok=True)
        mode = get_config_value("db_preferences", "default_mode", "encrypted")
        encrypted = mode != "plain"
        suffix = ".db.enc" if encrypted else ".db"
        db_path = db_folder / f"{flight_id}{suffix}"
        other_path = db_folder / f"{flight_id}{'.db' if encrypted else '.db.enc'}"
        if db_path.exists() or other_path.exists():
            st.error(f"❌ Database {flight_id} already exists")
            return
        with st.spinner(f"Creating database {db_path.name}..."):
            with tempfile.TemporaryDirectory() as temp_dir:
                plain_path = Path(temp_dir) / f"{flight_id}.db"
                conn = sqlite3.connect(plain_path)
                processor = HbprProcessor(conn)
                processor.process(file_content)
                flight_data = processor.flight_data[flight_id]
                record_count = len(flight_data["hbnb_numbers"])
                conn.commit()
                conn.close()
                plain_bytes = plain_path.read_bytes()
            if encrypted:
                try:
                    master_key = resolve_master_key()
                except PermissionError as exc:
                    st.error(f"❌ Master key unavailable: {exc}")
                    return
                if not master_key:
                    st.error("❌ Master password is not set.")
                    return
                payload = encrypt_sqlite_payload(plain_bytes, master_key)
                temporary = db_path.with_name(db_path.name + ".writing")
                temporary.write_bytes(payload)
                temporary.replace(db_path)
            else:
                temporary = db_path.with_name(db_path.name + ".writing")
                temporary.write_bytes(plain_bytes)
                temporary.replace(db_path)
            st.success(f"✅ Database created successfully with {record_count} records!")
            if load_database(str(db_path)):
                # 清理状态
                st.session_state.show_create_db = False
                # Automatically process all records
                st.info("🔄 Automatically processing all records...")
                process_all_records()
            else:
                st.error("❌ Failed to load database to server")               
    except Exception as e:
        st.error(f"❌ Failed to create database: {str(e)}")
