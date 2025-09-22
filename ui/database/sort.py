#!/usr/bin/env python3
"""
Sort tab for Database page - Record sorting and filtering
"""

import streamlit as st


def show_sort_records():
    """Show sort records functionality"""
    st.subheader("Sort Records")
    from ui.process_records.sort_records import show_sort_records
    show_sort_records()
