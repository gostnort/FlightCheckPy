# -*- coding: utf-8 -*-
"""
UI 样式加载器模块
负责加载外部静态 CSS 样式表及应用动态用户字体配置
"""

from pathlib import Path
import streamlit as st

CSS_FILE_PATH = Path("resources/styles/main.css")

DEFAULT_UI_STYLE = {
    "nav_bg": "#90EE90",
    "nav_text": "#000000",
    "nav_border": "#32CD32",
    "nav_hover_bg": "#98FB98",
    "nav_hover_border": "#228B22",
    "nav_border_width": 2.0,
    "nav_bold": True,
    "content_pad_top": 0.0,
    "content_pad_bottom": 5.0,
    "block_gap": 0.5,
    "header_height": 2.5,
    "main_pad_top": 1.0,
    "button_gap": 5.0,
    "field_gap": 5.0,
    "tab_gap": 5.0,
    "notice_gap": 1.0,
    "header_shadow": True,
    "badge_enc": "#0b3d91",
    "badge_plain": "#555555",
}

_STYLE_LIMITS = {
    "nav_border_width": (0.0, 8.0),
    "content_pad_top": (0.0, 12.0),
    "content_pad_bottom": (0.0, 12.0),
    "block_gap": (0.0, 4.0),
    "header_height": (1.0, 6.0),
    "main_pad_top": (0.0, 6.0),
    "button_gap": (0.0, 48.0),
    "field_gap": (0.0, 48.0),
    "tab_gap": (0.0, 48.0),
    "notice_gap": (0.0, 4.0),
}


def _hex_color(value, fallback: str) -> str:
    text = str(value or "").strip()
    if len(text) == 7 and text.startswith("#"):
        digits = text[1:]
        if all(char in "0123456789abcdefABCDEF" for char in digits):
            return text.lower()
    return fallback


def _number(value, fallback: float, low: float, high: float) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return fallback
    return max(low, min(high, number))


def normalized_ui_style(raw: dict | None) -> dict:
    """Keep only known style fields, with defaults and safe values."""
    stored = raw if isinstance(raw, dict) else {}
    style = dict(DEFAULT_UI_STYLE)
    for key, default in DEFAULT_UI_STYLE.items():
        if key not in stored:
            continue
        if isinstance(default, bool):
            style[key] = bool(stored[key])
        elif isinstance(default, str):
            style[key] = _hex_color(stored[key], default)
        else:
            low, high = _STYLE_LIMITS.get(key, (0.0, 12.0))
            style[key] = _number(stored[key], default, low, high)
    return style


def saved_ui_style() -> dict:
    """Style values last saved in app config, filled with defaults."""
    from scripts.config_manager import load_app_config

    return normalized_ui_style(load_app_config().get("ui_style"))


def _style_variables(style: dict) -> str:
    shadow = "0 1px 2px rgba(0, 0, 0, 0.1)" if style["header_shadow"] else "none"
    weight = "bold" if style["nav_bold"] else "normal"
    return f"""
:root {{
    --nav-btn-bg: {style["nav_bg"]};
    --nav-btn-text: {style["nav_text"]};
    --nav-btn-border: {style["nav_border"]};
    --nav-btn-hover-bg: {style["nav_hover_bg"]};
    --nav-btn-hover-border: {style["nav_hover_border"]};
    --nav-btn-border-width: {style["nav_border_width"]}px;
    --nav-btn-weight: {weight};
    --content-pad-top: {style["content_pad_top"]}rem;
    --content-pad-bottom: {style["content_pad_bottom"]}rem;
    --block-gap: {style["block_gap"]}rem;
    --header-height: {style["header_height"]}rem;
    --main-pad-top: {style["main_pad_top"]}rem;
    --button-gap: {style["button_gap"]}px;
    --field-gap: {style["field_gap"]}px;
    --tab-gap: {style["tab_gap"]}px;
    --notice-gap: {style["notice_gap"]}rem;
    --header-shadow: {shadow};
    --badge-enc: {style["badge_enc"]};
    --badge-plain: {style["badge_plain"]};
}}
"""


def load_custom_css() -> None:
    """加载并注入外部静态 CSS 样式表"""
    if not CSS_FILE_PATH.exists():
        return
    try:
        css_content = CSS_FILE_PATH.read_text(encoding="utf-8")
        css_content += _style_variables(saved_ui_style())
        st.markdown(f"<style>\n{css_content}\n</style>", unsafe_allow_html=True)
    except Exception:
        pass


def apply_font_settings() -> None:
    """应用用户字体设置（从 session_state 动态生成并注入）"""
    if "settings" in st.session_state:
        settings = st.session_state.settings
        font_family = settings.get("font_family", "Courier New")
        font_size_percent = settings.get("font_size_percent", 100)
        base_font_size = 14
        actual_font_size = int(base_font_size * font_size_percent / 100)
        st.markdown(
            f"""
        <style>
        .stTextArea textarea {{
            font-family: "{font_family}", monospace !important;
            font-size: {actual_font_size}px !important;
        }}
        .stDataFrame {{
            font-family: "{font_family}", monospace !important;
            font-size: {actual_font_size}px !important;
        }}
        </style>
        """,
            unsafe_allow_html=True,
        )


def apply_app_styles() -> None:
    """全局统一入口：加载静态 CSS 并应用动态字体配置"""
    load_custom_css()
    apply_font_settings()
