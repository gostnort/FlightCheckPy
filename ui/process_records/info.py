#!/usr/bin/env python3
"""
Info tab for Process Records page - Error display only
"""

import streamlit as st
from ui.common import is_db_available, get_hbpr_database_client
from ui.process_records.process_all import show_error_summary, show_error_messages


def show_info_tab():
    """Show the Info tab with error display only (no buttons)"""
    st.subheader("ℹ️ Processing Information")

    if not is_db_available():
        st.warning("⚠️ Please select a database from the sidebar to begin.")
        return

    try:
        db = get_hbpr_database_client()
        if not db:
            st.error("❌ Database connection is not available.")
            return

        # Show error summary and error messages without buttons
        show_error_summary(db)
        show_error_messages(db)

    except Exception as e:
        st.error(f"❌ Error accessing database: {str(e)}")
