#!/usr/bin/env python3
"""
Simple tab for Database page - Simple record management
"""

import streamlit as st


def show_simple_records():
    """Show simple records management"""
    st.subheader("Simple Records Management")
    from ui.process_records.simple_record import show_simple_record
    show_simple_record()
