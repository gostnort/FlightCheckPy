#!/usr/bin/env python3
"""
Database management page for HBPR UI - Database operations and maintenance
"""

import streamlit as st
import pandas as pd
import sqlite3
import os
import traceback
from ui.db_management import apply_global_settings, db_manager, save_memory_database_to_file
from scripts.hbpr_list_processor import HBPRProcessor


def show_database_management():
    """显示数据库管理页面"""
    # Apply settings
    apply_global_settings()
    
    tab1, tab2, tab3, tab4 = st.tabs(["📥 Build Database", "📈 Statistics", "🔍 Database Info", "🧹 Maintenance"])
    
    with tab1:
        build_database_ui()

    with tab2:
        show_statistics()
    with tab3:
        st.subheader("🔍 Database Information")
        show_database_info()
    with tab4:
        st.subheader("🧹 Database Maintenance")
        show_database_maintenance()


def build_database_ui():
    """构建数据库的UI函数"""
    st.subheader("📥 Build Database from HBPR List")

    uploaded_file = st.file_uploader(
        "Choose HBPR list file:", 
        type=['txt'],
        help="Upload your HBPR list text file"
    )

    if uploaded_file is not None:
        file_content = uploaded_file.getvalue().decode("utf-8")
        
        st.subheader("Enter New Database Filename")
        db_name_input = st.text_input(
            "New DB Filename (e.g., CA984_25JUL25.db):", 
            "",
            help="Filename must follow the pattern FLTNUM_DDMMMYY.db"
        )

        if st.button("🔨 Build and Save Database", use_container_width=True):
            if db_name_input and db_name_input.endswith(".db"):
                db_folder = "databases"
                if not os.path.exists(db_folder):
                    os.makedirs(db_folder)
                
                new_db_path = os.path.join(db_folder, db_name_input)

                try:
                    with st.spinner(f"Building new database '{db_name_input}'..."):
                        # 1. Create a new temporary in-memory database
                        temp_conn = sqlite3.connect(":memory:")
                        
                        # 2. Process the uploaded file into the temp in-memory DB
                        processor = HBPRProcessor(temp_conn)
                        processor.create_tables_if_not_exist()
                        processor.process(file_content)
                        
                        # 3. Save the in-memory content to the new file
                        backup_conn = sqlite3.connect(new_db_path)
                        temp_conn.backup(backup_conn)
                        backup_conn.close()
                        temp_conn.close()

                        st.success(f"✅ Successfully built and saved database to '{new_db_path}'")
                        st.info("🔄 Refreshing database list...")
                        
                        # Optionally, switch to the new DB immediately
                        st.session_state.current_db_path = new_db_path
                        st.session_state.current_db_name = os.path.basename(new_db_path)
                        db_manager.load_database(new_db_path)
                        st.rerun()

                except Exception as e:
                    st.error(f"❌ Error building database: {str(e)}")
                    st.text(traceback.format_exc())
            else:
                st.error("❌ Please enter a valid database filename ending with .db")


def show_database_info():
    """显示数据库信息"""
    if not db_manager.is_available():
        st.warning("⚠️ No database loaded in memory.")
        return

    try:
        db = db_manager.get_database()
        conn = db.get_connection()
        cursor = conn.cursor()
        
        db_name = db_manager.get_database_name()
        
        with st.expander(f"📁 {db_name} (In-Memory)"):
            try:
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
                    # Use reusable components for consistent display
                    from ui.components.main_stats import get_and_display_main_statistics, display_detailed_range_info
                    all_stats = get_and_display_main_statistics(db)
                    
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
            except Exception as e:
                st.error(f"Error reading database: {str(e)}")
    except Exception as e:
        st.error(f"Error accessing database manager: {str(e)}")


def show_database_maintenance():
    """显示数据库维护选项"""
    if not db_manager.is_available():
        st.info("ℹ️ No database selected. Please select a database from the sidebar.")
        return

    st.info("💡 If you encounter errors, you can perform maintenance on the in-memory database.")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        # 保存数据库按钮
        if st.button("💾 Save Database to File", use_container_width=True):
            if save_memory_database_to_file():
                st.success("✅ Database saved successfully!")
            else:
                st.error("❌ Error saving database.")
    
    with col2:
        # 更新missing_numbers表按钮
        if st.button("🔄 Update Missing Numbers", use_container_width=True):
            try:
                db = db_manager.get_database()
                db.update_missing_numbers_table()
                st.success("✅ Missing numbers table updated successfully!")
            except Exception as e:
                st.error(f"❌ Error updating missing numbers table: {str(e)}")
    
    with col3:
        # 数据库清理按钮
        if st.button("🧹 Clean Database Data", use_container_width=True):
            st.warning("Cleaning should be done on the source file before loading.")
            # try:
            #     clean_database_data(db_manager.get_database().get_connection())
            # except Exception as e:
            #     st.error(f"❌ Error cleaning database: {str(e)}")


def clean_database_data(conn: sqlite3.Connection):
    """清理数据库中的问题数据"""
    st.warning("In-memory database cleaning is not fully implemented yet.")
    # This function would need to be adapted to work on a connection
    # instead of a file path.
    # try:
    #     st.info("🔄 正在清理数据库数据...")
        
    #     # 导入清理函数
    #     from scripts.clean_database_data import clean_database_file
        
    #     # 执行清理
    #     success = clean_database_file(db_file, backup=True)
        
    #     if success:
    #         st.success("✅ 数据库数据清理完成！")
    #         st.info("💡 现在可以尝试导出数据了")
    #         st.rerun()
    #     else:
    #         st.error("❌ 数据库数据清理失败")
            
    # except ImportError:
    #     st.error("❌ 清理工具未找到，请确保 scripts/clean_database_data.py 文件存在")
    # except Exception as e:
    #     st.error(f"❌ 清理过程中发生错误: {str(e)}")
    #     st.error("💡 请检查错误信息并重试")


def show_statistics():
    """显示统计信息"""
    if not db_manager.is_available():
        st.error("❌ No database loaded.")
        st.info("💡 Please select a database from the sidebar or build one first.")
        return

    try:
        db = db_manager.get_database()
        
        # 添加刷新按钮
        col1, col2, col3 = st.columns([3, 1, 1])
        with col1:
            st.subheader("📈 Statistics")
        with col2:
            if st.button("🔄 Refresh", use_container_width=True):
                st.rerun()
        with col3:
            debug_trigger = st.toggle("🔍 Debug", value=False)
        
        # 显示调试信息（如果触发）
        if debug_trigger:
            from ui.components.home_metrics import get_debug_summary
            # Debug summary needs a file path, so this might not work as expected
            # with an in-memory database.
            st.info("Debug summary may not be accurate for in-memory databases.")

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

