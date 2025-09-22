#!/usr/bin/env python3
"""
Database management page for HBPR UI - Database operations and maintenance
"""

import streamlit as st
from ui.database.operations import show_database_operations
from ui.database.simple import show_simple_records
from ui.database.sort import show_sort_records


def show_database_management():
    """Display the database management page"""
    st.markdown("<h3>🗄️ Database Management</h3>", unsafe_allow_html=True)

    tab1, tab2, tab3 = st.tabs(["💾 Operations", "🧻 Simple", "📋 Sort"])

    with tab1:
        show_database_operations()
    with tab2:
        show_simple_records()
    with tab3:
        show_sort_records()
