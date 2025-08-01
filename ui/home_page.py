#!/usr/bin/env python3
"""
Home page for HBPR UI - System overview and quick actions
"""

import streamlit as st
import pandas as pd
from .common import apply_global_settings, get_sorted_database_files, HbprDatabase


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