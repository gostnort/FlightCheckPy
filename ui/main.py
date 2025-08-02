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

def main():
    """主UI函数"""
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
    
    # 侧边栏导航
    st.sidebar.title("📋 Navigation")
    
    # Show logged in user info
    if 'username' in st.session_state:
        st.sidebar.markdown(f"👤 **Logged in as:** {st.session_state.username}")
    
    # Centralized database selection
    st.sidebar.markdown("---")
    # Get database files
    db_files = get_sorted_database_files(sort_by='creation_time', reverse=True)
    if db_files:
        # Create options with flight information
        db_options = []
        for db_file in db_files:
            try:
                temp_db = HbprDatabase(db_file)
                flight_info = temp_db.get_flight_info()
                if flight_info:
                    display_name = f"{os.path.basename(db_file)}"
                else:
                    display_name = f"Unknown Flight - {os.path.basename(db_file)}"
            except:
                display_name = f"Database - {os.path.basename(db_file)}"
            
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
    # Home page
    if st.sidebar.button("🏠 Home", use_container_width=True):
        st.session_state.current_page = "🏠 Home"    
    st.sidebar.markdown("---")
    # 导航链接
    if st.sidebar.button("🗄️ Database", use_container_width=True):
        st.session_state.current_page = "🗄️ Database"
    if st.sidebar.button("🔍 Process Records", use_container_width=True):
        st.session_state.current_page = "🔍 Process Records"
    if st.sidebar.button("📊 View Results", use_container_width=True):
        st.session_state.current_page = "📊 View Results"
    # 设置页
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
    
    # 根据当前页面显示内容
    current_page = st.session_state.current_page
    if current_page == "🏠 Home":
        # 只在主页显示标题
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