#!/usr/bin/env python3
"""
Edit a Command tab for Process Records page - Edit individual commands
"""

import streamlit as st


def show_edit_command_tab():
    """Show Edit a Command tab - current Add/Edit Commands"""
    st.subheader("📋 Edit a Command")
    from ui.command_analysis_page import show_edit_data
    show_edit_data()
