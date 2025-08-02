#!/usr/bin/env python3
"""
Database management page for HBPR UI - Database operations and maintenance
"""

import streamlit as st
import pandas as pd
import os
import glob
import sqlite3
import traceback
from ui.common import apply_global_settings, create_database_selectbox
from scripts.hbpr_info_processor import HbprDatabase
from scripts.hbpr_list_processor import HBPRProcessor


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