#!/usr/bin/env python3
"""
Database management page for HBPR UI - Database operations and maintenance
"""

import streamlit as st
from ui.database.hbpr import show_hbpr_operations
from ui.database.commands import show_commands_operations
from ui.database.export import show_export_operations
from ui.database.simple import show_simple_records
from ui.database.sort import show_sort_records


def show_database_management():
    """Display the database management page"""
    st.markdown("<h3>🗄️ Database Management</h3>", unsafe_allow_html=True)

    tab1, tab2, tab3, tab4, tab5 = st.tabs(["📥 HBPR", "📝 Commands", "📤 Export", "🧻 Simple", "📋 Sort"])

    with tab1:
        show_hbpr_operations()
    with tab2:
        show_commands_operations()
    with tab3:
        show_export_operations()
    with tab4:
        show_simple_records()
    with tab5:
        show_sort_records()
