#!/usr/bin/env python3
"""
Common utilities and shared functions for HBPR UI
"""

import streamlit as st
import base64
import hashlib
import subprocess
import sys
import time
from urllib.request import urlopen
from urllib.error import URLError

def get_icon_base64(path):
    """将图标文件转换为base64编码"""
    try:
        with open(path, "rb") as icon_file:
            return base64.b64encode(icon_file.read()).decode()
    except FileNotFoundError:
        return ""


def authenticate_user(username):
    """
    Authenticate user using username only (SHA256 hashed)
    """
    # Obfuscated valid usernames (SHA256 hashes)
    valid_usernames = [
        'c7c5b358d4097f8e2798c54f2ab6c3574a0cc82c87a3acf4ac9f038af4f75d2c',
        '9fe93417853739c1c18c2e8b051860d1a317824f1aa91304d16f3fe832486f7a'
    ]
    # Hash the provided username
    username_hash = hashlib.sha256(username.encode()).hexdigest()
    # Check if the username hash exists in valid usernames
    return username_hash in valid_usernames


def _port_for_username(username: str) -> int:
    """Map valid username (by hash) to a fixed LAN port (two users)."""
    username_hash = hashlib.sha256(username.encode()).hexdigest()
    mapping = {
        'c7c5b358d4097f8e2798c54f2ab6c3574a0cc82c87a3acf4ac9f038af4f75d2c': 51201,
        '9fe93417853739c1c18c2e8b051860d1a317824f1aa91304d16f3fe832486f7a': 51202,
    }
    return mapping.get(username_hash, 0)


def _is_server_running(port: int) -> bool:
    if not port:
        return False
    try:
        with urlopen(f"http://127.0.0.1:{port}/health", timeout=1) as resp:
            return resp.status == 200
    except URLError:
        return False
    except Exception:
        return False


def ensure_memdb_server(username: str) -> tuple:
    """
    Ensure a per-user in-memory DB HTTP server is running on the mapped port.
    Returns: (ok: bool, port: int, message: str)
    Behavior:
    - If server already running → treat as already logged in, return (False, port, msg)
    - Else spawn remote_db/memdb_port_server.py on that port and wait until healthy
    """
    port = _port_for_username(username)
    if not port:
        return False, 0, "No port mapping for user"
    if _is_server_running(port):
        return False, port, "User already logged in on this host"
    # Spawn server
    server_path = None
    try:
        # Resolve script path relative to project root
        from pathlib import Path
        project_root = Path(__file__).resolve().parents[1]
        server_path = str(project_root / 'remote_db' / 'memdb_port_server.py')
        subprocess.Popen([sys.executable, server_path, '--port', str(port)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception as e:
        return False, 0, f"Failed to start server: {e}"
    # Wait until health OK
    for _ in range(30):
        if _is_server_running(port):
            return True, port, "OK"
        time.sleep(0.1)
    return False, 0, "Timed out starting server"


def apply_global_settings():
    """Apply global settings from session state"""
    if 'settings' in st.session_state:
        # Apply font settings globally
        apply_font_settings()
    # Remove the purple vertical block spacing
    remove_vertical_block_spacing()


def apply_font_settings():
    """Apply font settings from session state"""
    if 'settings' in st.session_state:
        settings = st.session_state.settings
        font_family = settings.get('font_family', 'Courier New')
        font_size_percent = settings.get('font_size_percent', 100)
        base_font_size = 14  # Base font size for data elements
        actual_font_size = int(base_font_size * font_size_percent / 100)
        st.markdown(f"""
        <style>
        /* Data-specific font settings - only for Raw Content and Data Tables */
        .stTextArea textarea {{
            font-family: "{font_family}", monospace !important;
            font-size: {actual_font_size}px !important;
        }}
        /* Data frames */
        .stDataFrame {{
            font-family: "{font_family}", monospace !important;
            font-size: {actual_font_size}px !important;
        }}
        </style>
        """, unsafe_allow_html=True)


def remove_vertical_block_spacing():
    """Remove the purple vertical block spacing from stMainBlockContainer while preserving button spacing"""
    st.markdown("""
    <style>
    /* Remove spacing from stMainBlockContainer but keep element gaps */
    [data-testid="stMainBlockContainer"] {
        padding-top: 0 !important;
        padding-bottom: 5rem !important;
        margin-top: 0 !important;
    }
    /* Target the main block container more specifically */
    .stMainBlockContainer {
        padding-top: 0 !important;
        margin-top: 0 !important;
    }
    /* Remove the top vertical spacing but keep small gaps between elements */
    .stVerticalBlock {
        gap: 0.5rem !important;
        padding-top: 0 !important;
        padding-bottom: 0.5rem !important;
        margin-top: 0 !important;
    }
    /* Target the stVerticalBlock inside stMainBlockContainer - keep minimal spacing */
    [data-testid="stVerticalBlock"] {
        gap: 0.5rem !important;
        padding-top: 0 !important;
        padding-bottom: 0.5rem !important;
        margin-top: 0 !important;
    }
    /* Remove any additional top spacing from the main content area */
    .main .block-container {
        padding-top: 0 !important;
        margin-top: 0 !important;
    }
    /* Properly positioned header without overlap */
    header[data-testid="stHeader"] {
        height: 2.5rem !important;
        min-height: 2.5rem !important;
        box-shadow: 0 1px 2px rgba(0,0,0,0.1) !important;
        z-index: 999 !important;
        position: relative !important;
    }
    /* Ensure header toolbar is properly sized */
    header[data-testid="stHeader"] [data-testid="stToolbar"] {
        height: 2.5rem !important;
        min-height: 2.5rem !important;
    }
    /* Proper spacing for main content */
    .stApp {
        padding-top: 0 !important;
        margin-top: 0 !important;
        min-height: 100vh !important;
        height: auto !important;
        overflow-y: visible !important;
    }
    /* Ensure main content doesn't overlap and can scroll properly */
    .stApp > .main {
        padding-top: 1rem !important;
        margin-top: 0 !important;
        padding-bottom: 5rem !important;
        min-height: calc(100vh - 3rem) !important;
        height: auto !important;
        overflow-y: visible !important;
    }
    /* Ensure the app view container allows full content display */
    section[data-testid="stAppViewContainer"] {
        height: auto !important;
        min-height: 100vh !important;
        overflow-y: visible !important;
    }
    /* Make sure the main content area is not height constrained */
    section[data-testid="stAppViewContainer"] > .main {
        height: auto !important;
        min-height: calc(100vh - 4rem) !important;
        overflow-y: visible !important;
        padding-bottom: 5rem !important;
    }
    /* Ensure buttons have proper spacing */
    .stButton {
        margin-bottom: 5px !important;
    }
    /* Add spacing between form elements */
    .stSelectbox, .stSlider, .stTextInput, .stNumberInput {
        margin-bottom: 5px !important;
    }
    /* Add minimal spacing between tabs and other elements */
    .stTabs {
        margin-top: 5px !important;
        margin-bottom: 5px !important;
    }
    </style>
    """, unsafe_allow_html=True)


def parse_hbnb_input(input_text: str) -> list:
    """
    解析HBNB输入，支持单个数字、范围和逗号分隔的列表
    例如: "400-410,412,415-420" -> [400, 401, 402, ..., 410, 412, 415, 416, ..., 420]
    """
    if not input_text.strip():
        return []
    hbnb_numbers = set()
    parts = [part.strip() for part in input_text.split(',')]
    for part in parts:
        if '-' in part:
            # 处理范围，如 "400-410"
            try:
                start, end = map(int, part.split('-'))
                if start > end:
                    start, end = end, start  # 自动交换顺序
                if start < 1 or end > 99999:
                    raise ValueError(f"Range {start}-{end} is out of valid range (1-99999)")
                hbnb_numbers.update(range(start, end + 1))
            except ValueError as e:
                raise ValueError(f"Invalid range format '{part}': {str(e)}")
        else:
            # 处理单个数字
            try:
                number = int(part)
                if number < 1 or number > 99999:
                    raise ValueError(f"Number {number} is out of valid range (1-99999)")
                hbnb_numbers.add(number)
            except ValueError as e:
                raise ValueError(f"Invalid number format '{part}': {str(e)}")
    return sorted(list(hbnb_numbers))