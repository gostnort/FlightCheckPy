#!/usr/bin/env python3
"""
Add HBPRs tab for Process Records page - Add HBPR records with duplicate handling
"""

import streamlit as st
from ui.common import get_hbpr_database_client, trigger_auto_save
from scripts.hbpr_list_processor import HBPRProcessor, parse_flight_id_from_content
from scripts.hbpr_info_processor import CHbpr


def show_add_hbprs_tab():
    """显示添加HBPR记录标签页 - 从HBPR列表更新现有数据库"""
    st.subheader("➕ 从HBPR列表更新当前数据库")

    uploaded_file = st.file_uploader(
        "上传HBPR列表文件以更新记录",
        type=["txt"],
        help="上传HBPR列表文件。如果HBNB已存在，创建副本记录并更新；如果不存在，创建新记录。",
        key="add_hbprs_upload"
    )

    if uploaded_file is not None:
        if st.button("🚀 处理并更新HBPR记录", use_container_width=True, type="primary"):
            process_and_add_hbprs(uploaded_file)


def process_and_add_hbprs(uploaded_file):
    """处理HBPR文件并添加/更新记录，处理重复记录"""
    try:
        db = get_hbpr_database_client()
        if not db:
            st.error("❌ 数据库连接不可用")
            return

        file_content = uploaded_file.getvalue().decode("utf-8")

        with st.spinner("正在处理HBPR文件..."):
            # 步骤1: 解析文件获取航班信息
            flight_id_from_file = parse_flight_id_from_content(file_content)
            if not flight_id_from_file:
                st.error("❌ 无法从文件中解析航班信息")
                return

            # 步骤2: 验证航班信息是否匹配当前数据库
            current_flight_info = db.get_flight_info()
            if not current_flight_info:
                st.error("❌ 当前数据库没有航班信息")
                return

            if current_flight_info['flight_id'] != flight_id_from_file:
                st.error("❌ 航班信息不匹配！")
                st.error(f"文件航班: **{flight_id_from_file}**")
                st.error(f"数据库航班: **{current_flight_info['flight_id']}**")
                return

            st.info(f"✅ 航班信息匹配: **{flight_id_from_file}**")

            # 步骤3: 使用HBPRProcessor解析所有记录
            conn = db.get_connection()
            processor = HBPRProcessor(conn)
            processor.parse_file_content(file_content)

            if not processor.flight_data or flight_id_from_file not in processor.flight_data:
                st.error("❌ 文件解析失败，未找到有效记录")
                return

            flight_data = processor.flight_data[flight_id_from_file]
            full_records = flight_data['full_records']
            simple_records = flight_data['simple_records']

            # 统计数据
            stats = {
                'new_records': 0,
                'updated_records': 0,
                'duplicates_created': 0,
                'skipped_unchanged': 0,  # 内容未变化的记录
                'errors': 0,
                'to_process': []  # 需要用CHbpr处理的HBNB列表
            }

            # 步骤4: 处理完整记录
            progress_bar = st.progress(0)
            status_text = st.empty()
            total_records = len(full_records) + len(simple_records)
            current = 0

            for hbnb_num, record_content in full_records.items():
                current += 1
                progress = current / total_records
                progress_bar.progress(progress)
                status_text.text(f"处理完整记录: {current}/{total_records} - HBNB {hbnb_num}")

                try:
                    # 检查记录是否已存在
                    exists_info = db.check_hbnb_exists(hbnb_num)
                    
                    if exists_info['full_record']:
                        # 记录已存在 - 比较内容
                        original_info = db.get_original_record_info(hbnb_num)
                        if original_info:
                            # 比较内容是否相同（去除首尾空白后比较）
                            if original_info['record_content'].strip() == record_content.strip():
                                # 内容完全相同，跳过
                                stats['skipped_unchanged'] += 1
                            else:
                                # 内容有变化 - 创建副本并更新
                                # 创建副本记录（用于时间线）
                                db.create_duplicate_record_with_time(
                                    hbnb_num, 
                                    hbnb_num, 
                                    original_info['record_content'],
                                    original_info['created_at']
                                )
                                stats['duplicates_created'] += 1
                                
                                # 更新记录内容（使用INSERT OR REPLACE）
                                db.create_full_record(hbnb_num, record_content)
                                stats['updated_records'] += 1
                                stats['to_process'].append(hbnb_num)
                        else:
                            # 无法获取原始记录，直接更新
                            db.create_full_record(hbnb_num, record_content)
                            stats['updated_records'] += 1
                            stats['to_process'].append(hbnb_num)
                        
                    else:
                        # 新记录 - 直接创建
                        if exists_info['simple_record']:
                            # 删除简单记录
                            db.delete_simple_record(hbnb_num)
                        db.create_full_record(hbnb_num, record_content)
                        stats['new_records'] += 1
                        stats['to_process'].append(hbnb_num)

                except Exception as e:
                    st.warning(f"⚠️ 处理HBNB {hbnb_num}失败: {str(e)[:100]}...")
                    stats['errors'] += 1

            # 步骤5: 处理简单记录
            for hbnb_num, record_line in simple_records.items():
                current += 1
                progress = current / total_records
                progress_bar.progress(progress)
                status_text.text(f"处理简单记录: {current}/{total_records} - HBNB {hbnb_num}")

                try:
                    # 只添加简单记录，如果没有完整记录
                    exists_info = db.check_hbnb_exists(hbnb_num)
                    if not exists_info['full_record'] and not exists_info['simple_record']:
                        db.create_simple_record(hbnb_num, record_line)
                        stats['new_records'] += 1
                except Exception as e:
                    st.warning(f"⚠️ 处理简单记录HBNB {hbnb_num}失败: {str(e)[:100]}...")
                    stats['errors'] += 1

            progress_bar.empty()
            status_text.empty()

            # 显示统计信息
            st.success("📊 记录导入完成！")
            col1, col2, col3, col4, col5 = st.columns(5)
            with col1:
                st.metric("新建记录", stats['new_records'])
            with col2:
                st.metric("更新记录", stats['updated_records'])
            with col3:
                st.metric("创建副本", stats['duplicates_created'])
            with col4:
                st.metric("未变化", stats['skipped_unchanged'])
            with col5:
                st.metric("错误", stats['errors'])

            # 标记有未保存的更改
            if stats['new_records'] > 0 or stats['updated_records'] > 0:
                st.session_state.db_has_unsaved_changes = True

            # 步骤6: 使用CHbpr处理所有新建/更新的记录
            if stats['to_process']:
                st.info(f"🔄 开始处理 {len(stats['to_process'])} 条新建/更新的记录...")
                process_updated_records(db, stats['to_process'])

            # 自动保存
            if trigger_auto_save():
                st.toast("✅ 数据库已自动保存")

    except Exception as e:
        st.error(f"❌ 处理HBPR文件时出错: {str(e)}")
        import traceback
        st.error(traceback.format_exc())


def process_updated_records(db, hbnb_list):
    """使用CHbpr处理更新的记录"""
    try:
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        processed_count = 0
        valid_count = 0
        error_count = 0
        
        for i, hbnb_number in enumerate(hbnb_list):
            try:
                # 更新进度
                progress = (i + 1) / len(hbnb_list)
                progress_bar.progress(progress)
                status_text.text(f"处理进度: {i + 1}/{len(hbnb_list)} - HBNB {hbnb_number}")
                
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
                    
            except Exception as e:
                st.warning(f"⚠️ 处理 HBNB {hbnb_number} 时出错: {str(e)}")
        
        progress_bar.empty()
        status_text.empty()
        
        # 显示处理结果
        st.success(f"🎉 处理完成！共处理 {processed_count} 条记录")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("处理总数", processed_count)
        with col2:
            st.metric("有效记录 (有BN)", valid_count)
        with col3:
            st.metric("错误记录 (有BN)", error_count)
        
    except Exception as e:
        st.error(f"❌ 处理记录时出错: {str(e)}")
