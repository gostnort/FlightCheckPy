#!/usr/bin/env python3
"""
Common utilities and shared functions for HBPR UI
"""

import streamlit as st
import os
import glob
import base64
import hashlib
import sqlite3
import tempfile
import sys
from datetime import datetime
from scripts.hbpr_info_processor import HbprDatabase


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


def apply_global_settings():
    """Apply global settings from session state"""
    if 'settings' in st.session_state:
        settings = st.session_state.settings
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


def get_sorted_database_files(sort_by='creation_time', reverse=True, custom_folder=None):
    """
    获取排序后的数据库文件列表
    Args:
        sort_by (str): 排序方式 - 'creation_time', 'modification_time', 'name'
        reverse (bool): 是否反向排序（True为最新的在前）
        custom_folder (str): 自定义数据库文件夹路径
    Returns:
        list: 排序后的数据库文件路径列表
    """
    # 搜索数据库文件
    db_files = []
    # 首先添加自定义文件夹中的数据库（如果指定）
    if custom_folder and os.path.exists(custom_folder) and os.path.isdir(custom_folder):
        custom_db_files = glob.glob(os.path.join(custom_folder, "*.db"))
        db_files.extend(custom_db_files)
    # 然后查找默认的databases文件夹
    if os.path.exists("databases"):
        default_db_files = glob.glob("databases/*.db")
        db_files.extend(default_db_files)
    # 如果databases文件夹中没有找到，则搜索根目录
    if not any(f.startswith("databases/") for f in db_files):
        root_db_files = glob.glob("*.db")
        db_files.extend(root_db_files)
    # 去重（防止同一文件被添加多次）
    db_files = list(set(db_files))
    if not db_files:
        return []
    # 根据指定方式排序
    if sort_by == 'creation_time':
        # 按创建时间排序
        db_files.sort(key=lambda x: os.path.getctime(x), reverse=reverse)
    elif sort_by == 'modification_time':
        # 按修改时间排序
        db_files.sort(key=lambda x: os.path.getmtime(x), reverse=reverse)
    elif sort_by == 'name':
        # 按文件名排序
        db_files.sort(key=lambda x: os.path.basename(x), reverse=reverse)
    else:
        # 默认按创建时间排序
        db_files.sort(key=lambda x: os.path.getctime(x), reverse=reverse)
    return db_files


def create_database_selectbox(label="Select database:", key=None, default_index=0, show_flight_info=False, custom_folder=None):
    """
    创建数据库选择下拉框并自动加载到内存数据库
    Args:
        label (str): 下拉框标签
        key (str): Streamlit组件key
        default_index (int): 默认选中的索引（0为最新的数据库）
        show_flight_info (bool): 是否显示航班信息
        custom_folder (str): 自定义数据库文件夹路径
    Returns:
        tuple: (selected_db_file, db_files_list) 或 (None, []) 如果没有数据库
    """
    db_files = get_sorted_database_files(sort_by='creation_time', reverse=True, custom_folder=custom_folder)
    if not db_files:
        return None, []
    
    if show_flight_info:
        # 显示航班信息的版本
        db_options = []
        for db_file in db_files:
            base_name = os.path.basename(db_file)
            
            # 添加位置指示器
            if custom_folder and db_file.startswith(custom_folder):
                location_indicator = "📁"  # 自定义文件夹
            elif db_file.startswith("databases/"):
                location_indicator = "🏠"  # 默认databases文件夹
            else:
                location_indicator = "📄"  # 根目录
            
            # 尝试从当前内存数据库获取航班信息
            current_memory_db_name = st.session_state.get('current_db_name', '')
            flight_info = None
            
            # 构建显示名称（只显示文件名，需求不再显示其他信息）
            display_name = f"{location_indicator} {base_name}"
            
            db_options.append((display_name, db_file))
        
        # 添加内存状态指示器
        current_memory_db_name = st.session_state.get('current_db_name', '')
        enhanced_options = []
        for display_name, db_file in db_options:
            db_name = os.path.basename(db_file)
            if db_name == current_memory_db_name:
                enhanced_display = f"💾 {display_name} (已加载到内存)"
            else:
                enhanced_display = display_name
            enhanced_options.append((enhanced_display, db_file))
        
        # 设定选中索引为当前已加载到内存的数据库
        selected_index = default_index
        for i, (_, db_file) in enumerate(enhanced_options):
            if os.path.basename(db_file) == current_memory_db_name:
                selected_index = i
                break

        selected_db_display = st.selectbox(
            label,
            options=[opt[0] for opt in enhanced_options],
            index=selected_index,
            key=key
        )
        
        # 获取选中的数据库文件
        selected_db_file = None
        for enhanced_display, db_file in enhanced_options:
            if enhanced_display == selected_db_display:
                selected_db_file = db_file
                break
    else:
        # 简单版本，只显示文件名
        db_names = [os.path.basename(db_file) for db_file in db_files]
        # 设定选中索引为当前已加载到内存的数据库
        current_memory_db_name = st.session_state.get('current_db_name', '')
        selected_index = default_index
        for i, name in enumerate(db_names):
            if name == current_memory_db_name:
                selected_index = i
                break

        selected_db_name = st.selectbox(
            label,
            options=db_names,
            index=selected_index,
            key=key
        )
        # 获取完整的文件路径
        selected_db_file = db_files[db_names.index(selected_db_name)]
    
    # 检查是否需要加载新的数据库到内存
    if selected_db_file:
        current_memory_db_name = st.session_state.get('current_db_name', '')
        selected_db_name = os.path.basename(selected_db_file)
        
        # 如果选择的数据库与当前内存中的不同，则加载新数据库
        if selected_db_name != current_memory_db_name:
            with st.spinner(f"🔄 正在切换到 {selected_db_name}..."):
                # 1) 先同步保存当前内存库（仅在存在已加载库时）
                if current_memory_db_name:
                    save_memory_database_to_file(show_progress=True)

                # 2) 清理旧的内存数据库和缓存
                if current_memory_db_name:
                    cleanup_old_memory_database()

                # 3) 加载新数据库
                success = load_database_to_memory(selected_db_file)
                if success:
                    memory_key = f"memory_db_{selected_db_name}"
                    st.session_state['current_memory_db'] = memory_key
                    st.session_state['current_db_name'] = selected_db_name
                    st.success(f"✅ 数据库 {selected_db_name} 已加载到内存")

                    # 触发页面刷新以更新状态显示
                    st.rerun()
                else:
                    st.error(f"❌ 无法加载数据库 {selected_db_name} 到内存")
                    return None, []
    
    return selected_db_file, db_files


def get_current_database():
    """
    获取当前选中的数据库文件路径（从session state）
    Returns:
        str or None: 当前选中的数据库文件路径，如果没有选中则返回None
    """
    return st.session_state.get('selected_database', None)


def get_available_databases():
    """
    获取可用的数据库文件列表（从session state）
    Returns:
        list: 可用的数据库文件路径列表
    """
    return st.session_state.get('available_databases', [])



def cleanup_old_memory_database():
    """
    清理旧的内存数据库连接和缓存，避免线程冲突
    """
    try:
        # 获取当前内存数据库标识
        current_memory_db = st.session_state.get('current_memory_db')
        if not current_memory_db:
            return
        
        # 清理所有相关的缓存实例
        keys_to_remove = []
        for key in st.session_state.keys():
            if (key.startswith(current_memory_db) and 
                ('_instance' in key or '_enhanced_instance' in key)):
                keys_to_remove.append(key)
        
        for key in keys_to_remove:
            cached_instance = st.session_state.get(key)
            if cached_instance and hasattr(cached_instance, 'close'):
                try:
                    cached_instance.close()  # 关闭连接
                except:
                    pass
            st.session_state.pop(key, None)
        
        # 移除当前内存数据库标识（不再持有连接对象）
        if current_memory_db in st.session_state:
            st.session_state.pop(current_memory_db, None)
        
        # 清理相关状态
        st.session_state.pop('current_memory_db', None)
        st.session_state.pop('current_db_name', None)
        
        # 清理临时保存文件
        temp_db_path = st.session_state.get('temp_db_for_background_save')
        if temp_db_path and os.path.exists(temp_db_path):
            try:
                os.remove(temp_db_path)
                st.session_state.pop('temp_db_for_background_save', None)
            except:
                pass
        
    except Exception as e:
        print(f"清理旧数据库时出错: {e}")


def load_database_to_memory(db_file_path: str) -> str:
    """
    将SQLite数据库文件加载到内存数据库中
    Args:
        db_file_path (str): 数据库文件路径
    Returns:
        str: 内存数据库的连接标识符（临时文件路径或内存标识）
    """
    try:
        # 检查文件是否存在
        if not os.path.exists(db_file_path):
            raise FileNotFoundError(f"数据库文件不存在: {db_file_path}")
        
        # 创建内存数据库连接（允许跨线程访问，避免Streamlit多线程导致的限制）
        memory_conn = sqlite3.connect(":memory:", check_same_thread=False)
        
        # 连接源数据库（短生命周期，不跨线程）
        source_conn = sqlite3.connect(db_file_path)
        
        # 将源数据库备份到内存数据库
        source_conn.backup(memory_conn)
        
        # 关闭源连接
        source_conn.close()
        
        # 将内存数据库连接存储到session state
        memory_db_key = f"memory_db_{os.path.basename(db_file_path)}"
        st.session_state[memory_db_key] = memory_conn
        
        # 返回内存数据库标识
        return memory_db_key
        
    except Exception as e:
        st.error(f"加载数据库到内存失败: {e}")
        return None


def get_memory_database_connection(memory_db_key: str) -> sqlite3.Connection:
    """
    获取内存数据库连接
    Args:
        memory_db_key (str): 内存数据库标识
    Returns:
        sqlite3.Connection: 数据库连接对象
    """
    return st.session_state.get(memory_db_key, None)


def create_database_uploader_widget():
    """
    创建数据库文件上传组件
    Returns:
        tuple: (uploaded_file, memory_db_key) 或 (None, None)
    """
    st.subheader("📂 数据库文件管理")
    
    # 显示当前可用的数据库
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.markdown("**本地数据库文件:**")
        local_dbs = get_sorted_database_files()
        if local_dbs:
            for db in local_dbs[:5]:  # 只显示前5个
                if st.button(f"📁 加载 {os.path.basename(db)}", key=f"load_{db}"):
                    with st.spinner("正在加载数据库到内存..."):
                        memory_key = load_database_to_memory(db)
                        if memory_key:
                            st.session_state['current_memory_db'] = memory_key
                            st.session_state['current_db_name'] = os.path.basename(db)
                            st.success(f"✅ 数据库 {os.path.basename(db)} 已加载到内存")
                            st.rerun()
        else:
            st.info("📋 未找到本地数据库文件")
    
    with col2:
        st.markdown("**上传数据库:**")
        uploaded_file = st.file_uploader(
            "选择数据库文件",
            type=['db', 'sqlite', 'sqlite3'],
            help="支持 .db, .sqlite, .sqlite3 格式"
        )
        
        if uploaded_file is not None:
            if st.button("🚀 加载上传的数据库"):
                with st.spinner("正在处理上传的数据库..."):
                    memory_key = load_uploaded_database_to_memory(uploaded_file)
                    if memory_key:
                        st.session_state['current_memory_db'] = memory_key
                        st.session_state['current_db_name'] = uploaded_file.name
                        st.success(f"✅ 上传的数据库 {uploaded_file.name} 已加载到内存")
                        st.rerun()
    
    # 显示当前加载的数据库状态
    current_db = st.session_state.get('current_memory_db')
    current_name = st.session_state.get('current_db_name', '未选择')
    
    if current_db:
        st.success(f"🎯 当前数据库: **{current_name}** (已加载到内存)")
        
        # 显示数据库信息
        try:
            conn = get_memory_database_connection(current_db)
            if conn:
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM hbpr_full_records")
                record_count = cursor.fetchone()[0]
                st.info(f"📊 记录数量: {record_count:,} 条")
        except Exception as e:
            st.warning(f"⚠️ 数据库信息读取失败: {e}")
    else:
        st.info("📋 请选择或上传数据库文件")
    
    return current_db


def load_uploaded_database_to_memory(uploaded_file) -> str:
    """
    将上传的数据库文件加载到内存
    Args:
        uploaded_file: Streamlit上传的文件对象
    Returns:
        str: 内存数据库标识符
    """
    try:
        # 创建临时文件保存上传的数据库
        with tempfile.NamedTemporaryFile(delete=False, suffix='.db') as tmp_file:
            tmp_file.write(uploaded_file.getvalue())
            tmp_path = tmp_file.name
        
        # 加载到内存
        memory_key = load_database_to_memory(tmp_path)
        
        # 删除临时文件
        os.unlink(tmp_path)
        
        return memory_key
        
    except Exception as e:
        st.error(f"处理上传数据库失败: {e}")
        return None


def create_memory_database_instance() -> HbprDatabase:
    """
    创建使用内存数据库的HbprDatabase实例
    Returns:
        HbprDatabase: 配置为使用内存数据库的实例
    """
    current_memory_db = st.session_state.get('current_memory_db')
    if not current_memory_db:
        raise ValueError("没有可用的内存数据库，请先加载数据库文件")
    
    conn = get_memory_database_connection(current_memory_db)
    if not conn:
        raise ValueError("内存数据库连接已失效，请重新加载数据库")
    
    # 创建HbprDatabase实例
    db = HbprDatabase(conn)
    return db


# === 全局内存数据库管理 ===

def terminate_application(error_message: str):
    """
    终止应用程序运行
    Args:
        error_message (str): 错误信息
    """
    st.error(f"🚨 严重错误：{error_message}")
    st.error("应用程序无法继续运行，请重新启动")
    st.stop()


def ensure_memory_database() -> HbprDatabase:
    """
    确保有可用的内存数据库，如果没有则终止应用
    Returns:
        HbprDatabase: 内存数据库实例
    """
    current_memory_db = st.session_state.get('current_memory_db')
    
    if not current_memory_db:
        st.error("❌ 没有可用的内存数据库")
        st.warning("请在数据库管理页面加载数据库文件")
        st.stop()
    
    # 检查是否已有缓存的数据库实例
    db_instance_key = f"{current_memory_db}_instance"
    cached_instance = st.session_state.get(db_instance_key)
    
    if cached_instance:
        # 测试连接是否仍然有效
        try:
            conn = cached_instance.get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM hbpr_full_records")
            record_count = cursor.fetchone()[0]
            
            if record_count > 0:
                return cached_instance
        except:
            # 连接无效，清除缓存
            st.session_state.pop(db_instance_key, None)
    
    # 创建新的数据库实例
    conn = get_memory_database_connection(current_memory_db)
    if not conn:
        terminate_application("内存数据库连接已失效")
    
    try:
        # 测试数据库连接
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM hbpr_full_records")
        record_count = cursor.fetchone()[0]
        
        if record_count == 0:
            terminate_application("内存数据库中没有数据")
        
        # 创建并缓存实例
        db_instance = HbprDatabase(conn)
        st.session_state[db_instance_key] = db_instance
        
        return db_instance
        
    except sqlite3.Error as e:
        terminate_application(f"内存数据库访问失败: {e}")
    except Exception as e:
        terminate_application(f"内存数据库未知错误: {e}")


def get_global_database() -> HbprDatabase:
    """
    获取全局统一的内存数据库实例
    这是整个项目唯一的数据库访问入口
    Returns:
        HbprDatabase: 内存数据库实例
    """
    return ensure_memory_database()


def initialize_memory_database_from_file(db_file_path: str) -> bool:
    """
    从文件初始化内存数据库
    Args:
        db_file_path (str): 数据库文件路径
    Returns:
        bool: 是否成功
    """
    try:
        memory_key = load_database_to_memory(db_file_path)
        if memory_key:
            st.session_state['current_memory_db'] = memory_key
            st.session_state['current_db_name'] = os.path.basename(db_file_path)
            return True
        return False
    except Exception as e:
        terminate_application(f"初始化内存数据库失败: {e}")


def database_status_widget():
    """
    显示数据库状态的小部件
    """
    current_db = st.session_state.get('current_memory_db')
    current_name = st.session_state.get('current_db_name', '未加载')
    
    if current_db:
        try:
            conn = get_memory_database_connection(current_db)
            if not conn:
                st.sidebar.error("❌ 数据库连接失效")
        except Exception as e:
            st.sidebar.error(f"❌ 数据库错误: {e}")
    else:
        st.sidebar.warning("⚠️ 未加载数据库")


def require_database_loaded():
    """
    装饰器：要求页面加载前必须有可用的数据库
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            if not st.session_state.get('current_memory_db'):
                st.error("❌ 请先在数据库管理页面加载数据库文件")
                st.info("👈 请在左侧菜单中选择 '数据库管理' 页面")
                st.stop()
            return func(*args, **kwargs)
        return wrapper
    return decorator


# === 简化的数据库管理接口 ===

class GlobalDatabaseManager:
    """
    全局数据库管理器 - 整个项目的唯一数据库访问入口
    """
    
    @staticmethod
    def get_database() -> HbprDatabase:
        """获取数据库实例"""
        return get_global_database()
    
    @staticmethod 
    def is_available() -> bool:
        """检查数据库是否可用"""
        return st.session_state.get('current_memory_db') is not None
    
    @staticmethod
    def get_record_count() -> int:
        """获取记录总数"""
        try:
            db = get_global_database()
            conn = db.get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM hbpr_full_records")
            return cursor.fetchone()[0]
        except:
            return 0
    
    @staticmethod
    def get_database_name() -> str:
        """获取数据库名称"""
        return st.session_state.get('current_db_name', '未知')


# 创建全局实例
db_manager = GlobalDatabaseManager()



# === 内存数据库持久化机制 ===

def save_memory_database_to_file(target_file_path: str = None, show_progress: bool = True) -> bool:
    """
    将内存数据库保存到文件
    Args:
        target_file_path (str, optional): 目标文件路径，如果为空则使用当前数据库文件路径
        show_progress (bool): 是否显示进度信息
    Returns:
        bool: 是否保存成功
    """
    try:
        current_memory_db = st.session_state.get('current_memory_db')
        if not current_memory_db:
            if show_progress:
                st.error("❌ 没有可用的内存数据库")
            return False
        
        # 获取内存数据库连接
        memory_conn = get_memory_database_connection(current_memory_db)
        if not memory_conn:
            if show_progress:
                st.error("❌ 内存数据库连接已失效")
            return False
        
        # 确定目标文件路径
        if not target_file_path:
            current_db_name = st.session_state.get('current_db_name', 'backup.db')
            # 如果在databases文件夹中，保存到databases文件夹
            if os.path.exists('databases'):
                target_file_path = os.path.join('databases', current_db_name)
            else:
                target_file_path = current_db_name
        
        # 确保目标目录存在
        target_dir = os.path.dirname(target_file_path)
        if target_dir and not os.path.exists(target_dir):
            os.makedirs(target_dir, exist_ok=True)
        
        if show_progress:
            with st.spinner(f"正在保存数据库到 {target_file_path}..."):
                # 创建目标文件数据库连接
                target_conn = sqlite3.connect(target_file_path, check_same_thread=False)
                
                # 将内存数据库备份到文件
                memory_conn.backup(target_conn)
                
                # 关闭目标连接
                target_conn.close()
                
                # 更新最后保存时间
                st.session_state['last_db_save_time'] = datetime.now()
                st.session_state['last_db_save_path'] = target_file_path
        else:
            # 不显示进度的静默保存
            target_conn = sqlite3.connect(target_file_path, check_same_thread=False)
            memory_conn.backup(target_conn)
            target_conn.close()
            st.session_state['last_db_save_time'] = datetime.now()
            st.session_state['last_db_save_path'] = target_file_path
        
        if show_progress:
            st.success(f"✅ 数据库已保存到: {target_file_path}")
        
        return True
        
    except Exception as e:
        if show_progress:
            st.error(f"❌ 保存数据库失败: {e}")
        else:
            print(f"Background save failed: {e}")
        return False


def auto_save_memory_database():
    """
    自动保存内存数据库（使用同步方式避免线程问题）
    """
    try:
        current_memory_db = st.session_state.get('current_memory_db')
        if not current_memory_db:
            return
        
        memory_conn = get_memory_database_connection(current_memory_db)
        if not memory_conn:
            return
        
        # 确定保存路径
        current_db_name = st.session_state.get('current_db_name', 'auto_backup.db')
        if os.path.exists('databases'):
            save_path = os.path.join('databases', current_db_name)
        else:
            save_path = current_db_name
        
        # 同步保存（避免线程问题）
        target_conn = sqlite3.connect(save_path, check_same_thread=False)
        memory_conn.backup(target_conn)
        target_conn.close()
        
        # 更新保存状态
        st.session_state['last_auto_save_time'] = datetime.now()
        st.session_state['auto_save_count'] = st.session_state.get('auto_save_count', 0) + 1
        
    except Exception as e:
        # 静默处理错误，不影响主线程
        print(f"Auto-save error: {e}")


def background_auto_save_memory_database():
    """
    已弃用：移除后台异步保存，统一采用同步保存以避免线程问题
    """
    return


def create_database_backup(backup_name: str = None) -> str:
    """
    创建数据库备份
    Args:
        backup_name (str, optional): 备份文件名，如果为空则自动生成
    Returns:
        str: 备份文件路径
    """
    try:
        if not backup_name:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            current_db_name = st.session_state.get('current_db_name', 'database.db')
            name_without_ext = os.path.splitext(current_db_name)[0]
            backup_name = f"{name_without_ext}_backup_{timestamp}.db"
        
        backup_path = os.path.join('databases', 'backups', backup_name)
        
        # 确保备份目录存在
        os.makedirs(os.path.dirname(backup_path), exist_ok=True)
        
        success = save_memory_database_to_file(backup_path, show_progress=False)
        
        if success:
            return backup_path
        else:
            return None
            
    except Exception as e:
        st.error(f"❌ 创建备份失败: {e}")
        return None


def database_save_status_widget():
    """
    在侧边栏显示简洁的保存状态。
    图标：🗃️ 已保存 / 💣 未保存
    """
    last_save_time = st.session_state.get('last_db_save_time')
    current_name = st.session_state.get('current_db_name', '未加载')
    if last_save_time:
        icon = "🗃️"
        msg = f"{icon} 已保存 {last_save_time.strftime('%H:%M:%S')}"
        st.sidebar.success(msg)
    else:
        icon = "💣"
        msg = f"{icon} 未保存 | {current_name}"
        st.sidebar.warning(msg)


def enable_auto_save_on_change():
    """
    启用数据修改时的自动保存
    在所有数据库修改操作后调用此函数
    """
    # 检查是否启用自动保存
    auto_save_enabled = st.session_state.get('auto_save_enabled', True)
    
    if auto_save_enabled:
        auto_save_memory_database()


class HbprDatabaseWithAutoSave(HbprDatabase):
    """
    带自动保存功能的内存数据库类
    """
    
    def update_with_chbpr_results(self, chbpr_instance):
        """重写父类方法，添加自动保存"""
        result = super().update_with_chbpr_results(chbpr_instance)
        enable_auto_save_on_change()  # 触发自动保存
        return result
    
    def create_simple_record(self, hbnb_number: int, record_line: str):
        """重写父类方法，添加自动保存"""
        result = super().create_simple_record(hbnb_number, record_line)
        enable_auto_save_on_change()  # 触发自动保存
        return result
    
    def create_full_record(self, hbnb_number: int, record_content: str):
        """重写父类方法，添加自动保存"""
        result = super().create_full_record(hbnb_number, record_content)
        enable_auto_save_on_change()  # 触发自动保存
        return result
    
    def delete_simple_record(self, hbnb_number: int):
        """重写父类方法，添加自动保存"""
        result = super().delete_simple_record(hbnb_number)
        enable_auto_save_on_change()  # 触发自动保存
        return result


# 修改数据库状态小部件，集成保存状态
def enhanced_database_status_widget():
    """
    增强的数据库状态小部件，包含保存状态
    """
    database_status_widget()  # 原有的数据库状态
    database_save_status_widget()  # 新增的保存状态


# 更新全局数据库管理器以使用带自动保存的类
class EnhancedGlobalDatabaseManager(GlobalDatabaseManager):
    """
    增强的全局数据库管理器，支持自动保存
    """
    
    @staticmethod
    def get_database() -> HbprDatabaseWithAutoSave:
        """获取带自动保存功能的数据库实例"""
        current_memory_db = st.session_state.get('current_memory_db')
        
        if not current_memory_db:
            st.error("❌ 没有可用的内存数据库")
            st.warning("请在数据库管理页面加载数据库文件")
            st.stop()
        
        # 检查是否已有缓存的数据库实例
        db_instance_key = f"{current_memory_db}_enhanced_instance"
        cached_instance = st.session_state.get(db_instance_key)
        
        if cached_instance:
            # 测试连接是否仍然有效
            try:
                conn = cached_instance.get_connection()
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM hbpr_full_records")
                record_count = cursor.fetchone()[0]
                
                if record_count > 0:
                    return cached_instance
            except:
                # 连接无效，清除缓存
                st.session_state.pop(db_instance_key, None)
        
        # 创建新的数据库实例
        conn = get_memory_database_connection(current_memory_db)
        if not conn:
            terminate_application("内存数据库连接已失效")
        
        try:
            # 测试数据库连接
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM hbpr_full_records")
            record_count = cursor.fetchone()[0]
            
            if record_count == 0:
                terminate_application("内存数据库中没有数据")
            
            # 创建并缓存带自动保存功能的实例
            db_instance = HbprDatabaseWithAutoSave(conn)
            st.session_state[db_instance_key] = db_instance
            
            return db_instance
            
        except sqlite3.Error as e:
            terminate_application(f"内存数据库访问失败: {e}")
        except Exception as e:
            terminate_application(f"内存数据库未知错误: {e}")


# 替换全局数据库管理器
db_manager = EnhancedGlobalDatabaseManager()

