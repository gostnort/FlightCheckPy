#!/usr/bin/env python3
"""
Add HBPRs tab for Process Records page - Add HBPR records with duplicate handling
"""

import streamlit as st
from ui.common import is_db_available, get_hbpr_database_client
from ui.process_records.add_edit_record import _process_replace_record
from scripts.hbpr_list_processor import HBPRProcessor


def show_add_hbprs_tab():
    """Show Add HBPRs tab - similar to Create from HBPR but handles duplicates"""
    st.subheader("➕ Add HBPRs")

    uploaded_file = st.file_uploader(
        "Upload HBPR List file to Add Records",
        type=["txt"],
        help="Upload HBPR list file. If HBNB exists, creates duplicate record. If not, creates new record.",
        key="add_hbprs_upload"
    )

    if uploaded_file is not None:
        if st.button("🚀 Process and Add HBPRs", use_container_width=True, type="primary"):
            process_and_add_hbprs(uploaded_file)


def process_and_add_hbprs(uploaded_file):
    """Process HBPR file and add records, handling duplicates"""
    try:
        db = get_hbpr_database_client()
        if not db:
            st.error("Database connection not available.")
            return

        file_content = uploaded_file.getvalue().decode("utf-8")

        with st.spinner("Processing HBPR file and adding records..."):
            # Parse HBPR content to get individual records
            conn = db.get_connection()
            processor = HBPRProcessor(conn)

            # Process the file content to extract individual HBPR records
            lines = file_content.split('\n')
            hbpr_records = []
            current_record = []

            for line in lines:
                line = line.strip()
                if line.startswith('>HBPR:'):
                    # Save previous record if exists
                    if current_record:
                        hbpr_records.append('\n'.join(current_record))
                        current_record = []
                if line:  # Only add non-empty lines
                    current_record.append(line)

            # Add the last record
            if current_record:
                hbpr_records.append('\n'.join(current_record))

            if not hbpr_records:
                st.warning("No valid HBPR records found in the file.")
                return

            added_count = 0
            duplicate_count = 0

            for hbpr_content in hbpr_records:
                try:
                    # Use the existing replace record logic which handles duplicates
                    _process_replace_record(db, hbpr_content)
                    added_count += 1
                except Exception as e:
                    st.warning(f"Failed to process record: {str(e)[:100]}...")
                    continue

            st.success(f"✅ Processed {len(hbpr_records)} HBPR records. Added/Updated: {added_count}")

    except Exception as e:
        st.error(f"❌ Error processing HBPR file: {str(e)}")
