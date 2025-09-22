#!/usr/bin/env python3
"""
Timeline tab for Process Records page - Timeline view with HBPR and Commands history
"""

import streamlit as st
from ui.common import is_db_available, get_hbpr_database_client


def show_timeline_tab():
    """Show Timeline tab with radio buttons to switch between HBPR and Commands history"""
    st.subheader("📅 Timeline")

    # Radio buttons to switch between HBPR and Commands
    timeline_type = st.radio(
        "Select Timeline Type:",
        ["HBPR Records", "Commands"],
        horizontal=True,
        help="Choose which type of timeline to view"
    )

    if timeline_type == "HBPR Records":
        show_hbpr_timeline()
    else:
        show_commands_timeline()


def show_hbpr_timeline():
    """Show HBPR records timeline (duplicate records)"""
    st.markdown("**HBPR Records Timeline**")

    try:
        db = get_hbpr_database_client()
        if not db:
            st.error("Database connection not available.")
            return

        # Get duplicate records for timeline
        duplicate_hbnbs = db.get_all_duplicate_hbnbs()
        if not duplicate_hbnbs:
            st.info("ℹ️ No duplicate HBPR records found.")
            return

        selected_hbnb = st.selectbox(
            "Select HBNB to view timeline:",
            duplicate_hbnbs,
            help="Select an HBNB number to view its duplicate record timeline"
        )

        if selected_hbnb:
            # Get original and duplicate records
            original_record = db.get_hbpr_record(selected_hbnb)
            duplicate_records = db.get_duplicate_records(selected_hbnb)

            st.markdown(f"### 📅 Timeline for HBNB: **{selected_hbnb}**")

            # Display original record first
            with st.expander("Original Record", expanded=True):
                st.text_area("Content", original_record, height=200, disabled=True, key=f"original_{selected_hbnb}")

            # Display duplicate records
            for dup in duplicate_records:
                is_latest = dup.get('is_latest', False)
                with st.expander(f"Duplicate Record (ID: {dup['id']}) {'(Latest)' if is_latest else ''}", expanded=is_latest):
                    record_content = db.get_duplicate_record_content(dup['id'])
                    st.text_area(f"Content (Created: {dup['created_at']})", record_content, height=200, disabled=True, key=f"dup_{dup['id']}")

    except Exception as e:
        st.error(f"❌ Error loading HBPR timeline: {str(e)}")


def show_commands_timeline():
    """Show commands timeline - reuse existing functionality"""
    from ui.command_analysis_page import show_timeline_view
    show_timeline_view()
