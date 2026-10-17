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
from ui.common import get_icon_base64, apply_global_settings, logout_current_user
from ui.login_page import show_login_page
from ui.style_loader import load_custom_css


def setup_navigation_highlighting():
    """设置导航高亮样式（已抽离至 resources/styles/main.css）"""
    load_custom_css()


def create_navigation_button(page_name, current_page, button_text):
    """创建导航按钮并处理高亮"""
    button_type = "primary" if current_page == page_name else "secondary"
    if st.sidebar.button(button_text, use_container_width=True, type=button_type):
        st.session_state.current_page = page_name
        st.rerun()


def main():
    """Main UI function"""
    st.set_page_config(
        page_title="Flight Check Py-0.6.4",
        page_icon="resources/fcp.ico",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    # Initialize session state
    if "current_page" not in st.session_state:
        st.session_state.current_page = "🏠 Home"
    # Initialize settings
    if "settings" not in st.session_state:
        st.session_state.settings = {
            "font_family": "Courier New",
            "font_size_percent": 100,
            "auto_refresh": True,
        }
    # Initialize file cleanup tracking
    if "uploaded_file_path" not in st.session_state:
        st.session_state.uploaded_file_path = None
    if "previous_page" not in st.session_state:
        st.session_state.previous_page = None
    # Check authentication
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
    # If not authenticated, show login page
    if not st.session_state.authenticated:
        show_login_page()
        return
    # =============================================================================
    #           LAZY LOADING: Import pages only after authentication
    # =============================================================================
    from ui.home_page import show_home_page
    from ui.database_page import show_database_management
    from ui.settings_page import show_settings
    from ui.process_records_page import show_process_records
    from ui.emd_summary_page import show_emd_summary
    from ui.components.database_selector import render_sidebar_database_selector
    # Apply global settings
    apply_global_settings()
    # Add CSS for navigation highlighting
    setup_navigation_highlighting()
    # Sidebar navigation
    st.sidebar.title("📋 Navigation")
    # 使用简化的数据库选择器
    with st.sidebar:
        # 渲染数据库选择器
        render_sidebar_database_selector()
    st.sidebar.markdown("---")
    # Home page
    create_navigation_button("🏠 Home", st.session_state.current_page, "🏠 Home")
    # Navigation links
    create_navigation_button("🗄️ Database", st.session_state.current_page, "🗄️ Database")
    create_navigation_button(
        "🔍 Process Records", st.session_state.current_page, "🔍 Process Records"
    )
    create_navigation_button(
        "📊 EMD Summary", st.session_state.current_page, "📊 EMD Summary"
    )
    # Settings page
    st.sidebar.markdown("---")
    create_navigation_button("⚙️ Settings", st.session_state.current_page, "⚙️ Settings")
    # Logout button - 简化的登出逻辑
    if st.sidebar.button("🚪 Logout", use_container_width=True, type="secondary"):
        # Clean up any uploaded files before logout
        if st.session_state.uploaded_file_path and os.path.exists(
            st.session_state.uploaded_file_path
        ):
            try:
                os.remove(st.session_state.uploaded_file_path)
            except Exception:
                pass
        # 登出当前用户
        logout_current_user()
        # 注意：不再自动关闭服务器，让服务器持续运行
        # 用户可以通过登录页的服务器控制按钮管理服务器
        # Clear session state
        st.session_state.authenticated = False
        st.session_state.username = None
        st.session_state.uploaded_file_path = None
        st.session_state.db_service_port = None
        st.session_state.db_service_host = None
        if "last_username" in st.session_state:
            del st.session_state.last_username
        st.rerun()
    # Update previous page before creating navigation
    st.session_state.previous_page = st.session_state.current_page
    # Clean up uploaded file when navigating away from database page
    pages_with_uploads = ["🗄️ Database"]
    if (
        st.session_state.previous_page in pages_with_uploads
        and st.session_state.current_page not in pages_with_uploads
        and st.session_state.uploaded_file_path
        and os.path.exists(st.session_state.uploaded_file_path)
    ):
        try:
            os.remove(st.session_state.uploaded_file_path)
            st.session_state.uploaded_file_path = None
        except Exception:
            pass
    # Display content based on current page
    current_page = st.session_state.current_page
    if current_page == "🏠 Home":
        # Only show title on homepage
        st.markdown(
            """
        <div style="display: flex; align-items: center; gap: 10px;">
            <img src="data:image/x-icon;base64,{}" width="64" height="64">
            <h3 style="margin: 0;">Flight Check 0.6.4 --- Python</h3>
        </div>
        """.format(get_icon_base64("resources/fcp.ico")),
            unsafe_allow_html=True,
        )
        st.markdown("---")
        show_home_page()
    elif current_page == "🗄️ Database":
        show_database_management()
    elif current_page == "🔍 Process Records":
        show_process_records()
    elif current_page == "📊 EMD Summary":
        show_emd_summary()
    elif current_page == "⚙️ Settings":
        show_settings()


if __name__ == "__main__":
    main()

