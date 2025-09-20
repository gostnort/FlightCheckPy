#!/usr/bin/env python3
"""
Database management page for HBPR UI - Database operations and maintenance
"""

import streamlit as st
import pandas as pd
import sqlite3
import os
import traceback
from send2trash import send2trash
from tkinter import filedialog
from scripts.hbpr_list_processor import HBPRProcessor
from scripts.clean_database_data import clean_database_data
from ui.common import (
    get_hbpr_database_client, 
    is_db_available, 
    get_database_name,
    trigger_auto_save
)


def show_database_management():
    """Display the database management page"""
    st.markdown("<h3>🗄️ Database Management</h3>", unsafe_allow_html=True)
    
    tab1, tab2, tab3 = st.tabs(
        ["➕ Create/Append from HBPR", "💾 Operations", "ℹ️ Info"]
    )

    with tab1:
        st.subheader("Upload HBPR List to Create or Append")
        uploaded_file = st.file_uploader(
            "Upload an HBPR List file (e.g., sample_hbpr_list.txt)",
            type=["txt"],
            help="This will process the file and load the data into the current in-memory database.",
        )
        
        if uploaded_file is not None:
            if st.button("Process File", use_container_width=True, type="primary"):
                file_content = uploaded_file.getvalue().decode("utf-8")
                
                with st.spinner("Processing file and loading data..."):
                    try:
                        db_client = get_hbpr_database_client()
                        if not db_client:
                            st.error("Database service is not available. Please log in again.")
                            return

                        conn = db_client.get_connection()
                        processor = HBPRProcessor(conn)
                        processor.process(file_content)
                        st.success("✅ HBPR data processed and loaded into the current in-memory database.")
                        
                        if trigger_auto_save():
                            st.toast("Database changes have been saved to disk.")
                        
                        st.rerun()
                    except Exception as e:
                        st.error(f"❌ Error processing file: {e}")

    with tab2:
        st.subheader("Database Operations")
        
        if not is_db_available():
            st.warning("⚠️ No database loaded. Please select one from the sidebar.")
        else:
            db_name = get_database_name()
            st.info(f"**Current Database:** `{db_name}`")

            col1, col2 = st.columns(2)
            with col1:
                if st.button("💾 Save to File", use_container_width=True, help="Persist in-memory changes to disk"):
                    if trigger_auto_save():
                        st.success(f"✅ Database `{db_name}` saved successfully.")
                    else:
                        st.error("❌ Failed to save database.")
            with col2:
                if st.button("🧹 Clean Database Data", use_container_width=True, help="Run data cleaning scripts"):
                    try:
                        db = get_hbpr_database_client()
                        with st.spinner("Cleaning database data..."):
                            clean_database_data(db.get_connection())
                        st.success("✅ Database cleaned successfully.")
                        if trigger_auto_save():
                            st.toast("💾 Changes saved to disk.")
                    except Exception as e:
                        st.error(f"❌ Error cleaning database: {e}")

    with tab3:
        st.subheader("Database Information")

        if not is_db_available():
            st.warning("⚠️ No database loaded to display information.")
        else:
            try:
                db = get_hbpr_database_client()
                stats = db.get_record_summary()
                
                col1, col2, col3, col4 = st.columns(4)
                col1.metric("Total Records", f"{stats.get('total_records', 0)}")
                col2.metric("Full Records", f"{stats.get('full_records', 0)}")
                col3.metric("Simple Records", f"{stats.get('simple_records', 0)}")
                col4.metric("Validated Records", f"{stats.get('validated_records', 0)}")

            except Exception as e:
                st.error(f"❌ Error fetching database info: {e}")

