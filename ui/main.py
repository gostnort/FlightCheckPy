#!/usr/bin/env python3
"""
Main UI coordinator for Flight Check python
"""

import streamlit as st
import os
import sys
from pathlib import Path
# Add project root to Python path
project_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(project_root))
# Project-specific imports (after path setup)
from ui.common import get_icon_base64, apply_global_settings, shutdown_db_server
from ui.login_page import show_login_page
from ui.home_page import show_home_page
from ui.database_page import show_database_management
from ui.settings_page import show_settings


def setup_navigation_highlighting():
    """设置导航高亮样式"""
    st.markdown("""
    <style>
    /* Target Streamlit's primary buttons in the sidebar */
    section[data-testid="stSidebar"] button[kind="primary"] {
        background-color: #e6ffe6 !important;
        color: #000000 !important;
        border: 2px solid #e6ffe6 !important;
        font-weight: bold !important;
    }
    section[data-testid="stSidebar"] button[kind="primary"]:hover {
        background-color: #98FB98 !important;
        border-color: #32CD32 !important;
        color: #000000 !important;
    }
    /* Also target buttons with the primary class */
    section[data-testid="stSidebar"] .stButton > button[data-testid="baseButton-primary"] {
        background-color: #90EE90 !important;
        color: #000000 !important;
        border: 2px solid #32CD32 !important;
        font-weight: bold !important;
    }
    section[data-testid="stSidebar"] .stButton > button[data-testid="baseButton-primary"]:hover {
        background-color: #98FB98 !important;
        border-color: #228B22 !important;
        color: #000000 !important;
    }
    /* Ensure main content area can scroll properly and show all content */
    .main .block-container {
        padding-bottom: 5rem !important;
        max-width: none !important;
    }
    /* Ensure proper height for main content */
    section[data-testid="stAppViewContainer"] > .main {
        min-height: 100vh !important;
        padding-bottom: 5rem !important;
    }
    /* Fix any potential height constraints */
    .stApp > header {
        background: transparent;
    }
    .stApp {
        overflow-y: auto !important;
    }
    </style>
    """, unsafe_allow_html=True)


def create_navigation_button(page_name, current_page, button_text):
    """创建导航按钮并处理高亮"""
    button_type = "primary" if current_page == page_name else "secondary"
    if st.sidebar.button(button_text, use_container_width=True, type=button_type):
        st.session_state.current_page = page_name
        st.rerun()


def main():
    """Main UI function"""
    st.set_page_config(
        page_title="Flight Check Py-0.63",
        page_icon="resources/fcp.ico",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    # Initialize session state
    if 'current_page' not in st.session_state:
        st.session_state.current_page = "🏠 Home"
    # Initialize settings
    if 'settings' not in st.session_state:
        st.session_state.settings = {
            'font_family': 'Courier New',
            'font_size_percent': 100,
            'auto_refresh': True
        }
    # Initialize file cleanup tracking
    if 'uploaded_file_path' not in st.session_state:
        st.session_state.uploaded_file_path = None
    if 'previous_page' not in st.session_state:
        st.session_state.previous_page = None
    # Check authentication
    if 'authenticated' not in st.session_state:
        st.session_state.authenticated = False
    # If not authenticated, show login page
    if not st.session_state.authenticated:
        show_login_page()
        return
    # Apply global settings
    apply_global_settings()
    # Add CSS for navigation highlighting
    setup_navigation_highlighting()
    # Sidebar navigation
    st.sidebar.title("📋 Navigation")
    
    # 使用简化的数据库选择器
    with st.sidebar:
        from ui.components.database_selector import render_sidebar_database_selector
        
        # 渲染数据库选择器
        render_sidebar_database_selector()
        
    st.sidebar.markdown("---")
    # Home page
    create_navigation_button("🏠 Home", st.session_state.current_page, "🏠 Home")
    # Navigation links
    create_navigation_button("🗄️ Database", st.session_state.current_page, "🗄️ Database")
    create_navigation_button("🔍 Process Records", st.session_state.current_page, "🔍 Process Records")
    create_navigation_button("📊 Excel Processor", st.session_state.current_page, "📊 Excel Processor")
    # Settings page
    st.sidebar.markdown("---")
    create_navigation_button("⚙️ Settings", st.session_state.current_page, "⚙️ Settings")
    # Logout button
    if st.sidebar.button("🚪 Logout", use_container_width=True, type="secondary"):
        # Clean up any uploaded files before logout
        if st.session_state.uploaded_file_path and os.path.exists(st.session_state.uploaded_file_path):
            try:
                os.remove(st.session_state.uploaded_file_path)
            except Exception:
                pass
        # Shutdown the database server for this user
        shutdown_db_server()
        # Clear session state
        st.session_state.authenticated = False
        st.session_state.username = None
        st.session_state.uploaded_file_path = None
        st.session_state.db_service_port = None
        st.session_state.db_service_host = None
        st.rerun()
    # Update previous page before creating navigation
    st.session_state.previous_page = st.session_state.current_page
    # Clean up uploaded file when navigating away from database page
    pages_with_uploads = ["🗄️ Database"]
    if (st.session_state.previous_page in pages_with_uploads and 
        st.session_state.current_page not in pages_with_uploads and 
        st.session_state.uploaded_file_path and 
        os.path.exists(st.session_state.uploaded_file_path)):
        try:
            os.remove(st.session_state.uploaded_file_path)
            st.session_state.uploaded_file_path = None
        except Exception:
            pass
    # Display content based on current page
    current_page = st.session_state.current_page
    if current_page == "🏠 Home":
        # Only show title on homepage
        st.markdown("""
        <div style="display: flex; align-items: center; gap: 10px;">
            <img src="data:image/x-icon;base64,{}" width="64" height="64">
            <h3 style="margin: 0;">Flight Check 0.63 --- Python</h3>
        </div>
        """.format(get_icon_base64("resources/fcp.ico")), unsafe_allow_html=True)
        st.markdown("---")
        show_home_page()
    elif current_page == "🗄️ Database":
        show_database_management()
    elif current_page == "🔍 Process Records":
        from ui.process_records_page import show_process_records
        show_process_records()
    elif current_page == "📊 Excel Processor":
        from ui.excel_processor_page import show_excel_processor
        show_excel_processor()
    elif current_page == "⚙️ Settings":
        show_settings()
if __name__ == "__main__":
    main()

