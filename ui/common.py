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
from remote_db.db_port_client import DbPortClient
from remote_db.remote_sqlite_adapter import RemoteSqliteConnection
from scripts.hbpr_database import HbprDatabase


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
        '9fe93417853739c1c18c2e8b051860d1a317824f1aa91304d16f3fe832486f7a',
        '239127e09157cbafb6212123b102aa1103241946b3684c232c44b8367c3a4d47'
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
        '239127e09157cbafb6212123b102aa1103241946b3684c232c44b8367c3a4d47': 51203
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
    确保指定用户的内存数据库HTTP服务器正在运行
    简化版：不再检查IP，只做用户名登录
    Returns: (ok: bool, port: int, message: str)
    行为:
    - 如果服务器已运行 → 直接调用登录接口
    - 否则启动服务器并等待健康检查通过，然后登录
    """
    port = _port_for_username(username)
    if not port:
        return False, 0, "No port mapping for user"
    server_already_running = _is_server_running(port)
    if server_already_running:
        # 服务器已运行，直接登录用户名
        try:
            client = DbPortClient("127.0.0.1", port)
            result = client.login_username(username)
            if result.get("ok"):
                return True, port, "OK"
            return False, port, "Login failed"
        except Exception as e:
            return False, 0, f"Failed to connect to server: {e}"
    # 启动服务器
    try:
        # 解析服务器脚本路径（相对于项目根目录）
        from pathlib import Path
        project_root = Path(__file__).resolve().parents[1]
        server_path = str(project_root / 'remote_db' / 'memdb_port_server.py')
        # 验证服务器脚本是否存在
        if not Path(server_path).exists():
            return False, 0, f"Server script not found: {server_path}"
        # 启动服务器进程，捕获输出用于调试
        proc = subprocess.Popen(
            [sys.executable, server_path, '--port', str(port)], 
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        # 给进程一点时间启动
        time.sleep(0.2)
        # 检查进程是否立即失败
        if proc.poll() is not None:
            # 进程已经退出，读取错误信息
            stdout, stderr = proc.communicate(timeout=1)
            error_msg = stderr if stderr else stdout
            return False, 0, f"Server failed to start: {error_msg[:200]}"
    except Exception as e:
        return False, 0, f"Failed to start server: {e}"
    # 等待服务器健康检查通过（增加到10秒超时）
    for i in range(100):
        if _is_server_running(port):
            # 服务器启动成功，登录用户名
            try:
                client = DbPortClient("127.0.0.1", port)
                client.login_username(username)
            except Exception:
                pass
            return True, port, "OK"
        time.sleep(0.1)
    return False, 0, "Timed out starting server (waited 10 seconds)"


# --- New Database Client Management ---


def get_db_port_client():
    """Gets/creates the DbPortClient for the current session."""
    port = st.session_state.get("db_service_port")
    if not port:
        return None
    client_key = f"db_port_client_{port}"
    if client_key not in st.session_state:
        st.session_state[client_key] = DbPortClient("127.0.0.1", port)
    return st.session_state[client_key]


def get_hbpr_database_client():
    """Gets/creates the HbprDatabase client instance for the current session."""
    port = st.session_state.get("db_service_port")
    client = get_db_port_client()
    if not client or not port:
        return None
    hbpr_client_key = f"hbpr_db_client_{port}"
    if hbpr_client_key not in st.session_state:
        remote_conn = RemoteSqliteConnection(client)
        st.session_state[hbpr_client_key] = HbprDatabase(remote_conn)
    return st.session_state[hbpr_client_key]


def is_db_available():
    """Check if a database is loaded and available."""
    client = get_db_port_client()
    if not client:
        return False
    try:
        health = client.health()
        return health.get("ok") and health.get("db") is not None
    except Exception:
        return False


def get_database_name():
    """Get the name of the currently loaded database."""
    client = get_db_port_client()
    if not client:
        return "N/A"
    try:
        return client.health().get("db", "N/A")
    except Exception:
        return "Error"


def trigger_auto_save():
    """
    Saves the in-memory database to its source file.
    Automatically clears the unsaved changes flag on success.
    """
    client = get_db_port_client()
    if client:
        try:
            client.save()
            # 清除未保存状态标志
            st.session_state.db_has_unsaved_changes = False
            return True
        except Exception as e:
            st.toast(f"Error saving database: {e}")
            return False
    return False


def reload_database_from_disk():
    """
    Reloads the current database from disk to reflect manual changes.
    This is useful when the database file has been modified externally.
    """
    client = get_db_port_client()
    port = st.session_state.get("db_service_port")
    if client and port:
        try:
            # First, reload the database from disk on the server
            result = client.reload_database()
            if result.get("ok"):
                # Only after successful reload, clear the cached database client
                # (since the data has changed and we need fresh queries)
                hbpr_client_key = f"hbpr_db_client_{port}"
                if hbpr_client_key in st.session_state:
                    del st.session_state[hbpr_client_key]
                st.success(f"✅ Database reloaded from disk: {result.get('db_name', 'Unknown')}")
                return True
            else:
                st.error(f"❌ Failed to reload database: {result.get('error', 'Unknown error')}")
                return False
        except Exception as e:
            st.error(f"❌ Error reloading database: {e}")
            return False
    return False


def logout_current_user():
    """
    登出当前用户（简化版，不再涉及IP）
    返回: (success: bool, message: str)
    """
    client = get_db_port_client()
    if not client:
        return False, "No database connection"
    try:
        result = client.logout_username()
        if result.get("ok"):
            return True, "Logged out successfully"
        else:
            return False, "Failed to logout"
    except Exception as e:
        return False, f"Error logging out: {e}"


def shutdown_db_server():
    """关闭当前用户的数据库服务器"""
    client = get_db_port_client()
    if client:
        try:
            client.shutdown()
            return True
        except Exception:
            # Server might already be down
            return True
    return False


def restart_db_server(username: str) -> tuple:
    """
    重启数据库服务器
    Returns: (ok: bool, port: int, message: str)
    """
    # 先关闭服务器
    shutdown_db_server()
    # 等待服务器完全关闭
    time.sleep(0.5)
    # 重新启动服务器
    return ensure_memdb_server(username)


def get_server_status(port: int) -> dict:
    """
    获取服务器状态信息
    Returns: dict with keys: running (bool), auth_status (dict or None)
    """
    if not port:
        return {"running": False, "auth_status": None}
    if not _is_server_running(port):
        return {"running": False, "auth_status": None}
    try:
        client = DbPortClient("127.0.0.1", port)
        auth_status = client.auth_status()
        return {"running": True, "auth_status": auth_status}
    except Exception:
        return {"running": True, "auth_status": None}


def load_database(path: str):
    """
    Requests the server to load a database file into memory.
    Automatically clears the unsaved changes flag on success.
    """
    client = get_db_port_client()
    port = st.session_state.get("db_service_port")
    if client and port:
        try:
            # When loading a new DB, we must destroy the old HbprDatabase client
            # because its internal state/cache is tied to the previous DB connection.
            hbpr_client_key = f"hbpr_db_client_{port}"
            if hbpr_client_key in st.session_state:
                del st.session_state[hbpr_client_key]
            client.load_database(path)
            # 清除未保存状态标志（加载新数据库时重置状态）
            st.session_state.db_has_unsaved_changes = False
            # Re-create the hbpr client on the next get() call
            return True
        except Exception as e:
            st.error(f"Failed to load database: {e}")
            return False
    return False


# --- New Database Selectbox Widget ---


def create_database_selectbox(label="💾 Select Database:", key="global_db_select", custom_folder=None):
    """
    Creates a selectbox for DB selection and handles loading it into memory.
    Now supports custom folders via session state or parameter.
    Only shows databases with valid schema.
    """
    client = get_db_port_client()
    db_files = []
    valid_db_files = []
    # Use custom folder from session state if available, otherwise use parameter
    active_custom_folder = st.session_state.get('custom_db_folder') or custom_folder
    if client:
        try:
            # List databases from custom folder if specified, otherwise from default 'databases' folder
            db_files = client.list_databases(active_custom_folder)
            # Validate each database schema
            for db_file in db_files:
                try:
                    validation_result = client.validate_database_schema(db_file)
                    if validation_result.get("valid", False):
                        valid_db_files.append(db_file)
                    else:
                        print(f"Database {db_file} has invalid schema, skipping")
                except Exception as e:
                    print(f"Failed to validate database {db_file}: {e}")
                    # Skip databases that can't be validated
                    pass
        except Exception:
            db_files = []
    if not valid_db_files:
        folder_desc = f"'{active_custom_folder}'" if active_custom_folder else "'databases/'"
        if db_files and not valid_db_files:
            # There are DB files but none are valid
            st.selectbox(label, [f"No compatible databases found in {folder_desc} folder"], disabled=True)
        else:
            # No DB files at all
            st.selectbox(label, [f"No databases found in {folder_desc} folder"], disabled=True)
        return None, []
    # Get current selection from session state to compare against widget state
    current_selection_key = f"db_selection_{key}"
    previous_selection = st.session_state.get(current_selection_key)
    # Find index of previous selection to set the widget correctly
    try:
        current_index = valid_db_files.index(previous_selection) if previous_selection in valid_db_files else 0
    except (ValueError, TypeError):
        current_index = 0
    selected_db_file = st.selectbox(label, valid_db_files, index=current_index, key=key)
    # If selection has changed, or if nothing is loaded yet, load the DB
    if (selected_db_file and selected_db_file != previous_selection) or (not is_db_available() and selected_db_file):
        if load_database(selected_db_file):
            st.session_state[current_selection_key] = selected_db_file
            st.rerun()
    return selected_db_file, valid_db_files


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


def detect_file_type(content: str) -> str:
    """
    检测文件内容类型：HBPR 或 PR
    Args:
        content: 文件内容
    Returns:
        str: 'HBPR', 'PR', 或 'UNKNOWN'
    """
    if not content or not content.strip():
        return 'UNKNOWN'
    # 检查是否包含HBPR或PR命令
    has_hbpr = '>HBPR:' in content
    has_pr = '>PR:' in content
    # 如果两者都有，返回UNKNOWN（不应该混合）
    if has_hbpr and has_pr:
        return 'UNKNOWN'
    # 返回检测到的类型
    if has_hbpr:
        return 'HBPR'
    if has_pr:
        return 'PR'
    return 'UNKNOWN'

