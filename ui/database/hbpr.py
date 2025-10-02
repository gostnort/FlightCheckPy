#!/usr/bin/env python3
"""
简化的HBPR数据库操作界面
使用现有的函数和类，避免重复造轮子
"""

import streamlit as st
from pathlib import Path
from ui.common import (
    get_hbpr_database_client,
    get_database_name,
    trigger_auto_save,
    load_database
)
from scripts.hbpr_info_processor import CHbpr


def show_hbpr_operations():
    """显示HBPR操作界面"""
    st.subheader("📥 HBPR Operations")
    # 显示当前数据库
    current_db = get_database_name()
    if current_db and current_db != "N/A" and current_db != "Error":
        st.info(f"📂 当前数据库: **{current_db}**")
    else:
        st.warning("⚠️ 未加载数据库 - 可以从下方选择或浏览文件夹")
    # 操作按钮
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("📤 创建新数据库", use_container_width=True, help="从HBPR列表文件创建新数据库"):
            st.session_state.show_create_db = True
    with col2:
        if st.button("🔄 处理所有记录", use_container_width=True, help="运行CHbpr处理所有记录"):
            process_all_records() 
    with col3:
        if st.button("🧹 清除处理结果", use_container_width=True, help="清除所有处理结果"):
            erase_processing_results()   
    # 处理创建新数据库
    if st.session_state.get('show_create_db', False):
        create_database_from_file()


def process_all_records():
    """处理所有HBPR记录"""
    db = get_hbpr_database_client()
    if not db:
        st.error("❌ 数据库连接不可用")
        return
    
    try:
        # 获取所有记录
        conn = db.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT hbnb_number FROM hbpr_full_records ORDER BY hbnb_number")
        records = [row[0] for row in cursor.fetchall()]
        
        if not records:
            st.info("ℹ️ 没有找到记录")
            return
        
        # 创建进度条
        progress_bar = st.progress(0)
        status_text = st.empty()
        results_container = st.container()
        
        processed_count = 0
        valid_count = 0
        error_count = 0
        
        # 处理记录
        with st.spinner(f"🔄 正在处理 {len(records)} 条记录..."):
            for i, hbnb_number in enumerate(records):
                try:
                    # 获取记录内容
                    content = db.get_hbpr_record(hbnb_number)
                    
                    # 使用CHbpr处理
                    chbpr = CHbpr()
                    chbpr.run(content)
                    
                    # 更新数据库
                    success = db.update_with_chbpr_results(chbpr)
                    
                    if success:
                        processed_count += 1
                        # 只统计有BN号的记录
                        if chbpr.BoardingNumber > 0:
                            if chbpr.is_valid():
                                valid_count += 1
                            else:
                                error_count += 1
                        # 标记有未保存的更改
                        st.session_state.db_has_unsaved_changes = True
                    
                    # 更新进度
                    progress = (i + 1) / len(records)
                    progress_bar.progress(progress)
                    status_text.text(f"处理进度: {i + 1}/{len(records)} ({progress*100:.1f}%)")
                    
                except Exception as e:
                    st.warning(f"⚠️ 处理 HBNB {hbnb_number} 时出错: {str(e)}")
        
        # 显示结果
        with results_container:
            st.success(f"🎉 处理完成！共处理 {processed_count} 条记录")
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("处理总数", processed_count)
            with col2:
                st.metric("有效记录 (有BN)", valid_count)
            with col3:
                st.metric("错误记录 (有BN)", error_count)
        
        # 自动保存
        if trigger_auto_save():
            st.toast("✅ 数据库已自动保存")
        
    except Exception as e:
        st.error(f"❌ 处理错误: {str(e)}")


def erase_processing_results():
    """清除所有处理结果"""
    db = get_hbpr_database_client()
    if not db:
        st.error("❌ 数据库连接不可用")
        return
    
    # 确认对话框
    if not st.session_state.get('confirm_erase', False):
        st.warning("⚠️ 此操作将清除所有处理结果，再次点击确认")
        st.session_state.confirm_erase = True
        return
    
    try:
        with st.spinner("🧹 正在清除处理结果..."):
            success = db.erase_splited_records()
            
            if success:
                st.success("✅ 处理结果已清除")
                st.info("ℹ️ 所有处理字段已重置，仅保留HBNB号码和原始内容")
                
                # 标记有未保存的更改
                st.session_state.db_has_unsaved_changes = True
                
                # 保存更改
                if trigger_auto_save():
                    st.toast("✅ 更改已保存")
                
                # 重置确认状态
                st.session_state.confirm_erase = False
                st.rerun()
            else:
                st.error("❌ 清除失败")
    
    except Exception as e:
        st.error(f"❌ 错误: {str(e)}")


def create_database_from_file():
    """从HBPR列表文件创建数据库"""
    with st.expander("📤 从HBPR文件创建新数据库", expanded=True):
        uploaded_file = st.file_uploader(
            "选择HBPR列表文件",
            type=["txt"],
            help="上传HBPR列表文件（如sample_hbpr.txt）",
            key="hbpr_uploader"
        )
        col1, col2 = st.columns(2)
        with col2:
            if st.button("❌ 取消", use_container_width=True):
                st.session_state.show_create_db = False
                st.rerun()
        if uploaded_file is not None:
            file_content = uploaded_file.getvalue().decode("utf-8")
            
            with col1:
                if st.button("✅ 创建数据库", use_container_width=True, type="primary"):
                    create_db_from_content(file_content)


def create_db_from_content(file_content: str):
    """从文件内容创建数据库"""
    try:
        # 解析航班号
        from scripts.hbpr_list_processor import parse_flight_id_from_content, HBPRProcessor
        
        flight_id = parse_flight_id_from_content(file_content)
        if not flight_id:
            st.error("❌ 无法从文件中解析航班号")
            return
        # 确定数据库路径
        db_folder = st.session_state.get('custom_db_folder', 'databases')
        db_path = Path(db_folder) / f"{flight_id}.db"
        if db_path.exists():
            st.error(f"❌ 数据库 {flight_id}.db 已存在")
            return
        with st.spinner(f"正在创建数据库 {flight_id}.db..."):
            # 创建数据库
            import sqlite3
            conn = sqlite3.connect(str(db_path))
            # 使用HBPRProcessor处理
            processor = HBPRProcessor(conn)
            processor.process(file_content)
            # 获取统计信息
            flight_data = processor.flight_data[flight_id]
            record_count = len(flight_data['hbnb_numbers']) 
            conn.close()
            st.success(f"✅ 创建数据库成功！包含 {record_count} 条记录")
            # 加载到内存服务器
            if load_database(str(db_path)):
                # 清理状态
                st.session_state.show_create_db = False
                
                # 自动处理所有记录
                st.info("🔄 开始自动处理所有记录...")
                process_all_records()
            else:
                st.error("❌ 无法加载数据库到服务器")               
    except Exception as e:
        st.error(f"❌ 创建数据库失败: {str(e)}")
