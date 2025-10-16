#!/usr/bin/env python3
"""
Database management page for HBPR UI - Database operations and maintenance
"""

import streamlit as st
from ui.database.management import show_database_management as show_db_management
from ui.database.hbpr import show_hbpr_operations
from ui.database.export import show_export_operations
from ui.database.simple import show_simple_records
from ui.database.sort import show_sort_records


def show_database_management():
    """Display the database management page"""
    st.markdown("<h3>🗄️ Database Management</h3>", unsafe_allow_html=True)
    tab1, tab2, tab3, tab4, tab5 = st.tabs(["📥 HBPR", "📋 Sort", "📤 Export", "🧻 Simple HBPR", "🗄️ Management"])
    with tab1:
        show_hbpr_operations()
    with tab2:
        show_sort_records()
    with tab3:
        show_export_operations()
    with tab4:
        show_simple_records()
    with tab5:
        show_db_management()