#!/usr/bin/env python3
"""
Common utilities and shared functions for HBPR UI
"""

import streamlit as st
import pandas as pd
import os
import glob
import sqlite3
import re
import base64
import hashlib
from datetime import datetime
from scripts.hbpr_info_processor import CHbpr, HbprDatabase
from scripts.hbpr_list_processor import HBPRProcessor
import traceback


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
    创建数据库选择下拉框
    
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
            try:
                temp_db = HbprDatabase(db_file)
                flight_info = temp_db.get_flight_info()
                if flight_info:
                    display_name = f"{flight_info['flight_number']} ({flight_info['flight_date']}) - {os.path.basename(db_file)}"
                else:
                    display_name = f"Unknown Flight - {os.path.basename(db_file)}"
            except:
                display_name = f"Database - {os.path.basename(db_file)}"
            
            db_options.append((display_name, db_file))
        
        selected_db_display = st.selectbox(
            label,
            options=[opt[0] for opt in db_options],
            index=default_index,
            key=key
        )
        
        # 获取选中的数据库文件
        selected_db_file = None
        for display_name, db_file in db_options:
            if display_name == selected_db_display:
                selected_db_file = db_file
                break
        
        return selected_db_file, db_files
    else:
        # 简单版本，只显示文件名
        db_names = [os.path.basename(db_file) for db_file in db_files]
        selected_db_name = st.selectbox(
            label,
            options=db_names,
            index=default_index,
            key=key
        )
        # 获取完整的文件路径
        selected_db_file = db_files[db_names.index(selected_db_name)]
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