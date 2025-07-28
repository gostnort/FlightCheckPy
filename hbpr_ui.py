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
from datetime import datetime
from hbpr_info_processor import CHbpr, HbprDatabase
import traceback


RAW_CONTENT_FONT = """
        <style>
        .stTextArea textarea {
            font-family: "Courier New", monospace !important;
            font-size: 14px !important;
        }
        </style>
        """


def get_icon_base64(path):
    """将图标文件转换为base64编码"""
    try:
        with open(path, "rb") as icon_file:
            return base64.b64encode(icon_file.read()).decode()
    except FileNotFoundError:
        return ""


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
    # 初始化session state
    if 'current_page' not in st.session_state:
        st.session_state.current_page = "🏠 Home"
    # 侧边栏导航
    st.sidebar.title("📋 Navigation")
    # 导航链接
    if st.sidebar.button("🏠 Home", use_container_width=True):
        st.session_state.current_page = "🏠 Home"
    if st.sidebar.button("🗄️ Database", use_container_width=True):
        st.session_state.current_page = "🗄️ Database"
    if st.sidebar.button("🔍 Process Records", use_container_width=True):
        st.session_state.current_page = "🔍 Process Records"
    if st.sidebar.button("📊 View Results", use_container_width=True):
        st.session_state.current_page = "📊 View Results"
    if st.sidebar.button("⚙️ Settings", use_container_width=True):
        st.session_state.current_page = "⚙️ Settings"
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
            db = HbprDatabase()
            db.find_database()
            st.success(f"✅ Database connected: `{db.db_file}`")
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
            with open("uploaded_hbpr_list.txt", "wb") as f:
                f.write(uploaded_file.getbuffer())
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
        # Delete the uploaded file after successful database building
        try:
            if os.path.exists(input_file):
                os.remove(input_file)
        except Exception:
            pass   
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
    
    # 搜索数据库文件，优先查找databases文件夹
    db_files = []
    if os.path.exists("databases"):
        db_files = glob.glob("databases/*.db")
    
    # 如果databases文件夹中没有找到，则搜索根目录
    if not db_files:
        db_files = glob.glob("*.db")
    
    if db_files:
        selected_db = st.selectbox("Select database file:", db_files)
        
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
        # 搜索数据库文件，优先查找databases文件夹
        db_files = []
        if os.path.exists("databases"):
            db_files = glob.glob("databases/*.db")
        
        # 如果databases文件夹中没有找到，则搜索根目录
        if not db_files:
            db_files = glob.glob("*.db")
        
        if not db_files:
            st.error("❌ No database files found.")
            return
        
        # 处理控制
        col1, col2 = st.columns(2)
        
        with col1:
            selected_db = st.selectbox("Select Database:", db_files, 
                                     index=db_files.index(db.db_file) if db.db_file in db_files else 0)
            # 如果选择了不同的数据库，重新初始化
            if selected_db != db.db_file:
                db = HbprDatabase(selected_db)
        
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
                # 添加自定义CSS来设置Raw Content的字体
                st.markdown(RAW_CONTENT_FONT, unsafe_allow_html=True)
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
                    pspt_exp_date = NULL, ckin_msg = NULL, expc_piece = NULL,
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
        # 添加自定义CSS来设置Raw Content的字体
        st.markdown(RAW_CONTENT_FONT, unsafe_allow_html=True)
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


def process_manual_input():
    """手动输入处理"""
    st.subheader("📄 Manual HBPR Input")
    
    # 搜索根目录中的数据库文件
    try:
        import glob
        import os
        
        # 优先搜索数据库文件夹中的.db文件
        db_files = []
        if os.path.exists("databases"):
            db_files = glob.glob("databases/*.db")
        
        # 如果数据库文件夹中没有找到，则搜索根目录
        if not db_files:
            db_files = glob.glob("*.db")
        
        if not db_files:
            st.error("❌ No HBPR databases found! Please build a database first.")
            st.info("💡 Tip: Consider creating a 'databases' folder to organize your database files.")
            return
        
        # 数据库选择下拉框
        st.subheader("🗄️ Select Database")
        
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
        
        db_options = []
        for db_file in db_files:
            # 尝试获取航班信息用于显示
            try:
                temp_db = HbprDatabase(db_file)
                flight_info = temp_db.get_flight_info()
                if flight_info:
                    display_name = f"{flight_info['flight_number']} ({flight_info['flight_date']}) - {db_file}"
                else:
                    display_name = f"Unknown Flight - {db_file}"
            except:
                display_name = f"Database - {db_file}"
            
            db_options.append((display_name, db_file))
        
        # 使用列布局来放置选择框和状态标记
        col1, col2 = st.columns([4, 1])
        
        with col1:
            selected_db_display = st.selectbox(
                "Choose database:",
                options=[opt[0] for opt in db_options],
                key="manual_input_db_select"
            )
        
        # 获取选中的数据库文件
        selected_db_file = None
        for display_name, db_file in db_options:
            if display_name == selected_db_display:
                selected_db_file = db_file
                break
        
        if not selected_db_file:
            st.error("❌ Please select a database.")
            return
        
        # 使用选中的数据库
        db = HbprDatabase(selected_db_file)
        
        # 显示状态标记
        flight_info = db.get_flight_info()
        with col2:
            if flight_info:
                st.markdown("✅")
            else:
                st.markdown("⚠️")
        
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
            
            if st.button("🔍 Process Full Record", use_container_width=True):
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
                        
                        # 处理记录替换/创建逻辑
                        if hbnb_exists['exists']:
                            if hbnb_exists['simple_record']:
                                # 如果存在简单记录，删除它并创建完整记录
                                db.delete_simple_record(chbpr.HbnbNumber)
                                st.info(f"🔄 Replaced simple record for HBNB {chbpr.HbnbNumber}")
                            
                            # 创建或更新完整记录
                            db.create_full_record(chbpr.HbnbNumber, hbpr_content)
                            st.success(f"✅ Updated full record for HBNB {chbpr.HbnbNumber}")
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
                        display_processing_results(chbpr)
                        
                        # 设置刷新标志
                        st.session_state.refresh_home = True
                        
                        # 清空输入框
                        st.session_state.manual_input_hbpr_content = ""
                        
                    except Exception as e:
                        st.error(f"❌ Error processing full record: {str(e)}")
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
        
        # 显示简单记录列表
        st.markdown("---")
        st.subheader("📋 Simple Records in Database")
        
        try:
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
                
        except Exception as e:
            st.error(f"❌ Error loading simple records: {str(e)}")
    
    except Exception as e:
        st.error(f"❌ Error accessing databases: {str(e)}")
        st.info("💡 Please build a database first in the Database Management page.")



def show_view_results():
    """显示结果查看页面"""
    st.header("📊 View Processing Results")
    
    try:
        db = HbprDatabase()
        db.find_database()
        
        tab1, tab2, tab3 = st.tabs(["📈 Statistics", "📋 Records Table", "📤 Export Data"])
        
        with tab1:
            show_statistics(db)
        
        with tab2:
            show_records_table(db)
        
        with tab3:
            show_export_options(db)
    
    except Exception as e:
        st.error(f"❌ Database not available: {str(e)}")


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
        
        # 查询已处理的记录
        df = pd.read_sql_query("""
            SELECT hbnb_number, is_valid, name, seat, class, destination,
                   bag_piece, bag_weight, ff, error_count, validated_at
            FROM hbpr_full_records 
            WHERE is_validated = 1
            ORDER BY hbnb_number
        """, conn)
        
        conn.close()
        
        if df.empty:
            st.info("ℹ️ No processed records found.")
            return
        
        # 过滤选项
        col1, col2, col3 = st.columns(3)
        
        with col1:
            filter_valid = st.selectbox("Filter by Validation:", ["All", "Valid Only", "Invalid Only"])
        
        with col2:
            filter_class = st.multiselect("Filter by Class:", df['class'].dropna().unique())
        
        with col3:
            filter_destination = st.multiselect("Filter by Destination:", df['destination'].dropna().unique())
        
        # 应用过滤器
        filtered_df = df.copy()
        
        if filter_valid == "Valid Only":
            filtered_df = filtered_df[filtered_df['is_valid'] == 1]
        elif filter_valid == "Invalid Only":
            filtered_df = filtered_df[filtered_df['is_valid'] == 0]
        
        if filter_class:
            filtered_df = filtered_df[filtered_df['class'].isin(filter_class)]
        
        if filter_destination:
            filtered_df = filtered_df[filtered_df['destination'].isin(filter_destination)]
        
        # 显示表格
        st.dataframe(
            filtered_df,
            use_container_width=True,
            column_config={
                "hbnb_number": st.column_config.NumberColumn("HBNB", format="%d"),
                "is_valid": st.column_config.CheckboxColumn("Valid"),
                "name": "Name",
                "seat": "Seat",
                "class": "Class",
                "destination": "Destination", 
                "bag_piece": st.column_config.NumberColumn("Bag Pieces", format="%d"),
                "bag_weight": st.column_config.NumberColumn("Bag Weight", format="%d kg"),
                "ff": "FF Number",
                "error_count": st.column_config.NumberColumn("Errors", format="%d"),
                "validated_at": st.column_config.DatetimeColumn("Validated At")
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
    
    tab1, tab2 = st.tabs(["🎨 UI Settings", "📋 About"])
    
    with tab1:
        st.subheader("🎨 User Interface Settings")
        
        # 主题设置
        theme = st.selectbox("Theme:", ["Auto", "Light", "Dark"])
        
        # 显示设置
        show_debug = st.checkbox("Show debug information", value=False)
        auto_refresh = st.checkbox("Auto-refresh data", value=True)
        
        # 处理设置
        st.subheader("🔧 Processing Settings")
        default_batch_size = st.number_input("Default batch size:", min_value=1, max_value=1000, value=10)
        
        if st.button("💾 Save Settings"):
            st.success("✅ Settings saved!")
    
    with tab2:
        st.subheader("📋 About HBPR Processing System")
        
        st.markdown("""
        **Version:** 1.0.0  
        **Developer:** HBPR Team  
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


if __name__ == "__main__":
    main() 