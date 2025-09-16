#!/usr/bin/env python3
"""
Main UI coordinator for Flight Check python
"""

import streamlit as st
import os
import sys
import tkinter as tk
from tkinter import filedialog
from pathlib import Path
# Add project root to Python path
project_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(project_root))
# Project-specific imports (after path setup)
from ui.common import get_icon_base64, apply_global_settings
from ui.components.database_manager import create_database_selectbox
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
        page_title="Flight Check Py-0.62.1",
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
    # 使用增强的数据库选择器（自动加载到内存）
    custom_folder = st.session_state.get('custom_db_folder', None)
    
    # 在侧边栏中使用自定义的数据库选择器
    with st.sidebar:
        # 创建一个临时容器来包装选择器
        container = st.container()
        with container:
            selected_db_file, db_files = create_database_selectbox(
                label="💾 选择数据库:",
                key="global_db_select",
                default_index=0,
                custom_folder=custom_folder
            )
    
    if not selected_db_file:
        st.sidebar.warning("⚠️ 未找到数据库")
        st.sidebar.info("💡 请先创建数据库")
    # Store selected database in session state for all pages to use
    st.session_state.selected_database = selected_db_file
    st.session_state.available_databases = db_files if selected_db_file else []
    # Native Windows folder picker button and refresh button
    col1, col2, col3 = st.sidebar.columns([3,1,1])
    with col1:
        open_db_clicked = st.button("🧾 Open DB", use_container_width=True)
    with col3:
        refresh_clicked = st.button("🔄", use_container_width=True, help="Refresh all content")
    if open_db_clicked:
        try:
            # Create a root window and hide it
            root = tk.Tk()
            root.withdraw()
            root.wm_attributes('-topmost', 1)
            # Open Windows folder selection dialog
            folder_path = filedialog.askdirectory(
                title="Select Database Folder",
                initialdir=st.session_state.get('custom_db_folder', os.getcwd())
            )
            # Clean up the root window
            root.destroy()
            if folder_path:
                st.session_state.custom_db_folder = folder_path
                st.sidebar.success(f"📁 Selected: {os.path.basename(folder_path)}")
                st.rerun()
        except Exception as e:
            st.sidebar.error(f"❌ Error opening folder dialog: {str(e)}")
    # Handle refresh button click
    if refresh_clicked:
        st.rerun()
    # Show current custom folder if set
    current_custom_folder = st.session_state.get('custom_db_folder', '')
    if current_custom_folder:
        st.sidebar.caption(f"📁 Custom: {os.path.basename(current_custom_folder)}")
        if st.sidebar.button("🗑️ Clear Custom Folder", use_container_width=True):
            st.session_state.custom_db_folder = ''
            st.rerun()
    st.sidebar.markdown("---")
    # Home page
    create_navigation_button("🏠 Home", st.session_state.current_page, "🏠 Home")
    # Navigation links
    create_navigation_button("🗄️ Database", st.session_state.current_page, "🗄️ Database")
    create_navigation_button("🔍 Process Records", st.session_state.current_page, "🔍 Process Records")
    create_navigation_button("📋 Other Commands", st.session_state.current_page, "📋 Other Commands")
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
        st.session_state.authenticated = False
        st.session_state.username = None
        st.session_state.uploaded_file_path = None
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
            <h3 style="margin: 0;">Flight Check 0.62.1 --- Python</h3>
        </div>
        """.format(get_icon_base64("resources/fcp.ico")), unsafe_allow_html=True)
        st.markdown("---")
        show_home_page()
    elif current_page == "🗄️ Database":
        show_database_management()
    elif current_page == "🔍 Process Records":
        from ui.process_records_page import show_process_records
        show_process_records()
    elif current_page == "📋 Other Commands":
        from ui.command_analysis_page import show_command_analysis
        show_command_analysis()
    elif current_page == "📊 Excel Processor":
        from ui.excel_processor_page import show_excel_processor
        show_excel_processor()
    elif current_page == "⚙️ Settings":
        show_settings()
if __name__ == "__main__":
    main()

