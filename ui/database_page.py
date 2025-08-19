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
from ui.common import apply_global_settings, get_current_database
from scripts.hbpr_info_processor import HbprDatabase
from scripts.hbpr_list_processor import HBPRProcessor


def show_database_management():
    """显示数据库管理页面"""
    # Apply settings
    apply_global_settings()
    tab1, tab2, tab3, tab4 = st.tabs(["📥 Build Database", "📈 Statistics", "🔍 Database Info", "🧹 Maintenance"])   
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
        show_statistics()
    with tab3:
        st.subheader("🔍 Database Information")
        show_database_info()
    with tab4:
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
        # Display main statistics using reusable component
        from ui.components.main_stats import get_and_display_main_statistics, display_detailed_range_info
        all_stats = get_and_display_main_statistics(db)
        
        # Display detailed range information specific to database page
        if all_stats:
            display_detailed_range_info(all_stats)
            missing_numbers = all_stats.get('missing_numbers', [])
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
                        # Use reusable components for consistent display
                        from ui.components.main_stats import get_and_display_main_statistics, display_detailed_range_info
                        all_stats = get_and_display_main_statistics(db_instance)
                        
                        # Display detailed range information
                        if all_stats:
                            display_detailed_range_info(all_stats)
                            missing_numbers = all_stats.get('missing_numbers', [])
                            
                            # Show missing numbers details
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
    selected_db = get_current_database()
    if selected_db:
        st.info("💡 如果导出数据时遇到错误，可以尝试清理数据库中的问题字符")
        
        col1, col2, col3 = st.columns(3)
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
        
        with col3:
            # 数据库清理按钮
            if st.button("🧹 Clean Database Data", use_container_width=True):
                try:
                    clean_database_data(selected_db)
                except Exception as e:
                    st.error(f"❌ Error cleaning database: {str(e)}")
    else:
        st.info("ℹ️ No database selected. Please select a database from the sidebar or create one first.")


def clean_database_data(db_file: str):
    """清理数据库中的问题数据"""
    try:
        st.info("🔄 正在清理数据库数据...")
        
        # 导入清理函数
        from scripts.clean_database_data import clean_database_file
        
        # 执行清理
        success = clean_database_file(db_file, backup=True)
        
        if success:
            st.success("✅ 数据库数据清理完成！")
            st.info("💡 现在可以尝试导出数据了")
            st.rerun()
        else:
            st.error("❌ 数据库数据清理失败")
            
    except ImportError:
        st.error("❌ 清理工具未找到，请确保 scripts/clean_database_data.py 文件存在")
    except Exception as e:
        st.error(f"❌ 清理过程中发生错误: {str(e)}")
        st.error("💡 请检查错误信息并重试")


def show_statistics():
    """显示统计信息"""
    # 获取当前选中的数据库
    selected_db_file = get_current_database()
    if not selected_db_file:
        st.error("❌ No database selected.")
        st.info("💡 Please select a database from the sidebar or build one first.")
        return
    try:
        db = HbprDatabase(selected_db_file)
        # 添加刷新按钮
        col1, col2, col3 = st.columns([3, 1, 1])
        with col1:
            st.subheader("📈 Statistics")
        with col2:
            if st.button("🔄 Refresh", use_container_width=True):
                # 强制刷新所有统计信息
                db.invalidate_statistics_cache()
                st.rerun()
        with col3:
            debug_trigger = st.toggle("🔍 Debug", value=False)
        
        # 显示调试信息（如果触发）
        if debug_trigger:
            from ui.components.home_metrics import get_debug_summary
            debug_info = get_debug_summary(selected_db_file)
            st.info(debug_info)
        # Use reusable components for consistent display
        from ui.components.main_stats import get_and_display_main_statistics
        all_stats = get_and_display_main_statistics(db)
        
        # Extract missing numbers for the detailed display below
        missing_numbers = all_stats.get('missing_numbers', []) if all_stats else []
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
    except Exception as e:
        st.error(f"❌ Database not available: {str(e)}")
        st.info("💡 Please select a database from the sidebar or build one first.")

