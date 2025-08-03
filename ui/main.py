#!/usr/bin/env python3
"""
Main UI coordinator for HBPR Processing System
"""

import streamlit as st
import os
from ui.common import get_icon_base64, apply_global_settings
from ui.login_page import show_login_page
from ui.home_page import show_home_page
from ui.database_page import show_database_management
from ui.settings_page import show_settings  
from ui.common import get_sorted_database_files
from scripts.hbpr_info_processor import HbprDatabase
from tkinter import filedialog
import tkinter as tk

def main():
    """Main UI function"""
    st.set_page_config(
        page_title="HBPR Processing System",
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
    # Sidebar navigation
    st.sidebar.title("📋 Navigation")
    # Show logged in user info
    if 'username' in st.session_state:
        st.sidebar.markdown(f"👤 **Logged in as:** {st.session_state.username}")
    # Centralized database selection
    st.sidebar.markdown("---")
    # Get database files (including custom folder if set)
    custom_folder = st.session_state.get('custom_db_folder', None)
    db_files = get_sorted_database_files(sort_by='creation_time', reverse=True, custom_folder=custom_folder)
    if db_files:
        # Create options with flight information and location indicators
        db_options = []
        for db_file in db_files:
            try:
                temp_db = HbprDatabase(db_file)
                flight_info = temp_db.get_flight_info()
                base_name = os.path.basename(db_file)
                # Determine location indicator
                if custom_folder and db_file.startswith(custom_folder):
                    location_indicator = "📁"  # Custom folder
                elif db_file.startswith("databases/"):
                    location_indicator = "🏠"  # Default databases folder
                else:
                    location_indicator = "📄"  # Root directory 
                if flight_info:
                    display_name = f"{location_indicator} {base_name}"
                else:
                    display_name = f"{location_indicator} Unknown Flight - {base_name}"
            except Exception:
                base_name = os.path.basename(db_file)
                # Determine location indicator for error case
                if custom_folder and db_file.startswith(custom_folder):
                    location_indicator = "📁"
                elif db_file.startswith("databases/"):
                    location_indicator = "🏠"
                else:
                    location_indicator = "📄"
                display_name = f"{location_indicator} Database - {base_name}"
            
            db_options.append((display_name, db_file))
        # Sidebar selectbox
        selected_db_display = st.sidebar.selectbox(
            "Select Database:",
            options=[opt[0] for opt in db_options],
            index=0,
            key="global_db_select"
        )
        # Get selected database file
        selected_db_file = None
        for display_name, db_file in db_options:
            if display_name == selected_db_display:
                selected_db_file = db_file
                break
    else:
        selected_db_file = None
        st.sidebar.warning("⚠️ No databases found")
        st.sidebar.info("💡 Create a database first")
    # Store selected database in session state for all pages to use
    st.session_state.selected_database = selected_db_file
    st.session_state.available_databases = db_files
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
    if st.sidebar.button("🏠 Home", use_container_width=True):
        st.session_state.current_page = "🏠 Home"    
    # Navigation links
    if st.sidebar.button("🗄️ Database", use_container_width=True):
        st.session_state.current_page = "🗄️ Database"
    if st.sidebar.button("🔍 Process Records", use_container_width=True):
        st.session_state.current_page = "🔍 Process Records"
    if st.sidebar.button("📊 View Results", use_container_width=True):
        st.session_state.current_page = "📊 View Results"
    # Settings page
    st.sidebar.markdown("---")
    if st.sidebar.button("⚙️ Settings", use_container_width=True):
        st.session_state.current_page = "⚙️ Settings"
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
    # Clean up uploaded file when navigating away from database page
    if (st.session_state.previous_page == "🗄️ Database" and 
        st.session_state.current_page != "🗄️ Database" and 
        st.session_state.uploaded_file_path and 
        os.path.exists(st.session_state.uploaded_file_path)):
        try:
            os.remove(st.session_state.uploaded_file_path)
            st.session_state.uploaded_file_path = None
        except Exception:
            pass
    # Update previous page
    st.session_state.previous_page = st.session_state.current_page
    # Display content based on current page
    current_page = st.session_state.current_page
    if current_page == "🏠 Home":
        # Only show title on homepage
        st.markdown("""
        <div style="display: flex; align-items: center; gap: 10px;">
            <img src="data:image/x-icon;base64,{}" width="128" height="128">
            <h3 style="margin: 0;">Flight Check 0.61 --- Python</h3>
        </div>
        """.format(get_icon_base64("resources/fcp.ico")), unsafe_allow_html=True)
        st.markdown("---")
        show_home_page()
    elif current_page == "🗄️ Database":
        show_database_management()
    elif current_page == "🔍 Process Records":
        from ui.process_records_page import show_process_records
        show_process_records()
    elif current_page == "📊 View Results":
        from ui.view_results_page import show_view_results
        show_view_results()
    elif current_page == "⚙️ Settings":
        show_settings()


if __name__ == "__main__":
    main()