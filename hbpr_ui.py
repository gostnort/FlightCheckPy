#!/usr/bin/env python3
"""
HBPR Processing Web UI using Streamlit - LEGACY FILE
This file has been migrated to the ui/ folder structure.
All functionality is now available through the organized UI modules.

For new development, use:
- ui/main.py - Main UI coordinator
- ui/process_records_page.py - Process Records functionality  
- ui/view_results_page.py - View Results functionality
- ui/database_page.py - Database Management
- ui/home_page.py - Home Page
- ui/settings_page.py - Settings
- ui/login_page.py - Authentication
- ui/common.py - Shared utilities

This file is kept for backward compatibility only.
"""

import streamlit as st


# Legacy functions for backward compatibility
# All functionality has been moved to ui/ folder structure

def show_process_records():
    """Legacy function - redirects to new UI structure"""
    st.warning("⚠️ Legacy function called. Please use ui/process_records_page.py")
    from ui.process_records_page import show_process_records as new_show_process_records
    new_show_process_records()


def show_view_results():
    """Legacy function - redirects to new UI structure"""
    st.warning("⚠️ Legacy function called. Please use ui/view_results_page.py")
    from ui.view_results_page import show_view_results as new_show_view_results
    new_show_view_results()


def main():
    """Legacy main function - redirects to new UI structure"""
    st.warning("⚠️ You are using the legacy hbpr_ui.py entry point.")
    st.info("💡 Please use 'streamlit run ui/main.py' or the new organized UI structure.")
    st.markdown("---")
    
    # Redirect to new main function
    from ui.main import main as new_main
    new_main()


if __name__ == "__main__":
    main()