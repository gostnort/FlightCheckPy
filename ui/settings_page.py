#!/usr/bin/env python3
"""
Settings page for HBPR UI - System configuration
"""

import streamlit as st
from scripts.config_manager import load_app_config, save_app_config
from ui.style_loader import DEFAULT_UI_STYLE, normalized_ui_style, saved_ui_style


def _style_key(field: str) -> str:
    return f"ui_style_{field}"


def _seed_style_widgets() -> None:
    saved = saved_ui_style()
    for field, value in saved.items():
        key = _style_key(field)
        if key not in st.session_state:
            st.session_state[key] = value


def _style_from_widgets() -> dict:
    style = {}
    for field, default in DEFAULT_UI_STYLE.items():
        style[field] = st.session_state.get(_style_key(field), default)
    return style


def _save_ui_config(font_family: str, font_size_percent: int, style: dict) -> None:
    cfg = load_app_config()
    if "ui_settings" not in cfg:
        cfg["ui_settings"] = {}
    cfg["ui_settings"].update({
        "font_family": font_family,
        "font_size_percent": font_size_percent,
    })
    cfg["ui_style"] = normalized_ui_style(style)
    save_app_config(cfg)


def _reset_ui_settings() -> None:
    st.session_state.settings = {
        "font_family": "Courier New",
        "font_size_percent": 100,
    }
    st.session_state["font_family_select"] = "Courier New"
    st.session_state["font_size_slider"] = 100
    for field, value in DEFAULT_UI_STYLE.items():
        st.session_state[_style_key(field)] = value
    _save_ui_config("Courier New", 100, dict(DEFAULT_UI_STYLE))
    st.session_state.settings_notice = "Settings reset to defaults. Refresh the page to apply the layout."


def _render_layout_controls() -> None:
    st.subheader("Layout")
    st.caption("These controls edit the app stylesheet. Save, then refresh the page.")
    st.markdown("Navigation button")
    background, text, border = st.columns(3)
    with background:
        st.color_picker("Background", key=_style_key("nav_bg"))
    with text:
        st.color_picker("Text", key=_style_key("nav_text"))
    with border:
        st.color_picker("Border", key=_style_key("nav_border"))
    hover_bg, hover_border, border_width = st.columns(3)
    with hover_bg:
        st.color_picker("Hover background", key=_style_key("nav_hover_bg"))
    with hover_border:
        st.color_picker("Hover border", key=_style_key("nav_hover_border"))
    with border_width:
        st.number_input("Border width (px)", min_value=0.0, max_value=8.0, step=1.0, key=_style_key("nav_border_width"))
    bold, shadow = st.columns(2)
    with bold:
        st.checkbox("Bold label", key=_style_key("nav_bold"))
    with shadow:
        st.checkbox("Header shadow", key=_style_key("header_shadow"))
    st.markdown("Spacing")
    top, bottom, gap = st.columns(3)
    with top:
        st.number_input("Content top (rem)", min_value=0.0, max_value=12.0, step=0.1, key=_style_key("content_pad_top"))
    with bottom:
        st.number_input("Content bottom (rem)", min_value=0.0, max_value=12.0, step=0.1, key=_style_key("content_pad_bottom"))
    with gap:
        st.number_input("Section gap (rem)", min_value=0.0, max_value=4.0, step=0.1, key=_style_key("block_gap"))
    header, page_top, notice = st.columns(3)
    with header:
        st.number_input("Header height (rem)", min_value=1.0, max_value=6.0, step=0.1, key=_style_key("header_height"))
    with page_top:
        st.number_input("Page top (rem)", min_value=0.0, max_value=6.0, step=0.1, key=_style_key("main_pad_top"))
    with notice:
        st.number_input("Notice spacing (rem)", min_value=0.0, max_value=4.0, step=0.1, key=_style_key("notice_gap"))
    button_gap, field_gap, tab_gap = st.columns(3)
    with button_gap:
        st.number_input("Button spacing (px)", min_value=0.0, max_value=48.0, step=1.0, key=_style_key("button_gap"))
    with field_gap:
        st.number_input("Field spacing (px)", min_value=0.0, max_value=48.0, step=1.0, key=_style_key("field_gap"))
    with tab_gap:
        st.number_input("Tab spacing (px)", min_value=0.0, max_value=48.0, step=1.0, key=_style_key("tab_gap"))
    enc, plain = st.columns(2)
    with enc:
        st.color_picker("Encrypted marker", key=_style_key("badge_enc"))
    with plain:
        st.color_picker("Plain marker", key=_style_key("badge_plain"))


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
        _seed_style_widgets()
        notice = st.session_state.pop("settings_notice", None)
        if notice:
            st.success(notice)
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
        _render_layout_controls()
        if st.button("💾 Save Settings", type="primary"):
            st.session_state.settings.update({
                "font_family": font_family,
                "font_size_percent": font_size_percent,
            })
            _save_ui_config(font_family, int(font_size_percent), _style_from_widgets())
            st.session_state.settings_notice = "Settings saved. Refresh the page to apply the layout."
            st.rerun()
        st.button("🔄 Reset to Defaults", on_click=_reset_ui_settings)
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

