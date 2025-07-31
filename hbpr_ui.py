#!/usr/bin/env python3
"""
HBPR Processing Web UI using Streamlit
Provides a user-friendly interface for HBPR record processing and validation.
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
from hbpr_info_processor import CHbpr, HbprDatabase
from hbpr_list_processor import HBPRProcessor
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


def show_login_page():
    """Display the login page"""
    st.markdown("""
    <div style="display: flex; align-items: center; justify-content: center; gap: 10px; margin-bottom: 30px;">
        <img src="data:image/x-icon;base64,{}" width="64" height="64">
        <h1 style="margin: 0;">Flight Check 0.6 --- Python</h1>
    </div>
    """.format(get_icon_base64("resources/fcp.ico")), unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Center the login form
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("### 🔐 User Authentication")
        st.caption("Please enter your username to access the system")
        
        with st.form("login_form"):
            username = st.text_input("👤 Username", placeholder="Enter username")
            
            col1, col2 = st.columns(2)
            with col1:
                submit_button = st.form_submit_button("🚀 Login", type="primary", use_container_width=True)
            with col2:
                if st.form_submit_button("🔄 Clear", use_container_width=True):
                    st.rerun()
            
            if submit_button:
                if not username:
                    st.error("❌ Please enter a username")
                elif authenticate_user(username):
                    st.session_state.authenticated = True
                    st.session_state.username = username
                    st.success(f"✅ Welcome, {username}! Authentication successful.")
                    st.rerun()
                else:
                    st.error("❌ Invalid username. Please try again.")
        
        st.markdown("---")
        st.caption("🔐 **Contact administrator for access credentials**")


def apply_global_settings():
    """Apply global settings from session state"""
    if 'settings' in st.session_state:
        settings = st.session_state.settings
        
        # Apply font settings globally
        apply_font_settings()


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
            <h3 style="margin: 0;">Flight Check 0.6 --- Python</h3>
        </div>
        """.format(get_icon_base64("resources/fcp.ico")), unsafe_allow_html=True)
        st.markdown("---")
        show_home_page()
    elif current_page == "🗄️ Database":
        show_database_management()
    elif current_page == "🔍 Process Records":
        show_process_records()
    elif current_page == "📊 View Results":
        show_view_results()
    elif current_page == "⚙️ Settings":
        show_settings()


def show_home_page():
    """显示主页"""
    # Apply settings
    apply_global_settings()
    
    # 检查是否需要刷新
    if 'refresh_home' in st.session_state and st.session_state.refresh_home:
        st.session_state.refresh_home = False
        st.rerun()
    
    st.header("🏠 Home Page")
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("📈 System Overview")
        # 检查数据库状态
        try:
            # 获取最新的数据库文件
            db_files = get_sorted_database_files(sort_by='creation_time', reverse=True)
            
            if not db_files:
                st.error("❌ No database files found!")
                st.info("💡 Please build a database first using the Database Management page.")
                return
            
            # 使用最新的数据库
            newest_db_file = db_files[0]
            db = HbprDatabase(newest_db_file)
            st.success(f"✅ Database connected: `{newest_db_file}`")
            
            # 获取HBNB范围信息
            range_info = db.get_hbnb_range_info()
            missing_numbers = db.get_missing_hbnb_numbers()
            record_summary = db.get_record_summary()
            
            # 显示HBNB范围信息
            metrics_col1, metrics_col2, metrics_col3, metrics_col4 = st.columns(4)
            with metrics_col1:
                st.metric("HBNB Range", f"{range_info['min']} - {range_info['max']}")
            with metrics_col2:
                st.metric("Total Records", record_summary['total_records'])
            with metrics_col3:
                st.metric("Full Records", record_summary['full_records'])
            with metrics_col4:
                st.metric("Simple Records", record_summary['simple_records'])
            
            # 显示验证统计
            validation_col1, validation_col2, validation_col3 = st.columns(3)
            with validation_col1:
                st.metric("Validated Records", record_summary['validated_records'])
            with validation_col2:
                st.metric("Missing Numbers", len(missing_numbers))
            with validation_col3:
                if record_summary['total_records'] > 0:
                    completeness = (record_summary['validated_records'] / record_summary['total_records']) * 100
                    st.metric("Completeness", f"{completeness:.1f}%")
                else:
                    st.metric("Completeness", "0%")
            # 显示缺失号码表格
            if missing_numbers:
                st.subheader("🚫 Missing HBNB Numbers")
                # 分页显示缺失号码
                items_per_page = 20
                total_pages = (len(missing_numbers) + items_per_page - 1) // items_per_page
                if total_pages > 1:
                    page = st.selectbox("Page:", range(1, total_pages + 1), key="missing_page")
                    start_idx = (page - 1) * items_per_page
                    end_idx = min(start_idx + items_per_page, len(missing_numbers))
                    page_missing = missing_numbers[start_idx:end_idx]
                else:
                    page_missing = missing_numbers
                # 创建缺失号码的DataFrame
                import pandas as pd
                missing_df = pd.DataFrame({
                    'Missing HBNB Numbers': page_missing
                })
                st.dataframe(missing_df, use_container_width=True)
                if total_pages > 1:
                    st.info(f"Showing page {page} of {total_pages} ({len(page_missing)} of {len(missing_numbers)} missing numbers)")
            else:
                st.success("✅ No missing HBNB numbers found!")
        except Exception as e:
            st.error(f"❌ No database found: {str(e)}")
            st.info("💡 Please build a database first using the Database Management page.")
    with col2:
        st.subheader("🚀 Quick Actions")
        if st.button("🗄️ Build Database", use_container_width=True):
            st.session_state.current_page = "🗄️ Database"
            st.rerun()
        if st.button("🔍 Process HBPR Record", use_container_width=True):
            st.session_state.current_page = "🔍 Process Records"
            st.rerun()
        if st.button("📄 Manual Input", use_container_width=True):
            st.session_state.current_page = "🔍 Process Records"
            st.rerun()
        if st.button("📊 View Results", use_container_width=True):
            st.session_state.current_page = "📊 View Results"
            st.rerun()
        if st.button("🔄 Refresh Home Page", use_container_width=True):
            st.rerun()
    st.markdown("---")
    # 最近活动
    st.subheader("📝 How to Use")
    st.markdown("""
    1. **Database Management**: Build your database from HBPR list files
    2. **Process Records**: Select and process individual HBPR records or manually input new records
    3. **View Results**: Browse validation results and export data
    4. **Settings**: Configure system preferences
    
    **Manual Input Features:**
    - Select database from dropdown
    - Input full HBPR records with flight info validation
    - Create simple HBNB records for placeholders
    - Automatic replacement of simple records with full records
    """)


def show_database_management():
    """显示数据库管理页面"""
    # Apply settings
    apply_global_settings()
    
    st.header("🗄️ Database Management")
    tab1, tab2, tab3 = st.tabs(["📥 Build Database", "🔍 Database Info", "🧹 Maintenance"])   
    with tab1:
        st.subheader("📥 Build Database from HBPR List")
        # 文件选择
        uploaded_file = st.file_uploader(
            "Choose HBPR list file:", 
            type=['txt'],
            help="Upload your sample_hbpr_list.txt file"
        )
        if uploaded_file is not None:
            # 保存上传的文件
            file_path = "uploaded_hbpr_list.txt"
            with open(file_path, "wb") as f:
                f.write(uploaded_file.getbuffer())
            # Track the uploaded file path for cleanup
            st.session_state.uploaded_file_path = file_path
            st.success("✅ File uploaded successfully!")
        # 使用上传的文件
        if uploaded_file and st.button("🔨 Build from Uploaded File", use_container_width=True):
            build_database_ui("uploaded_hbpr_list.txt")
    with tab2:
        st.subheader("🔍 Database Information")
        show_database_info()
    with tab3:
        st.subheader("🧹 Database Maintenance")
        show_database_maintenance()


def build_database_ui(input_file):
    """构建数据库的UI函数"""
    if not os.path.exists(input_file):
        st.error(f"❌ File not found: {input_file}")
        return
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    try:
        status_text.text("🔄 Initializing database builder...")
        progress_bar.progress(25)
        
        db = HbprDatabase()
        
        status_text.text("🔄 Processing HBPR list file...")
        progress_bar.progress(50)
        
        processor = db.build_from_hbpr_list(input_file)
        
        status_text.text("🔄 Adding CHbpr fields to database...")
        progress_bar.progress(75)
        
        progress_bar.progress(100)
        status_text.text("✅ Database built successfully!")
        
        st.success(f"🎉 Database created: `{db.db_file}`")
        
        # 显示构建结果 - 重点关注缺失号码
        range_info = db.get_hbnb_range_info()
        missing_numbers = db.get_missing_hbnb_numbers()
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("HBNB Range", f"{range_info['min']} - {range_info['max']}")
        with col2:
            st.metric("Total Expected", range_info['total_expected'])
        with col3:
            st.metric("Total Found", range_info['total_found'])
        with col4:
            st.metric("Missing Numbers", len(missing_numbers))
        
        # 显示缺失号码表格
        if missing_numbers:
            st.subheader("🚫 Missing HBNB Numbers")
            # 分页显示缺失号码
            items_per_page = 20
            total_pages = (len(missing_numbers) + items_per_page - 1) // items_per_page
            
            if total_pages > 1:
                page = st.selectbox("Page:", range(1, total_pages + 1), key="build_missing_page")
                start_idx = (page - 1) * items_per_page
                end_idx = min(start_idx + items_per_page, len(missing_numbers))
                page_missing = missing_numbers[start_idx:end_idx]
            else:
                page_missing = missing_numbers
            
            # 创建缺失号码的DataFrame
            import pandas as pd
            missing_df = pd.DataFrame({
                'Missing HBNB Numbers': page_missing
            })
            
            st.dataframe(missing_df, use_container_width=True)
            
            if total_pages > 1:
                st.info(f"Showing page {page} of {total_pages} ({len(page_missing)} of {len(missing_numbers)} missing numbers)")
        else:
            st.success("✅ No missing HBNB numbers found!")
    except Exception as e:
        status_text.text("❌ Error building database")
        st.error(f"Error: {str(e)}")
        st.error(traceback.format_exc())


def show_database_info():
    """显示数据库信息"""
    try:
        # 搜索数据库文件，优先查找databases文件夹
        db_files = []
        if os.path.exists("databases"):
            db_files = glob.glob("databases/*.db")
        
        # 如果databases文件夹中没有找到，则搜索根目录
        if not db_files:
            db_files = glob.glob("*.db")
        
        if not db_files:
            st.warning("⚠️ No database files found.")
            return
        
        for db_file in db_files:
            with st.expander(f"📁 {db_file}"):
                try:
                    conn = sqlite3.connect(db_file)
                    cursor = conn.cursor()
                    
                    # 获取表信息
                    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                    tables = cursor.fetchall()
                    
                    st.write("**Tables:**")
                    for table in tables:
                        table_name = table[0]
                        cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                        count = cursor.fetchone()[0]
                        st.write(f"- {table_name}: {count} records")
                    
                    # 如果是HBPR数据库，显示详细统计
                    if "hbpr_full_records" in [t[0] for t in tables]:
                        db_instance = HbprDatabase(db_file)
                        range_info = db_instance.get_hbnb_range_info()
                        missing_numbers = db_instance.get_missing_hbnb_numbers()
                        
                        st.write("**HBNB Range Information:**")
                        metrics_col1, metrics_col2, metrics_col3, metrics_col4 = st.columns(4)
                        with metrics_col1:
                            st.metric("HBNB Range", f"{range_info['min']} - {range_info['max']}")
                        with metrics_col2:
                            st.metric("Total Expected", range_info['total_expected'])
                        with metrics_col3:
                            st.metric("Total Found", range_info['total_found'])
                        with metrics_col4:
                            st.metric("Missing Numbers", len(missing_numbers))
                        
                        # 显示缺失号码
                        if missing_numbers:
                            st.write("**Missing HBNB Numbers:**")
                            # 限制显示前20个缺失号码
                            display_missing = missing_numbers[:20]
                            missing_text = ", ".join(map(str, display_missing))
                            if len(missing_numbers) > 20:
                                missing_text += f" ... and {len(missing_numbers) - 20} more"
                            st.text(missing_text)
                        else:
                            st.success("✅ No missing HBNB numbers found!")
                    
                    conn.close()
                    
                except Exception as e:
                    st.error(f"Error reading database: {str(e)}")
    
    except Exception as e:
        st.error(f"Error accessing databases: {str(e)}")


def show_database_maintenance():
    """显示数据库维护选项"""
    st.warning("⚠️ Maintenance operations are irreversible!")
    
    # 使用新的数据库选择函数，按创建时间排序，最新的在前
    selected_db, db_files = create_database_selectbox(
        label="Select database file:", 
        key="maintenance_db_select",
        default_index=0,  # 默认选择最新的数据库
        show_flight_info=False
    )
    
    if db_files:
        col1, col2 = st.columns(2)
        
        with col1:
            # 删除数据库按钮
            if st.button("🗑️ Delete Database", use_container_width=True):
                try:
                    os.remove(selected_db)
                    st.success(f"✅ Deleted {selected_db}")
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ Error deleting database: {str(e)}")
        
        with col2:
            # 更新missing_numbers表按钮
            if st.button("🔄 Update Missing Numbers", use_container_width=True):
                try:
                    db = HbprDatabase(selected_db)
                    db.update_missing_numbers_table()
                    st.success("✅ Missing numbers table updated successfully!")
                except Exception as e:
                    st.error(f"❌ Error updating missing numbers table: {str(e)}")
    else:
        st.info("ℹ️ No database files found.")


def show_process_records():
    """显示记录处理页面"""
    # Apply settings
    apply_global_settings()
    
    st.header("🔍 Process HBPR Records")
    
    try:
        db = HbprDatabase()
        db.find_database()
        
        tab1, tab2, tab3 = st.tabs(["🚀 Process All Records", "👀 View Record", "📄 Manual Input"])
        
        with tab1:
            process_all_records(db)
        
        with tab2:
            view_single_record(db)
        
        with tab3:
            process_manual_input()
        

    
    except Exception as e:
        st.error(f"❌ Database not available: {str(e)}")
        st.info("💡 Please build a database first in the Database Management page.")


def process_all_records(db):
    """处理所有记录并显示错误信息"""
    st.subheader("🚀 Process All Records")
    
    try:
        # 获取数据库文件列表
        db_files = get_sorted_database_files(sort_by='creation_time', reverse=True)
        # 数据库选择下拉框 - 只显示数据库文件名
        db_names = [os.path.basename(db_file) for db_file in db_files]
        if not db_files:
            st.error("❌ No database files found.")
            return
        
        # 处理控制
        col1, col2 = st.columns(2)
        
        with col1:
            # 数据库选择下拉框
            selected_db_name = st.selectbox(
                "Select Database:", 
                options=db_names,
                index=0,  # 默认选择最新的数据库
                key="process_all_db_select"
            )
            
            # 获取完整的文件路径
            selected_db_file = db_files[db_names.index(selected_db_name)]
            
            # 如果选择了不同的数据库，重新初始化
            if selected_db_file != db.db_file:
                db = HbprDatabase(selected_db_file)
        
        with col2:
            if st.button("🚀 Start Processing", use_container_width=True):
                start_processing_all_records(db, None)  # Always process all records
            
            if st.button("🧹 Erase Result", use_container_width=True):
                erase_splited_records(db)
        
        # 显示错误分组统计
        show_error_summary(db)
        # 显示错误信息
        show_error_messages(db)
        
    except Exception as e:
        st.error(f"❌ Error accessing database: {str(e)}")


def view_single_record(db):
    """查看单个记录"""
    try:
        conn = sqlite3.connect(db.db_file)
        cursor = conn.cursor()
        # 检查是否有已处理的记录
        cursor.execute("""
            SELECT hbnb_number, boarding_number, name, seat 
            FROM hbpr_full_records 
            WHERE is_validated = 1 AND (boarding_number IS NOT NULL OR name IS NOT NULL OR seat IS NOT NULL)
            ORDER BY hbnb_number
        """)
        processed_records = cursor.fetchall()
        # 获取所有记录（包括未处理的）
        cursor.execute("SELECT hbnb_number FROM hbpr_full_records ORDER BY hbnb_number")
        all_records = [row[0] for row in cursor.fetchall()]
        conn.close()
        if not all_records:
            st.warning("⚠️ No HBPR records found in database.")
            return
        # 选择记录的方式
        selection_method = st.radio(
            "👀 View Record 🧺🧺🧺🧺 Sorting by:",
            ["HBNB Number", "Boarding Number (BN)", "Seat", "Name"],
            horizontal=True
        )
        selected_record = None
        if selection_method == "HBNB Number":
            # HBNB选择（按数字从小到大排序）
            hbnb_number = st.selectbox(
                "Select HBNB Number:",
                sorted(all_records),
                help="Choose an HBNB number to view"
            )
            selected_record = hbnb_number  
        elif selection_method == "Boarding Number (BN)":
            # BN选择（按数字从小到大排序）
            if processed_records:
                # 提取有效的BN号码并排序
                bn_records = [(row[0], row[1]) for row in processed_records if row[1] is not None and row[1] > 0]
                bn_records.sort(key=lambda x: x[1])  
                # 按BN号码排序
                if bn_records:
                    bn_options = [f"BN {record[1]} (HBNB {record[0]})" for record in bn_records]
                    selected_bn = st.selectbox(
                        "Select Boarding Number:",
                        bn_options,
                        help="Choose a boarding number to view"
                    )
                    # 提取HBNB号码
                    selected_record = int(selected_bn.split("(HBNB ")[1].split(")")[0])
                else:
                    st.warning("⚠️ No boarding numbers found in processed records.")
                    return
            else:
                st.warning("⚠️ No processed records found. Please process records first.")
                return
         # 座位选择（按行号从小到大，然后按座位号A-Z排序）        
        elif selection_method == "Seat":
            if processed_records:
                # 提取有效的座位并排序
                seat_records = [(row[0], row[3]) for row in processed_records if row[3] is not None and row[3].strip()]
                if seat_records:
                    # 自定义座位排序函数
                    def seat_sort_key(seat_tuple):
                        seat = seat_tuple[1]
                        # 提取行号和座位号
                        match = re.match(r'(\d+)([A-Z])', seat)
                        if match:
                            row_num = int(match.group(1))
                            seat_letter = match.group(2)
                            return (row_num, seat_letter)
                        return (999, 'Z')  # 无效座位排在最后
                    seat_records.sort(key=seat_sort_key)
                    seat_options = [f"{record[1]} (HBNB {record[0]})" for record in seat_records]
                    selected_seat = st.selectbox(
                        "Select Seat:",
                        seat_options,
                        help="Choose a seat to view"
                    )
                    # 提取HBNB号码
                    selected_record = int(selected_seat.split("(HBNB ")[1].split(")")[0])
                else:
                    st.warning("⚠️ No seats found in processed records.")
                    return
            else:
                st.warning("⚠️ No processed records found. Please process records first.")
                return
        # 姓名选择（按字母A-Z排序）        
        elif selection_method == "Name":
            if processed_records:
                # 提取有效的姓名并排序
                name_records = [(row[0], row[2]) for row in processed_records if row[2] is not None and row[2].strip()]
                if name_records:
                    # 按姓名排序
                    name_records.sort(key=lambda x: x[1].upper())
                    name_options = [f"{record[1]} (HBNB {record[0]})" for record in name_records]
                    selected_name = st.selectbox(
                        "Select Name:",
                        name_options,
                        help="Choose a passenger name to view"
                    )
                    # 提取HBNB号码
                    selected_record = int(selected_name.split("(HBNB ")[1].split(")")[0])
                else:
                    st.warning("⚠️ No names found in processed records.")
                    return
            else:
                st.warning("⚠️ No processed records found. Please process records first.")
                return
        # 显示记录预览
        if selected_record:
            st.subheader("📄 Raw HBPR Content")
            # 显示警告信息（当选择BN或Seat时）
            if selection_method in ["Boarding Number (BN)", "Seat"]:
                # 使用自定义CSS来设置警告消息的样式
                st.markdown("""
                <style>
                .stAlert > div[data-testid="stAlert"] {
                    font-size: 10px !important;
                    margin: 5px !important;
                    padding: 5px !important;
                }
                </style>
                """, unsafe_allow_html=True)
                st.warning("⚠️ 剔除部分没有 #️⃣ BN or 💺 Seat 的记录")
            try:
                content = db.get_hbpr_record(selected_record)
                # Apply dynamic font settings
                apply_font_settings()
                st.text_area("Raw Content:", content, height=300, disabled=True)         
            except Exception as e:
                st.error(f"❌ Error retrieving record: {str(e)}")
    except Exception as e:
        st.error(f"❌ Error accessing database: {str(e)}")


def process_record_ui(db, hbnb_number):
    """处理记录的UI函数"""
    try:
        # 获取原始内容
        hbpr_content = db.get_hbpr_record(hbnb_number)
        
        # 处理记录
        with st.spinner(f"🔄 Processing HBNB {hbnb_number}..."):
            chbpr = CHbpr()
            chbpr.run(hbpr_content)
            
            # 更新数据库
            success = db.update_with_chbpr_results(chbpr)
        
        if success:
            st.success(f"✅ HBNB {hbnb_number} processed successfully!")
            
            # 显示处理结果
            display_processing_results(chbpr)
        else:
            st.error("❌ Failed to update database")
    
    except Exception as e:
        st.error(f"❌ Error processing record: {str(e)}")
        st.error(traceback.format_exc())


def display_processing_results(chbpr):
    """显示处理结果"""
    data = chbpr.get_structured_data()
    
    # 验证状态
    if chbpr.is_valid():
        st.success("✅ **Validation: PASSED**")
    else:
        st.error("❌ **Validation: FAILED**")
    
    # 乘客信息
    st.subheader("👤 Passenger Information")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("HBNB Number", data['hbnb_number'])
        st.metric("Boarding Number", data['boarding_number'] or "N/A")
        st.metric("PNR", data['PNR'] or "N/A")
    
    with col2:
        st.metric("Name", data['NAME'] or "N/A")
        st.metric("Passport Name", data['PSPT_NAME'] or "N/A")
        st.metric("Seat", data['SEAT'] or "N/A")
    
    with col3:
        st.metric("Class", data['CLASS'] or "N/A")
        st.metric("Destination", data['DESTINATION'] or "N/A")
        st.metric("FF Number", data['FF'] or "N/A")
    
    # 行李信息
    st.subheader("🧳 Baggage Information")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Checked Pieces", data['BAG_PIECE'])
        st.metric("Checked Weight", f"{data['BAG_WEIGHT']} kg")
    
    with col2:
        st.metric("EXPC Pieces", data['EXPC_PIECE'])
        st.metric("EXPC Weight", f"{data['EXPC_WEIGHT']} kg")
    
    with col3:
        st.metric("ASVC Pieces", data['ASVC_PIECE'])
        st.metric("FBA Pieces", data['FBA_PIECE'])
    
    with col4:
        st.metric("Allowance", data['BAG_ALLOWANCE'])
        st.metric("Flyer Benefit", data['FLYER_BENEFIT'])
    
    # 错误信息
    if not chbpr.is_valid():
        st.subheader("⚠️ Validation Errors")
        for error_type, error_list in chbpr.error_msg.items():
            if error_list:  # 只显示有错误的类型
                st.subheader(f"🔴 {error_type} Errors")
                for error in error_list:
                    st.error(error)
    
    # 调试信息
    with st.expander("🔧 Debug Information"):
        for debug in chbpr.debug_msg:
            st.text(debug)


def start_processing_all_records(db, batch_size):
    """开始处理所有记录"""
    try:
        # 获取所有记录
        conn = sqlite3.connect(db.db_file)
        cursor = conn.cursor()
        cursor.execute("SELECT hbnb_number FROM hbpr_full_records ORDER BY hbnb_number")
        records = [row[0] for row in cursor.fetchall()]
        conn.close()
        
        if not records:
            st.info("ℹ️ No records found.")
            return
        
        results_container = st.container()
        
        processed_count = 0
        valid_count = 0
        error_count = 0
        
        # 使用spinner显示处理状态
        with st.spinner(f"🔄 Processing {len(records)} records..."):
            for hbnb_number in records:
                try:
                    # 处理记录
                    content = db.get_hbpr_record(hbnb_number)
                    chbpr = CHbpr()
                    chbpr.run(content)
                    
                    # 更新数据库
                    success = db.update_with_chbpr_results(chbpr)
                    
                    if success:
                        processed_count += 1
                        if chbpr.is_valid():
                            valid_count += 1
                        else:
                            error_count += 1
                    
                except Exception as e:
                    # 静默处理错误，不显示具体错误信息
                    pass
        
        # 显示结果总结
        with results_container:
            st.success(f"🎉 Processed {processed_count} records")
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("Total Processed", processed_count)
            with col2:
                st.metric("Valid Records", valid_count)
            with col3:
                st.metric("Records with Errors", error_count)
        
        # 自动刷新页面以显示新的错误信息
        st.rerun()
    
    except Exception as e:
        st.error(f"❌ Processing error: {str(e)}")


def erase_splited_records(db):
    """清除所有处理结果，重置hbpr_full_records表中的处理字段"""
    try:
        # 显示确认对话框
        if st.button("⚠️ Confirm Erase", type="primary"):
            with st.spinner("🧹 Erasing all processing results..."):
                # 调用数据库类的erase_splited_records方法
                success = db.erase_splited_records()
                
                if success:
                    st.success("✅ Successfully erased all processing results!")
                    st.info("ℹ️ All processing fields have been reset. Only HBNB numbers and raw content remain.")
                    
                    # 自动刷新页面以显示更新后的状态
                    st.rerun()
                else:
                    st.error("❌ Failed to erase processing results.")
        
        else:
            st.warning("⚠️ This will permanently remove ALL processing results from the database.")
            st.info("💡 Only HBNB numbers and raw content will be preserved. Click 'Confirm Erase' to proceed.")
    
    except Exception as e:
        st.error(f"❌ Error during cleanup: {str(e)}")


def erase_bn_related_errors(db):
    """清除所有处理结果，重置hbpr_full_records表中的处理字段"""
    try:
        # 显示确认对话框
        if st.button("⚠️ Confirm Erase", type="primary"):
            with st.spinner("🧹 Erasing all processing results..."):
                # 重置所有处理字段，保留hbnb_number和record_content
                conn = sqlite3.connect(db.db_file)
                cursor = conn.cursor()
                
                # 重置所有CHbpr处理字段
                cursor.execute("""
                    UPDATE hbpr_full_records SET 
                    is_validated = 0, is_valid = NULL, 
                    pnr = NULL, name = NULL, seat = NULL, class = NULL,
                    destination = NULL, bag_piece = NULL, bag_weight = NULL,
                    bag_allowance = NULL, ff = NULL, pspt_name = NULL,
                    pspt_exp_date = NULL, ckin_msg = NULL, asvc_msg = NULL, expc_piece = NULL,
                    expc_weight = NULL, asvc_piece = NULL, fba_piece = NULL,
                    ifba_piece = NULL, flyer_benefit = NULL, is_ca_flyer = NULL,
                    error_count = NULL, error_baggage = NULL, error_passport = NULL, error_name = NULL, error_visa = NULL, error_other = NULL, validated_at = NULL
                """)
                
                # 获取更新的记录数
                updated_records = cursor.rowcount
                conn.commit()
                conn.close()
                
                if updated_records > 0:
                    st.success(f"✅ Successfully erased processing results from {updated_records} records!")
                    st.info("ℹ️ All processing fields have been reset. Only HBNB numbers and raw content remain.")
                    
                    # 自动刷新页面以显示更新后的状态
                    st.rerun()
                else:
                    st.info("ℹ️ No processing results found to erase.")
        
        else:
            st.warning("⚠️ This will permanently remove ALL processing results from the database.")
            st.info("💡 Only HBNB numbers and raw content will be preserved. Click 'Confirm Erase' to proceed.")
    
    except Exception as e:
        st.error(f"❌ Error during cleanup: {str(e)}")


def show_error_summary(db):
    """显示错误分组统计"""
    try:
        conn = sqlite3.connect(db.db_file)
        # 查询有错误的记录
        df = pd.read_sql_query("""
            SELECT error_baggage, error_passport, error_name, error_visa, error_other
            FROM hbpr_full_records 
            WHERE is_validated = 1 AND is_valid = 0 AND error_count > 0
        """, conn)
        conn.close()
        
        if df.empty:
            st.info("ℹ️ No error messages found. All processed records are valid!")
            return
        
        # 统计每种错误类型的数量
        error_types = ['error_baggage', 'error_passport', 'error_name', 'error_visa', 'error_other']
        error_labels = ['Baggage', 'Passport', 'Name', 'Visa', 'Other']
        error_counts = {}
        
        for error_type, label in zip(error_types, error_labels):
            # 计算非空错误的数量
            count = df[df[error_type].notna() & (df[error_type] != '')].shape[0]
            error_counts[label] = count
        
        # 显示错误统计
        total_records_with_errors = len(df)
        st.write(f"📊 **Total records with errors: {total_records_with_errors}**")
        
        labels = {'Baggage': '🧳',
                   'Passport': '🪪', 'Name': '👤', 'Visa': '🛂', 'Other': '🔧'}

        # 使用列显示每种错误类型的统计
        cols = st.columns(5)
        for i, (label, count) in enumerate(error_counts.items()):
            with cols[i]:
                st.metric(
                    label=f"{labels[label]} {label}",
                    value=count
                )
        st.markdown("---")
    except Exception as e:
        st.error(f"❌ Error loading error summary: {str(e)}")


def show_error_messages(db):
    """显示错误信息"""
    try:
        conn = sqlite3.connect(db.db_file)
        # 查询有错误的记录
        df = pd.read_sql_query("""
            SELECT hbnb_number, name, error_count, error_baggage, error_passport, error_name, error_visa, error_other, validated_at
            FROM hbpr_full_records 
            WHERE is_validated = 1 AND is_valid = 0 AND error_count > 0
            ORDER BY validated_at DESC, hbnb_number
        """, conn)
        conn.close()
        
        if df.empty:
            st.info("ℹ️ No error messages found. All processed records are valid!")
            return
        
        # 添加错误类型过滤下拉框
        error_types = ['All', 'Baggage', 'Passport', 'Name', 'Visa', 'Other']
        selected_error_type = st.selectbox(
            "🔍 Filter by Error Type:",
            error_types
        )
        
        # 根据选择的错误类型过滤记录
        if selected_error_type != 'All':
            error_field_map = {
                'Baggage': 'error_baggage',
                'Passport': 'error_passport', 
                'Name': 'error_name',
                'Visa': 'error_visa',
                'Other': 'error_other'
            }
            error_field = error_field_map[selected_error_type]
            df = df[df[error_field].notna() & (df[error_field] != '')]
            
            if df.empty:
                st.info(f"ℹ️ No {selected_error_type} error messages found!")
                return
        # 显示错误统计
        total_errors = len(df)
        st.write(f"**Found {total_errors} records with errors:**")
        # 分页显示错误信息
        items_per_page = 10
        total_pages = (total_errors + items_per_page - 1) // items_per_page
        if total_pages > 1:
            page = st.selectbox("Page:", range(1, total_pages + 1), key="error_page")
            start_idx = (page - 1) * items_per_page
            end_idx = min(start_idx + items_per_page, total_errors)
            page_df = df.iloc[start_idx:end_idx]
        else:
            page_df = df
        # 初始化session state用于跟踪哪个记录显示弹窗
        if 'show_popup_for' not in st.session_state:
            st.session_state.show_popup_for = None
        # 显示错误记录
        for _, row in page_df.iterrows():
            with st.expander(f"🚫 HBNB {row['hbnb_number']} - {row['name'] or 'Unknown'} ({row['error_count']} errors)"):
                st.write(f"**Validated at:** {row['validated_at']}")
                # 添加查看记录的弹出窗口
                col1, col2 = st.columns([3, 1])
                with col1:
                    st.write("**Quick Actions:**")
                with col2:
                    # 根据当前状态显示不同的按钮样式
                    is_viewing = st.session_state.show_popup_for == row['hbnb_number']
                    button_text = "❌ Close" if is_viewing else "👀 View"
                    # 使用自定义CSS样式来改变按钮背景颜色
                    button_color = "red" if is_viewing else "yellow"
                    button_style = f"""
                    <style>
                    .stButton > button[data-testid="view_{row['hbnb_number']}"] {{
                        background-color: {button_color} !important;
                        color: black !important;
                        border: 2px solid {button_color} !important;
                        font-weight: bold !important;
                    }}
                    .stButton > button[data-testid="view_{row['hbnb_number']}"]:hover {{
                        background-color: {button_color} !important;
                        opacity: 0.8 !important;
                    }}
                    </style>
                    """
                    st.markdown(button_style, unsafe_allow_html=True)
                    if st.button(button_text, key=f"view_{row['hbnb_number']}", use_container_width=True):
                        if is_viewing:
                            st.session_state.show_popup_for = None
                        else:
                            st.session_state.show_popup_for = row['hbnb_number']
                        st.rerun()
                # 如果当前记录需要显示弹窗，则显示弹窗内容
                if st.session_state.show_popup_for == row['hbnb_number']:
                    show_record_popup(db, row['hbnb_number'])
                # 解析并显示错误信息
                if selected_error_type == 'All':
                    # 显示所有错误类型
                    error_types = ['error_baggage', 'error_passport', 'error_name', 'error_visa', 'error_other']
                    error_labels = ['Baggage', 'Passport', 'Name', 'Visa', 'Other']
                    
                    for error_type, label in zip(error_types, error_labels):
                        if row[error_type] and row[error_type].strip():
                            # 使用markdown来支持换行显示
                            error_text = row[error_type].replace('\n', '<br>')
                            st.markdown(f"🔴 **{label}:** {error_text}", unsafe_allow_html=True)
                else:
                    # 只显示选中的错误类型
                    error_field_map = {
                        'Baggage': 'error_baggage',
                        'Passport': 'error_passport', 
                        'Name': 'error_name',
                        'Visa': 'error_visa',
                        'Other': 'error_other'
                    }
                    error_field = error_field_map[selected_error_type]
                    if row[error_field] and row[error_field].strip():
                        # 使用markdown来支持换行显示
                        error_text = row[error_field].replace('\n', '<br>')
                        st.markdown(f"🔴 **{selected_error_type}:** {error_text}", unsafe_allow_html=True)
        if total_pages > 1:
            st.info(f"Showing page {page} of {total_pages} ({len(page_df)} of {total_errors} records)")
    except Exception as e:
        st.error(f"❌ Error loading error messages: {str(e)}")


def show_record_popup(db, hbnb_number):
    """显示记录的弹出窗口"""
    try:
        # 获取原始内容
        content = db.get_hbpr_record(hbnb_number)
        # Apply dynamic font settings
        apply_font_settings()
        # 显示原始内容，使用全宽度
        st.text_area(
            "Raw Content:",
            content,
            height=400,
            disabled=True,
            key=f"popup_content_{hbnb_number}",
        )
    except Exception as e:
        st.error(f"❌ Error retrieving record: {str(e)}")


def validate_full_hbpr_record(hbpr_content):
    """
    Validate if the input content is a valid full HBPR record
    
    Args:
        hbpr_content: String content to validate
        
    Returns:
        dict: {
            'is_valid': bool,
            'hbnb_number': int or None,
            'errors': list of error messages,
            'chbpr_errors': dict of CHbpr error messages
        }
    """
    result = {
        'is_valid': False,
        'hbnb_number': None,
        'errors': [],
        'chbpr_errors': {}
    }
    
    # Check if content is not empty
    if not hbpr_content or not hbpr_content.strip():
        result['errors'].append("Input content is empty")
        return result
    
    # Step 1: Check basic regex pattern for full HBPR record
    # Must start with >HBPR: and contain flight info and HBNB number
    hbpr_pattern = r'>HBPR:\s*[^,]+,(\d+)'
    hbpr_match = re.search(hbpr_pattern, hbpr_content)
    
    if not hbpr_match:
        result['errors'].append("Input does not contain valid full HBPR record format (>HBPR: flight_info,hbnb_number)")
        return result
    
    try:
        hbnb_number = int(hbpr_match.group(1))
        result['hbnb_number'] = hbnb_number
    except ValueError:
        result['errors'].append("Invalid HBNB number format")
        return result
    
    # Step 2: Use HBPRProcessor to parse and validate the record format
    try:
        # Create a temporary file-like content for parsing
        lines = hbpr_content.split('\n')
        
        # Find the line that starts with >HBPR:
        hbpr_line_index = -1
        for i, line in enumerate(lines):
            if line.strip().startswith('>HBPR:'):
                hbpr_line_index = i
                break
        
        if hbpr_line_index == -1:
            result['errors'].append("No line starting with '>HBPR:' found in the content")
            return result
        
        # Create HBPRProcessor instance
        processor = HBPRProcessor("temp_input")  # We'll override the file reading
        
        # Use the public parse_full_record method starting from the HBPR line
        parsed_hbnb, parsed_content, next_index = processor.parse_full_record(lines, hbpr_line_index)
        
        if parsed_hbnb is None:
            result['errors'].append("HBPRProcessor failed to parse the full record format")
            return result
        
        if parsed_hbnb != hbnb_number:
            result['errors'].append(f"HBNB number mismatch: regex found {hbnb_number}, parser found {parsed_hbnb}")
            return result
            
    except Exception as e:
        result['errors'].append(f"HBPRProcessor validation failed: {str(e)}")
        return result
    
    # Step 3: Use CHbpr to test the record and check for errors
    try:
        chbpr = CHbpr()
        chbpr.run(hbpr_content)
        
        # Store CHbpr errors for reference
        result['chbpr_errors'] = chbpr.error_msg
        
        # Check specifically for 'Other' category errors (critical errors)
        if chbpr.error_msg.get('Other'):
            result['errors'].append(f"CHbpr validation failed with critical errors: {'; '.join(chbpr.error_msg['Other'])}")
            return result
        
        # Verify HBNB number was extracted correctly
        if chbpr.HbnbNumber != hbnb_number:
            result['errors'].append(f"CHbpr HBNB number mismatch: expected {hbnb_number}, got {chbpr.HbnbNumber}")
            return result
            
    except Exception as e:
        result['errors'].append(f"CHbpr processing failed: {str(e)}")
        return result
    
    # If we reach here, all validations passed
    result['is_valid'] = True
    return result


def process_manual_input():
    """手动输入处理"""
    st.subheader("📄 Manual HBPR Input")
    
    # 搜索根目录中的数据库文件
    try:
        # 显示数据库文件夹建议
        if not os.path.exists("databases"):
            with st.expander("💡 Database Organization Suggestion"):
                st.write("Consider creating a 'databases' folder to organize your database files:")
                if st.button("📁 Create 'databases' folder"):
                    try:
                        os.makedirs("databases", exist_ok=True)
                        st.success("✅ 'databases' folder created!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"❌ Error creating folder: {str(e)}")
        
        # 获取数据库文件列表
        db_files = get_sorted_database_files(sort_by='creation_time', reverse=True)
        
        if not db_files:
            st.error("❌ No HBPR databases found! Please build a database first.")
            st.info("💡 Tip: Consider creating a 'databases' folder to organize your database files.")
            return
        
        # 将子标题和选择框放在同一行
        col1, col2, col3 = st.columns([4, 4, 1])
        
        with col1:
            st.markdown("### 🗄️ Select Database")
        
        with col2:
            # 数据库选择下拉框 - 只显示数据库文件名
            db_names = [os.path.basename(db_file) for db_file in db_files]
            selected_db_name = st.selectbox(
                "Choose database:",
                options=db_names,
                index=0,  # 默认选择最新的数据库
                key="manual_input_db_select"
            )
            # 获取完整的文件路径
            selected_db_file = db_files[db_names.index(selected_db_name)]
        
        with col3:
            # 状态指示器
            if selected_db_file:
                try:
                    temp_db = HbprDatabase(selected_db_file)
                    flight_info = temp_db.get_flight_info()
                    if flight_info:
                        st.markdown("✅")
                    else:
                        st.markdown("⚠️")
                except:
                    st.markdown("⚠️")
            else:
                st.markdown("")
        if not selected_db_file:
            st.error("❌ Please select a database.")
            return
        # 使用选中的数据库
        db = HbprDatabase(selected_db_file)
        st.markdown("---")
        # 输入类型选择
        input_type = st.radio(
            "📝 Input Type:",
            ["Full HBPR Record", "Simple HBNB Record"],
            horizontal=True,
            help="Full HBPR Record: Complete HBPR content with passenger details\nSimple HBNB Record: Just HBNB number for placeholder"
        )
        
        if input_type == "Full HBPR Record":
            # 完整HBPR记录输入
            st.subheader("📄 Full HBPR Record Input")
            
            hbpr_content = st.text_area(
                "Paste full HBPR content here:",
                height=300,
                placeholder="Paste your complete HBPR record content here...\nExample: >HBPR: CA984/25JUL25*LAX,12345\n...",
                key="manual_input_hbpr_content"
            )
            
            # Add two buttons side by side
            col1, col2 = st.columns(2)
            
            with col1:
                replace_clicked = st.button("🔍 Replace the Record", use_container_width=True)
            
            with col2:
                duplicate_clicked = st.button("📋 Create a Duplicate Record", use_container_width=True)
            
            if replace_clicked:
                if hbpr_content.strip():
                    # Step 1: Validate the full HBPR record format
                    st.subheader("🔍 Validating HBPR Record")
                    validation_result = validate_full_hbpr_record(hbpr_content)
                    
                    if not validation_result['is_valid']:
                        st.error("❌ HBPR Record Validation Failed")
                        for error in validation_result['errors']:
                            st.error(f"• {error}")
                        
                        # Show CHbpr errors if available for debugging
                        if validation_result['chbpr_errors']:
                            with st.expander("🔧 Debug Information"):
                                st.write("CHbpr Error Categories:")
                                for category, errors in validation_result['chbpr_errors'].items():
                                    if errors:
                                        st.write(f"**{category}:** {'; '.join(errors)}")
                        return
                    
                    # Validation passed - proceed with processing
                    st.success("✅ HBPR Record Format Validation Passed")
                    
                    try:
                        # Create CHbpr instance for final processing (we know it's valid)
                        chbpr = CHbpr()
                        chbpr.run(hbpr_content)
                        
                        # Verify no critical errors occurred during processing
                        if chbpr.error_msg.get('Other'):
                            st.error("❌ Critical errors occurred during CHbpr processing:")
                            for error in chbpr.error_msg['Other']:
                                st.error(f"• {error}")
                            return
                        
                        # 获取当前数据库的flight_info
                        flight_info = db.get_flight_info()
                        
                        # 获取HBNB的simple_record和full_record信息
                        hbnb_exists = db.check_hbnb_exists(chbpr.HbnbNumber)
                        
                        # 显示处理前的状态信息
                        st.subheader("📋 Processing Information")
                        col1, col2, col3 = st.columns(3)
                        
                        with col1:
                            st.write("**Database Flight Info:**")
                            if flight_info:
                                st.write(f"Flight: {flight_info['flight_number']}")
                                st.write(f"Date: {flight_info['flight_date']}")
                            else:
                                st.write("No flight info available")
                        
                        with col2:
                            st.write("**HBNB Status:**")
                            if hbnb_exists['exists']:
                                if hbnb_exists['full_record']:
                                    st.write(f"HBNB {chbpr.HbnbNumber}: Full record exists")
                                elif hbnb_exists['simple_record']:
                                    st.write(f"HBNB {chbpr.HbnbNumber}: Simple record exists")
                            else:
                                st.write(f"HBNB {chbpr.HbnbNumber}: New record")
                        
                        with col3:
                            st.write("**Validation Status:**")
                            st.success("✅ Format valid")
                            st.success("✅ CHbpr test passed")
                            if chbpr.error_msg:
                                non_critical_errors = sum(1 for k, v in chbpr.error_msg.items() if k != 'Other' and v)
                                if non_critical_errors > 0:
                                    st.warning(f"⚠️ {non_critical_errors} non-critical warnings")
                                else:
                                    st.success("✅ No validation warnings")
                            else:
                                st.success("✅ No validation warnings")
                        
                        # 验证航班信息匹配
                        flight_validation = db.validate_flight_info_match(hbpr_content)
                        
                        if not flight_validation['match']:
                            st.error(f"❌ Flight info mismatch: {flight_validation['reason']}")
                            if 'db_flight' in flight_validation and 'hbpr_flight' in flight_validation:
                                col1, col2 = st.columns(2)
                                with col1:
                                    st.write("**Database Flight:**")
                                    st.write(f"Number: {flight_validation['db_flight']['flight_number']}")
                                    st.write(f"Date: {flight_validation['db_flight']['flight_date']}")
                                with col2:
                                    st.write("**HBPR Flight:**")
                                    st.write(f"Number: {flight_validation['hbpr_flight']['flight_number']}")
                                    st.write(f"Date: {flight_validation['hbpr_flight']['flight_date']}")
                            return
                        
                        # All validations passed - proceed with database operations
                        st.subheader("💾 Database Operations")
                        
                        # 处理记录替换/创建逻辑
                        if hbnb_exists['exists']:
                            # Auto backup existing full record before replacement
                            if hbnb_exists['full_record']:
                                try:
                                    backup_success = db.auto_backup_before_replace(chbpr.HbnbNumber)
                                    if backup_success:
                                        st.info(f"📦 Auto-backed up original record for HBNB {chbpr.HbnbNumber} with original timestamp")
                                    else:
                                        st.warning(f"⚠️ Original record NOT exist for HBNB {chbpr.HbnbNumber}")
                                except Exception as e:
                                    st.warning(f"⚠️ Backup failed for HBNB {chbpr.HbnbNumber}: {str(e)}")
                            
                            if hbnb_exists['simple_record']:
                                # 如果存在简单记录，删除它并创建完整记录
                                db.delete_simple_record(chbpr.HbnbNumber)
                                st.info(f"🔄 Replaced simple record for HBNB {chbpr.HbnbNumber}")
                            
                            # 创建或更新完整记录
                            db.create_full_record(chbpr.HbnbNumber, hbpr_content)
                            if hbnb_exists['full_record']:
                                st.success(f"✅ Replaced full record for HBNB {chbpr.HbnbNumber} (original backed up)")
                            else:
                                st.success(f"✅ Updated record for HBNB {chbpr.HbnbNumber}")
                        else:
                            # 创建新的完整记录
                            db.create_full_record(chbpr.HbnbNumber, hbpr_content)
                            st.success(f"✅ Created new full record for HBNB {chbpr.HbnbNumber}")
                        
                        # 更新验证结果
                        db.update_with_chbpr_results(chbpr)
                        
                        # 更新missing_numbers表
                        try:
                            db.update_missing_numbers_table()
                            st.info("🔄 Updated missing numbers table")
                        except Exception as e:
                            st.warning(f"⚠️ Warning: Could not update missing numbers table: {str(e)}")
                        
                        st.success("✅ Full record processed and stored!")
                        st.info("ℹ️ You can now clear the input box manually or enter new content.")
                        display_processing_results(chbpr)
                        
                        # 设置刷新标志
                        st.session_state.refresh_home = True
                        
                    except Exception as e:
                        st.error(f"❌ Error processing full record: {str(e)}")
                        st.error(traceback.format_exc())
                else:
                    st.warning("⚠️ Please enter HBPR content first.")
            
            if duplicate_clicked:
                if hbpr_content.strip():
                    try:
                        # 处理HBPR记录
                        chbpr = CHbpr()
                        chbpr.run(hbpr_content)
                        
                        # 获取当前数据库的flight_info
                        flight_info = db.get_flight_info()
                        
                        # 获取HBNB的simple_record和full_record信息
                        hbnb_exists = db.check_hbnb_exists(chbpr.HbnbNumber)
                        
                        # 显示处理前的状态信息
                        st.subheader("📋 Duplicate Record Processing Information")
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            st.write("**Database Flight Info:**")
                            if flight_info:
                                st.write(f"Flight: {flight_info['flight_number']}")
                                st.write(f"Date: {flight_info['flight_date']}")
                            else:
                                st.write("No flight info available")
                        
                        with col2:
                            st.write("**HBNB Status:**")
                            if hbnb_exists['exists']:
                                if hbnb_exists['full_record']:
                                    st.write(f"HBNB {chbpr.HbnbNumber}: Full record exists")
                                elif hbnb_exists['simple_record']:
                                    st.write(f"HBNB {chbpr.HbnbNumber}: Simple record exists")
                            else:
                                st.write(f"HBNB {chbpr.HbnbNumber}: New record")
                        
                        # 验证航班信息匹配
                        flight_validation = db.validate_flight_info_match(hbpr_content)
                        
                        if not flight_validation['match']:
                            st.error(f"❌ Flight info mismatch: {flight_validation['reason']}")
                            if 'db_flight' in flight_validation and 'hbpr_flight' in flight_validation:
                                col1, col2 = st.columns(2)
                                with col1:
                                    st.write("**Database Flight:**")
                                    st.write(f"Number: {flight_validation['db_flight']['flight_number']}")
                                    st.write(f"Date: {flight_validation['db_flight']['flight_date']}")
                                with col2:
                                    st.write("**HBPR Flight:**")
                                    st.write(f"Number: {flight_validation['hbpr_flight']['flight_number']}")
                                    st.write(f"Date: {flight_validation['hbpr_flight']['flight_date']}")
                            return
                        
                        # 检查原始记录是否存在
                        if not hbnb_exists['full_record']:
                            st.error(f"❌ Cannot create duplicate: No full record exists for HBNB {chbpr.HbnbNumber}")
                            st.info("💡 Please create the original full record first using 'Replace the Record' button.")
                            return
                        
                        # 创建重复记录
                        db.create_duplicate_record(chbpr.HbnbNumber, chbpr.HbnbNumber, hbpr_content)
                        st.success(f"✅ Created duplicate record for HBNB {chbpr.HbnbNumber}")
                        
                        # 更新验证结果
                        db.update_with_chbpr_results(chbpr)
                        
                        # 更新missing_numbers表
                        try:
                            db.update_missing_numbers_table()
                            st.info("🔄 Updated missing numbers table")
                        except Exception as e:
                            st.warning(f"⚠️ Warning: Could not update missing numbers table: {str(e)}")
                        
                        st.success("✅ Duplicate record processed and stored!")
                        display_processing_results(chbpr)
                        
                        # 设置刷新标志
                        st.session_state.refresh_home = True
                        
                    except Exception as e:
                        st.error(f"❌ Error processing duplicate record: {str(e)}")
                        st.error(traceback.format_exc())
                else:
                    st.warning("⚠️ Please enter HBPR content first.")
        
        else:
            # 简单HBNB记录输入
            st.subheader("🔢 Simple HBNB Record Input")
            
            hbnb_input = st.text_input(
                "HBNB Numbers:",
                placeholder="e.g., 400-410,412,415-420",
                help="Enter HBNB numbers to create simple records. Supports:\n• Single number: 400\n• Range: 400-410\n• Comma-separated list: 400,412,415\n• Mixed: 400-410,412,415-420"
            )
            
            # 解析HBNB输入
            hbnb_numbers = []
            if hbnb_input.strip():
                try:
                    hbnb_numbers = parse_hbnb_input(hbnb_input)
                    if not hbnb_numbers:
                        st.warning("⚠️ No valid HBNB numbers found in input")
                except ValueError as e:
                    st.error(f"❌ Invalid input format: {str(e)}")
            
            # 显示HBNB状态预览（仅显示前5个）
            if hbnb_numbers:
                st.subheader("📋 HBNB Status Preview")
                preview_numbers = hbnb_numbers[:5]
                for hbnb_num in preview_numbers:
                    hbnb_exists = db.check_hbnb_exists(hbnb_num)
                    if hbnb_exists['exists']:
                        if hbnb_exists['full_record']:
                            st.error(f"❌ HBNB {hbnb_num}: Full record exists")
                        else:
                            st.warning(f"⚠️ HBNB {hbnb_num}: Simple record exists")
                    else:
                        st.success(f"✅ HBNB {hbnb_num}: Available")
                
                if len(hbnb_numbers) > 5:
                    st.info(f"ℹ️ ... and {len(hbnb_numbers) - 5} more HBNB numbers")
            
            # 创建简单记录的按钮
            if st.button("➕ Create Simple Records", use_container_width=True):
                if not hbnb_numbers:
                    st.warning("⚠️ Please enter valid HBNB numbers first")
                    return
                
                try:
                    # 获取当前数据库的flight_info
                    flight_info = db.get_flight_info()
                    
                    # 显示处理前的状态信息
                    st.subheader("📋 Processing Information")
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.write("**Database Flight Info:**")
                        if flight_info:
                            st.write(f"Flight: {flight_info['flight_number']}")
                            st.write(f"Date: {flight_info['flight_date']}")
                        else:
                            st.write("No flight info available")
                    
                    with col2:
                        st.write(f"**HBNB Numbers to Process:** {len(hbnb_numbers)}")
                    
                    # 处理每个HBNB数字
                    created_count = 0
                    skipped_count = 0
                    error_count = 0
                    
                    progress_bar = st.progress(0)
                    status_text = st.empty()
                    
                    for i, hbnb_num in enumerate(hbnb_numbers):
                        status_text.text(f"Processing HBNB {hbnb_num}... ({i+1}/{len(hbnb_numbers)})")
                        
                        try:
                            # 检查HBNB是否存在
                            hbnb_exists = db.check_hbnb_exists(hbnb_num)
                            
                            if hbnb_exists['exists']:
                                if hbnb_exists['full_record']:
                                    st.warning(f"⚠️ Skipped HBNB {hbnb_num}: Full record already exists")
                                    skipped_count += 1
                                else:
                                    st.info(f"ℹ️ Skipped HBNB {hbnb_num}: Simple record already exists")
                                    skipped_count += 1
                            else:
                                # 创建简单记录
                                record_line = f"HBPR *,{hbnb_num}"
                                db.create_simple_record(hbnb_num, record_line)
                                st.success(f"✅ Created simple record for HBNB {hbnb_num}")
                                created_count += 1
                        
                        except Exception as e:
                            st.error(f"❌ Error processing HBNB {hbnb_num}: {str(e)}")
                            error_count += 1
                        
                        # 更新进度条
                        progress_bar.progress((i + 1) / len(hbnb_numbers))
                    
                    # 显示最终结果
                    st.subheader("📊 Processing Summary")
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("Created", created_count, delta=f"+{created_count}")
                    with col2:
                        st.metric("Skipped", skipped_count)
                    with col3:
                        st.metric("Errors", error_count, delta=f"-{error_count}" if error_count > 0 else None)
                    
                    if created_count > 0:
                        st.success(f"✅ Successfully created {created_count} simple records!")
                        
                        # 更新missing_numbers表
                        try:
                            db.update_missing_numbers_table()
                            st.info("🔄 Updated missing numbers table")
                        except Exception as e:
                            st.warning(f"⚠️ Warning: Could not update missing numbers table: {str(e)}")
                        
                        # 设置刷新标志
                        st.session_state.refresh_home = True
                    
                except Exception as e:
                    st.error(f"❌ Error creating simple records: {str(e)}")
                    st.error(traceback.format_exc())
        
        # 显示记录列表区域
        st.markdown("---")
        st.subheader("📋 Records in Database")
        
        # 添加视图类型选择
        view_type = st.radio(
            "Select view type:",
            ["Simple Records", "Duplicate Records"],
            horizontal=True,
            help="Simple Records: Regular HBPR records\nDuplicate Records: Records with duplicates"
        )
        
        try:
            if view_type == "Simple Records":
                # 显示简单记录
                simple_records = db.get_simple_records()
                if simple_records:
                    # 创建DataFrame显示简单记录
                    simple_df = pd.DataFrame(simple_records)
                    st.dataframe(simple_df, use_container_width=True, height=200)
                    
                    # 显示统计信息
                    summary = db.get_record_summary()
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        st.metric("Total Records", summary['total_records'])
                    with col2:
                        st.metric("Full Records", summary['full_records'])
                    with col3:
                        st.metric("Simple Records", summary['simple_records'])
                    with col4:
                        st.metric("Validated Records", summary['validated_records'])
                else:
                    st.info("ℹ️ No simple records found in database.")
            
            else:  # Duplicate Records view
                # 获取有重复记录的HBNB号码
                duplicate_hbnbs = db.get_all_duplicate_hbnbs()
                
                if duplicate_hbnbs:
                    # 创建两列布局
                    left_col, right_col = st.columns([2, 3])
                    
                    with left_col:
                        # 选择要查看的HBNB
                        selected_hbnb = st.selectbox(
                            "Select HBNB to view duplicates:",
                            options=duplicate_hbnbs,
                            help="Select an HBNB number to view its duplicate records"
                        )
                        
                        if selected_hbnb:
                            # 获取原始记录和重复记录
                            original_record = db.get_hbpr_record(selected_hbnb)
                            duplicate_records = db.get_duplicate_records(selected_hbnb)
                            
                            # 创建组合数据用于DataFrame显示
                            display_data = []
                            
                            # 添加原始记录（在顶部）
                            display_data.append({
                                'Type': 'Original',
                                'Record ID': 0,  # Use 0 for original record to maintain integer type
                                'Created At': 'Original Record'
                            })
                            
                            # 添加重复记录（按创建时间排序）
                            for dup in duplicate_records:
                                display_data.append({
                                    'Type': 'Duplicate',
                                    'Record ID': int(dup['id']),  # Ensure integer type
                                    'Created At': dup['created_at']
                                })
                            
                            # 显示DataFrame
                            if display_data:
                                records_df = pd.DataFrame(display_data)
                                
                                # Ensure proper data types
                                records_df['Record ID'] = records_df['Record ID'].astype(int)
                                records_df['Type'] = records_df['Type'].astype(str)
                                records_df['Created At'] = records_df['Created At'].astype(str)
                                
                                # 使用st.dataframe创建可选择的表格
                                event = st.dataframe(
                                    records_df,
                                    use_container_width=True,
                                    height=400,
                                    hide_index=True,
                                    on_select="rerun",
                                    selection_mode="single-row",
                                    column_config={
                                        "Record ID": st.column_config.NumberColumn("Record ID", format="%d"),
                                        "Type": "Type",
                                        "Created At": "Created At"
                                    }
                                )
                            
                            # 显示统计信息
                            st.markdown("### 📊 Statistics")
                            col1, col2 = st.columns(2)
                            with col1:
                                st.metric("Original HBNB", selected_hbnb)
                            with col2:
                                st.metric("Duplicates", len(duplicate_records))
                    
                    with right_col:
                        # Record Content区域
                        st.markdown("### 📄 Record Content")
                        
                        if selected_hbnb and display_data:
                            # 检查是否有选中的行
                            if event.selection.rows:
                                selected_row_index = event.selection.rows[0]
                                selected_row = records_df.iloc[selected_row_index]
                                
                                if selected_row['Type'] == 'Original':
                                    # 显示原始记录
                                    record_content = original_record
                                    record_label = f"Original Record (HBNB: {selected_hbnb})"
                                else:
                                    # 显示重复记录
                                    record_id = int(selected_row['Record ID'])
                                    record_content = db.get_duplicate_record_content(record_id)
                                    record_label = f"Duplicate Record (ID: {record_id})"                               
                            else:
                                # 默认显示原始记录
                                record_content = original_record
                                record_label = f"Original Record (HBNB: {selected_hbnb})"
                                st.info("👈 Click on a row to view its content")
                                st.info(f"🔘 **{record_label}** (Default)")
                            
                            # 在文本区域显示记录内容（只读）
                            st.text_area(
                                "Content:",
                                value=record_content,
                                height=422,
                                disabled=True,  # 设置为只读
                                key=f"readonly_content_{selected_hbnb}_{event.selection.rows[0] if event.selection.rows else 'default'}"
                            )
                        else:
                            st.info("Select an HBNB from the left to view records")
                
                else:
                    st.info("ℹ️ No duplicate records found in database.")
                    st.info("💡 Create duplicate records using the 'Create a Duplicate Record' button above.")
                
        except Exception as e:
            st.error(f"❌ Error loading records: {str(e)}")
    
    except Exception as e:
        st.error(f"❌ Error accessing databases: {str(e)}")
        st.info("💡 Please build a database first in the Database Management page.")



def show_view_results():
    """显示结果查看页面"""
    # Apply settings
    apply_global_settings()
    
    st.header("📊 View Processing Results")
    
    try:
        # 获取数据库文件列表
        db_files = get_sorted_database_files(sort_by='creation_time', reverse=True)
        
        if not db_files:
            st.error("❌ No database files found.")
            st.info("💡 Please build a database first in the Database Management page.")
            return
        
        # 数据库选择下拉框 - 只显示数据库文件名
        db_names = [os.path.basename(db_file) for db_file in db_files]
        selected_db_name = st.selectbox(
            "Select Database:", 
            options=db_names,
            index=0,  # 默认选择最新的数据库
            key="view_results_db_select"
        )
        
        # 获取完整的文件路径
        selected_db_file = db_files[db_names.index(selected_db_name)]
        db = HbprDatabase(selected_db_file)
        
        tab1, tab2, tab3 = st.tabs(["📈 Statistics", "📋 Records Table", "📤 Export Data"])
        
        with tab1:
            show_statistics(db)
        
        with tab2:
            show_records_table(db)
        
        with tab3:
            show_export_options(db)
    
    except Exception as e:
        st.error(f"❌ Database not available: {str(e)}")
        st.info("💡 Please build a database first in the Database Management page.")


def show_statistics(db):
    """显示统计信息"""
    st.subheader("📈 HBNB Range Statistics")
    
    range_info = db.get_hbnb_range_info()
    missing_numbers = db.get_missing_hbnb_numbers()
    
    # 主要指标
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("HBNB Range", f"{range_info['min']} - {range_info['max']}")
    with col2:
        st.metric("Total Expected", range_info['total_expected'])
    with col3:
        st.metric("Total Found", range_info['total_found'])
    with col4:
        st.metric("Missing Numbers", len(missing_numbers))
    
    # 完整性率
    if range_info['total_expected'] > 0:
        completeness_rate = (range_info['total_found'] / range_info['total_expected']) * 100
        missing_rate = (len(missing_numbers) / range_info['total_expected']) * 100
        
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Completeness Rate", f"{completeness_rate:.1f}%")
        with col2:
            st.metric("Missing Rate", f"{missing_rate:.1f}%")
    
    # 显示缺失号码表格
    if missing_numbers:
        st.subheader("🚫 Missing HBNB Numbers")
        # 分页显示缺失号码
        items_per_page = 30
        total_pages = (len(missing_numbers) + items_per_page - 1) // items_per_page
        
        if total_pages > 1:
            page = st.selectbox("Page:", range(1, total_pages + 1), key="stats_missing_page")
            start_idx = (page - 1) * items_per_page
            end_idx = min(start_idx + items_per_page, len(missing_numbers))
            page_missing = missing_numbers[start_idx:end_idx]
        else:
            page_missing = missing_numbers
        
        # 创建缺失号码的DataFrame
        missing_df = pd.DataFrame({
            'Missing HBNB Numbers': page_missing
        })
        
        st.dataframe(missing_df, use_container_width=True)
        
        if total_pages > 1:
            st.info(f"Showing page {page} of {total_pages} ({len(page_missing)} of {len(missing_numbers)} missing numbers)")
    else:
        st.success("✅ No missing HBNB numbers found!")


def show_records_table(db):
    """显示记录表格"""
    st.subheader("📋 Processed Records")
    
    try:
        conn = sqlite3.connect(db.db_file)
        
        # 查询已处理的记录，包括properties、ckin_msg和asvc_msg字段
        df = pd.read_sql_query("""
            SELECT hbnb_number, boarding_number, name, seat, class, destination,
                   bag_piece, bag_weight, ff, ckin_msg, properties, asvc_msg, error_count
            FROM hbpr_full_records 
            WHERE is_validated = 1
            ORDER BY hbnb_number
        """, conn)
        conn.close()
        if df.empty:
            st.info("ℹ️ No processed records found.")
            return
        
        
        # 提取FF Level（从FF字段中提取最后的字母）
        def extract_ff_level(ff_value):
            if pd.isna(ff_value) or ff_value == '':
                return 'N/A'
            # 提取FF号码最后的字母，如 "CA 050021619897/B" -> "B"
            parts = ff_value.split('/')
            if len(parts) > 1:
                return parts[-1]
            return 'N/A'
        

        # 添加FF Level列
        df['ff_level'] = df['ff'].apply(extract_ff_level)
        
        # 提取CKIN类型（从CKIN_MSG中提取所有CKIN类型）
        def extract_ckin_type(ckin_msg):
            if pd.isna(ckin_msg) or ckin_msg == '':
                return ''
            # 分割CKIN消息并提取所有CKIN类型
            ckin_list = [msg.strip() for msg in ckin_msg.split(';') if msg.strip()]
            ckin_types = []
            for ckin_msg_item in ckin_list:
                # 匹配 CKIN 后跟 4个字母数字字符，然后是非数字字符
                import re
                match = re.search(r'CKIN\s+([A-Z0-9]{4})[^0-9]', ckin_msg_item)
                if match:
                    ckin_types.append(match.group(1))
            return ckin_types

        # 添加CKIN类型列（包含所有CKIN类型，用逗号分隔）
        df['ckin_types'] = df['ckin_msg'].apply(lambda x: ', '.join(extract_ckin_type(x)) if extract_ckin_type(x) else '')
        
        # 收集所有唯一的CKIN类型用于过滤器
        all_ckin_types = set()
        for ckin_types_str in df['ckin_types'].dropna():
            if ckin_types_str != '':
                types_list = [t.strip() for t in ckin_types_str.split(',') if t.strip()]
                all_ckin_types.update(types_list)
        
        # 过滤选项
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            filter_class = st.multiselect("Filter by Class:", df['class'].dropna().unique())
        
        with col2:
            # FF Level过滤器
            ff_levels = sorted(df['ff_level'].dropna().unique())
            filter_ff_level = st.multiselect("Filter by FF Level:", ff_levels)
        
        with col3:
            # CKIN类型过滤器
            available_ckin_types = sorted(list(all_ckin_types))
            filter_ckin_type = st.multiselect("Filter by CKIN Type:", available_ckin_types)
        
        with col4:
            # Properties过滤器 - 替换destination过滤器
            # 从properties字段中提取所有唯一的属性
            all_properties = set()
            for properties_str in df['properties'].dropna():
                if properties_str:
                    properties_list = [prop.strip() for prop in properties_str.split(',') if prop.strip()]
                    all_properties.update(properties_list)
            
            available_properties = sorted(list(all_properties))
            filter_properties = st.multiselect("Filter by Properties:", available_properties)
        
        # 应用过滤器
        filtered_df = df.copy()
        
        if filter_class:
            filtered_df = filtered_df[filtered_df['class'].isin(filter_class)]
        
        if filter_ff_level:
            filtered_df = filtered_df[filtered_df['ff_level'].isin(filter_ff_level)]
        
        if filter_ckin_type:
            # 过滤包含选定CKIN类型的记录
            def has_ckin_type(ckin_types_str, target_ckin_types):
                if pd.isna(ckin_types_str) or ckin_types_str == '':
                    return False
                types_list = [t.strip() for t in ckin_types_str.split(',') if t.strip()]
                return any(ckin_type in types_list for ckin_type in target_ckin_types)
            
            filtered_df = filtered_df[filtered_df['ckin_types'].apply(
                lambda x: has_ckin_type(x, filter_ckin_type)
            )]
        
        if filter_properties:
            # 过滤包含选定属性的记录
            def has_property(properties_str, target_properties):
                if pd.isna(properties_str) or properties_str == '':
                    return False
                properties_list = [prop.strip() for prop in properties_str.split(',') if prop.strip()]
                return any(prop in properties_list for prop in target_properties)
            
            filtered_df = filtered_df[filtered_df['properties'].apply(
                lambda x: has_property(x, filter_properties)
            )]
        
        # 显示表格（不显示ff_level和ckin_types列，因为它们只是用于过滤）
        display_df = filtered_df.drop(columns=['ff_level', 'ckin_types'])
        
        st.dataframe(
            display_df,
            use_container_width=True,
            hide_index=True,  # 隐藏自动序列号
            column_config={
                "hbnb_number": st.column_config.NumberColumn("HBNB", format="%d"),
                "boarding_number": st.column_config.NumberColumn("BN", format="%d"),
                "name": "Name",
                "seat": "Seat",
                "class": "Class",
                "destination": "Destination", 
                "bag_piece": st.column_config.NumberColumn("Bag Pieces", format="%d"),
                "bag_weight": st.column_config.NumberColumn("Bag Weight", format="%d kg"),
                "ff": "FF Number",
                "properties": "Properties",
                "ckin_msg": st.column_config.TextColumn("CKIN Messages", max_chars=100),
                "asvc_msg": st.column_config.TextColumn("ASVC Messages", max_chars=100),
                "error_count": st.column_config.NumberColumn("Errors", format="%d")
            }
        )
        
        st.info(f"📊 Showing {len(filtered_df)} of {len(df)} records")
    
    except Exception as e:
        st.error(f"❌ Error loading records: {str(e)}")


def show_export_options(db):
    """显示导出选项"""
    st.subheader("📤 Export Data")
    
    try:
        conn = sqlite3.connect(db.db_file)
        
        # 获取所有已处理的记录
        df = pd.read_sql_query("""
            SELECT * FROM hbpr_full_records 
            WHERE is_validated = 1
            ORDER BY hbnb_number
        """, conn)
        
        conn.close()
        
        if df.empty:
            st.info("ℹ️ No processed records to export.")
            return
        
        col1, col2 = st.columns(2)
        
        with col1:
            # CSV导出
            csv_data = df.to_csv(index=False)
            st.download_button(
                label="📥 Download as CSV",
                data=csv_data,
                file_name=f"hbpr_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv",
                use_container_width=True
            )
        
        with col2:
            # Excel导出
            from io import BytesIO
            excel_buffer = BytesIO()
            df.to_excel(excel_buffer, index=False, engine='openpyxl')
            excel_data = excel_buffer.getvalue()
            st.download_button(
                label="📊 Download as Excel",
                data=excel_data,
                file_name=f"hbpr_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )
        
        # 显示导出预览
        st.subheader("👀 Export Preview")
        st.dataframe(df.head(10), use_container_width=True)
        st.info(f"📊 Total records ready for export: {len(df)}")
    
    except Exception as e:
        st.error(f"❌ Error preparing export: {str(e)}")


def show_settings():
    """显示设置页面"""
    st.header("⚙️ Settings")
    
    # Initialize settings in session state
    if 'settings' not in st.session_state:
        st.session_state.settings = {
            'theme': 'Auto',
            'font_family': 'Courier New',
            'font_size_percent': 100,
            'show_debug': False,
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
            st.success("✅ Settings saved successfully!")
            # Force a rerun to apply settings immediately
            st.rerun()
        
        # Reset settings
        if st.button("🔄 Reset to Defaults"):
            st.session_state.settings = {
                'font_family': 'Courier New',
                'font_size_percent': 100,
            }
            st.success("✅ Settings reset to defaults!")
            # Force a rerun to apply settings immediately
            st.rerun()
    
    with tab2:
        st.subheader("📋 About FlightCheck")
        
        st.markdown("""
        **Version:** 0.6 
                    
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
        """)


def get_sorted_database_files(sort_by='creation_time', reverse=True):
    """
    获取排序后的数据库文件列表
    
    Args:
        sort_by (str): 排序方式 - 'creation_time', 'modification_time', 'name'
        reverse (bool): 是否反向排序（True为最新的在前）
    
    Returns:
        list: 排序后的数据库文件路径列表
    """
    # 搜索数据库文件，优先查找databases文件夹
    db_files = []
    if os.path.exists("databases"):
        db_files = glob.glob("databases/*.db")
    
    # 如果databases文件夹中没有找到，则搜索根目录
    if not db_files:
        db_files = glob.glob("*.db")
    
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


def create_database_selectbox(label="Select database:", key=None, default_index=0, show_flight_info=False):
    """
    创建数据库选择下拉框
    
    Args:
        label (str): 下拉框标签
        key (str): Streamlit组件key
        default_index (int): 默认选中的索引（0为最新的数据库）
        show_flight_info (bool): 是否显示航班信息
    
    Returns:
        tuple: (selected_db_file, db_files_list) 或 (None, []) 如果没有数据库
    """
    db_files = get_sorted_database_files(sort_by='creation_time', reverse=True)
    
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


if __name__ == "__main__":
    main() 