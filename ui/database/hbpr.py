#!/usr/bin/env python3
"""
HBPR tab for Database page - HBPR file processing and database operations
"""

import streamlit as st
from ui.common import (
    get_hbpr_database_client,
    is_db_available,
    get_database_name,
    trigger_auto_save
)
from ui.process_records.process_all import start_processing_all_records


def show_hbpr_operations():
    """Show HBPR operations tab"""
    st.subheader("HBPR Operations")

    if not is_db_available():
        st.warning("⚠️ No database loaded. Please select one from the sidebar.")
        return

    db_name = get_database_name()
    st.info(f"**Current Database:** `{db_name}`")

    # HBPR operations buttons
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        if st.button("📥 Create from HBPR", use_container_width=True, help="Upload and process HBPR list file"):
            st.session_state.create_hbpr_triggered = True
    with col2:
        if st.button("🔄 Process Again", use_container_width=True, help="Run processing on existing records"):
            db = get_hbpr_database_client()
            if db:
                start_processing_all_records(db, None)
    with col3:
        if st.button("🧹 Erase Result", use_container_width=True, help="Clear all processing results"):
            db = get_hbpr_database_client()
            if db:
                from ui.process_records.process_all import erase_splited_records
                erase_splited_records(db)
    with col4:
        if st.button("💾 Save DB", use_container_width=True, help="Save database to disk"):
            if trigger_auto_save():
                st.success(f"✅ Database `{db_name}` saved successfully.")
            else:
                st.error("❌ Failed to save database.")

    # Handle Create from HBPR
    if st.session_state.get('create_hbpr_triggered', False):
        del st.session_state.create_hbpr_triggered
        show_create_from_hbpr()


def show_create_from_hbpr():
    """Handle Create from HBPR functionality with auto-processing"""
    st.subheader("📥 Create from HBPR")
    uploaded_file = st.file_uploader(
        "Upload an HBPR List file (e.g., sample_hbpr_list.txt)",
        type=["txt"],
        help="This will process the file and load the data into the current in-memory database.",
        key="hbpr_upload"
    )

    if uploaded_file is not None:
        file_content = uploaded_file.getvalue().decode("utf-8")

        with st.spinner("Processing file and loading data..."):
            try:
                db_client = get_hbpr_database_client()
                if not db_client:
                    st.error("Database service is not available. Please log in again.")
                    return
                conn = db_client.get_connection()
                from scripts.hbpr_list_processor import HBPRProcessor
                processor = HBPRProcessor(conn)
                processor.process(file_content)
                st.success("✅ HBPR data processed and loaded into the current in-memory database.")

                if trigger_auto_save():
                    st.toast("Database changes have been saved to disk.")

                # Auto-run processing after successful HBPR creation
                st.info("🔄 Auto-starting record processing...")
                start_processing_all_records(db_client, None)

            except Exception as e:
                st.error(f"❌ Error processing file: {e}")

