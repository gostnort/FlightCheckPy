#!/usr/bin/env python3
"""
Settings page for HBPR UI - System configuration
"""

import streamlit as st
from scripts.config_manager import load_app_config, save_app_config


def show_settings():
    """显示设置页面"""
    st.header("⚙️ Settings")
    cfg = load_app_config()
    ui_cfg = cfg.get("ui_settings", {})
    # Initialize settings in session state from app_config.toml
    if 'settings' not in st.session_state:
        st.session_state.settings = {
            'theme': ui_cfg.get('theme', 'Auto'),
            'font_family': ui_cfg.get('font_family', 'Courier New'),
            'font_size_percent': ui_cfg.get('font_size_percent', 100),
            'show_debug': ui_cfg.get('show_debug', False),
            'auto_refresh': True
        }
    tab1, tab2 = st.tabs(["🎨 UI Settings", "📋 About"])
    with tab1:
        st.subheader("📝 Raw Content Font Settings")
        st.caption("💡 Dark Mode: Menu(...) → Settings → Choose app theme 🌔 for the Dark Mode 🌚")
        # Font family selection
        font_family = st.selectbox(
            "Font Family for Data:",
            ["Courier New", "Arial", "Times New Roman", "Consolas", "Monaco"],
            index=["Courier New", "Arial", "Times New Roman", "Consolas", "Monaco"].index(
                st.session_state.settings.get('font_family', 'Courier New')
            ),
            key="font_family_select"
        )
        # Update font family immediately when changed
        if font_family != st.session_state.settings.get('font_family'):
            st.session_state.settings['font_family'] = font_family
        # Font size percentage
        font_size_percent = st.slider(
            "Font Size for Data (% of default):",
            min_value=50,
            max_value=200,
            value=st.session_state.settings.get('font_size_percent', 100),
            step=10,
            help="Adjust font size for Raw Content and data tables as a percentage of the default size",
            key="font_size_slider"
        )
        # Update font size immediately when changed
        if font_size_percent != st.session_state.settings.get('font_size_percent'):
            st.session_state.settings['font_size_percent'] = font_size_percent
        # Save settings
        if st.button("💾 Save Settings", type="primary"):
            st.session_state.settings.update({
                'font_family': font_family,
                'font_size_percent': font_size_percent,
            })
            # 持久化保存到 resources/app_config.toml
            cfg = load_app_config()
            if "ui_settings" not in cfg:
                cfg["ui_settings"] = {}
            cfg["ui_settings"].update({
                'font_family': font_family,
                'font_size_percent': font_size_percent,
            })
            save_app_config(cfg)
            st.success("✅ Settings saved successfully to config!")
            # Force a rerun to apply settings immediately
            st.rerun()
        # Reset settings
        if st.button("🔄 Reset to Defaults"):
            st.session_state.settings = {
                'font_family': 'Courier New',
                'font_size_percent': 100,
            }
            cfg = load_app_config()
            if "ui_settings" not in cfg:
                cfg["ui_settings"] = {}
            cfg["ui_settings"].update({
                'font_family': 'Courier New',
                'font_size_percent': 100,
            })
            save_app_config(cfg)
            st.success("✅ Settings reset to defaults!")
            # Force a rerun to apply settings immediately
            st.rerun()
    with tab2:
        st.subheader("📋 About FlightCheck")
        st.markdown("""
        **Version:** 0.6.4
        **Developer:** Gostnort 
        **Description:** A comprehensive system for processing and validating HBPR passenger records.
        **Features:**
        - ✅ Database management and building
        - ✅ Single and batch record processing  
        - ✅ Real-time validation and error reporting
        - ✅ Statistical analysis and reporting
        - ✅ Data export in multiple formats
        - ✅ User-friendly web interface
        **Technology Stack:**
        - Python 3.x
        - Streamlit for UI
        - SQLite for database
        - Pandas for data analysis
        **Architecture:**
        - Modular UI components in /ui folder
        - Backend processing scripts in /scripts folder
        - Improved file organization and maintainability
        """)

