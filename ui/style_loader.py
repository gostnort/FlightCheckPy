# -*- coding: utf-8 -*-
"""
UI 样式加载器模块
负责加载外部静态 CSS 样式表及应用动态用户字体配置
"""

from pathlib import Path
import streamlit as st

CSS_FILE_PATH = Path("resources/styles/main.css")


def load_custom_css() -> None:
    """加载并注入外部静态 CSS 样式表"""
    if CSS_FILE_PATH.exists():
        try:
            with open(CSS_FILE_PATH, "r", encoding="utf-8") as f:
                css_content = f.read()
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
