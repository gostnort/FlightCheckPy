#!/usr/bin/env python3
"""
Add Commands tab for Process Records page - Import commands from files
"""

import streamlit as st


def show_add_commands_tab():
    """Show Add Commands tab - current Import Commands"""
    st.subheader("📝 Add Commands")
    from ui.command_analysis_page import show_import_commands
    show_import_commands()
