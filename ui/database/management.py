#!/usr/bin/env python3
"""
数据库管理功能 - 选择、保存、文件夹管理等
"""

import os
import streamlit as st
import tkinter as tk
from tkinter import filedialog
from pathlib import Path
from ui.common import (
    get_db_port_client,
    is_db_available,
    get_database_name,
    load_database,
    trigger_auto_save
)


def show_database_management():
    """显示数据库管理界面"""
    st.subheader("🗄️ Database Management")
    
    # 显示当前数据库信息
    current_db = get_database_name()
    if current_db and current_db != "N/A" and current_db != "Error":
        st.info(f"📂 当前数据库: **{current_db}**")
    else:
        st.warning("⚠️ 未加载数据库 - 可以从下方选择或浏览文件夹")
    
    st.markdown("---")
    
    # 数据库操作
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("### 📁 文件夹管理")
        render_folder_management()
    
    with col2:
        st.markdown("### 💾 数据库操作")
        render_database_operations()
    
    with col3:
        st.markdown("### 📊 数据库信息")
        render_database_info()


def render_folder_management():
    """渲染文件夹管理部分"""
    custom_folder = st.session_state.get('custom_db_folder')
    
    # 显示当前文件夹
    if custom_folder:
        st.info(f"📁 当前: {Path(custom_folder).name}")
    else:
        st.info("📁 当前: databases (默认)")
    
    # 选择文件夹按钮
    if st.button("🔍 选择文件夹", use_container_width=True):
        try:
            root = tk.Tk()
            root.withdraw()
            root.wm_attributes('-topmost', 1)
            
            folder_path = filedialog.askdirectory(
                title="选择数据库文件夹",
                initialdir=custom_folder or os.getcwd()
            )
            
            root.destroy()
            
            if folder_path:
                st.session_state.custom_db_folder = folder_path
                st.success(f"✅ 已选择: {Path(folder_path).name}")
                st.rerun()
                
        except Exception as e:
            st.error(f"❌ 错误: {str(e)}")
    
    # 重置为默认文件夹
    if custom_folder:
        if st.button("🔄 使用默认文件夹", use_container_width=True):
            del st.session_state['custom_db_folder']
            st.success("✅ 已切换到默认文件夹")
            st.rerun()
    
    # 创建databases文件夹（如果不存在）
    if st.button("📂 创建默认文件夹", use_container_width=True):
        os.makedirs("databases", exist_ok=True)
        os.makedirs("databases/backups", exist_ok=True)
        st.success("✅ 文件夹已创建")


def render_database_operations():
    """渲染数据库操作部分"""
    
    # 保存数据库
    if st.button("💾 保存当前数据库", use_container_width=True, type="primary"):
        if is_db_available():
            with st.spinner("正在保存..."):
                if trigger_auto_save():
                    st.success("✅ 数据库已保存")
                    # 清除未保存状态
                    st.session_state.db_has_unsaved_changes = False
                    st.rerun()
                else:
                    st.error("❌ 保存失败")
        else:
            st.warning("⚠️ 没有加载的数据库")
    
    # 刷新数据库列表
    if st.button("🔄 刷新数据库列表", use_container_width=True):
        st.rerun()
    
    # 加载数据库
    st.markdown("#### 📥 加载其他数据库")
    
    client = get_db_port_client()
    if client:
        custom_folder = st.session_state.get('custom_db_folder')
        try:
            db_files = client.list_databases(custom_folder)
            # 验证数据库
            valid_db_files = []
            for db_file in db_files:
                try:
                    validation_result = client.validate_database_schema(db_file)
                    if validation_result.get("valid", False):
                        valid_db_files.append(db_file)
                except:
                    pass
            
            if valid_db_files:
                selected_db = st.selectbox(
                    "选择数据库:",
                    options=valid_db_files,
                    format_func=lambda x: Path(x).name,
                    key="management_db_selector"
                )
                
                if st.button("📥 加载选中的数据库", use_container_width=True):
                    with st.spinner("正在加载..."):
                        if load_database(selected_db):
                            st.success(f"✅ 已加载: {Path(selected_db).name}")
                            # 清除未保存状态
                            st.session_state.db_has_unsaved_changes = False
                            st.rerun()
                        else:
                            st.error("❌ 加载失败")
            else:
                st.info("📭 未找到有效的数据库文件")
                
        except Exception as e:
            st.error(f"❌ 获取数据库列表失败: {e}")


def render_database_info():
    """渲染数据库信息部分"""
    
    if not is_db_available():
        st.info("📊 无数据库信息")
        return
    
    client = get_db_port_client()
    if not client:
        return
    
    try:
        # 获取数据库健康状态
        health = client.health()
        if health.get("ok"):
            st.success("✅ 服务状态: 正常")
        else:
            st.error("❌ 服务状态: 异常")
        
        # 获取更多信息（如果服务器支持）
        db_name = get_database_name()
        if db_name and db_name != "N/A":
            st.metric("数据库名称", db_name)
            
            # 尝试获取数据库大小等信息
            custom_folder = st.session_state.get('custom_db_folder', 'databases')
            db_path = Path(custom_folder) / db_name
            
            if db_path.exists():
                size_mb = db_path.stat().st_size / (1024 * 1024)
                st.metric("文件大小", f"{size_mb:.2f} MB")
                
                # 修改时间
                import datetime
                mtime = datetime.datetime.fromtimestamp(db_path.stat().st_mtime)
                st.metric("最后修改", mtime.strftime("%Y-%m-%d %H:%M"))
        
    except Exception as e:
        st.error(f"❌ 获取信息失败: {e}")
