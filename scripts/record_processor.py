#!/usr/bin/env python3
"""
Record Processor
处理HBPR记录验证和数据库操作（只处理HBPR，不处理PR）
"""

import re
import streamlit as st
from scripts.hbpr_info_processor import CHbpr
from scripts.hbpr_file_processor import HbprProcessor
from scripts.data_cleaner import clean_hbpr_record_content


def validate_full_hbpr_record(hbpr_content):
    """
    验证HBPR完整记录格式
    Args:
        hbpr_content: HBPR内容字符串
    Returns:
        dict: {
            'is_valid': bool,
            'hbnb_number': int or None,
            'errors': list of error messages,
            'chbpr_errors': dict of CHbpr error messages,
            'corrected_content': str - 清理后的内容
        }
    """
    result = {
        'is_valid': False,
        'hbnb_number': None,
        'errors': [],
        'chbpr_errors': {},
        'corrected_content': hbpr_content
    }
    # 检查内容是否为空
    if not hbpr_content or not hbpr_content.strip():
        result['errors'].append("Input content is empty")
        return result
    # 清理输入内容
    cleaned_content = clean_hbpr_record_content(hbpr_content)
    result['corrected_content'] = cleaned_content
    # 步骤1: 检查基本HBPR记录格式
    hbpr_pattern = r'>HBPR:\s*[^,]+,(\d+)'
    hbpr_match = re.search(hbpr_pattern, cleaned_content)
    if not hbpr_match:
        result['errors'].append("Input does not contain valid full HBPR record format (>HBPR: flight_info,hbnb_number)")
        return result
    try:
        hbnb_number = int(hbpr_match.group(1))
        result['hbnb_number'] = hbnb_number
    except ValueError:
        result['errors'].append("Invalid HBNB number format")
        return result
    # 步骤2: 使用HbprProcessor验证记录格式
    try:
        lines = cleaned_content.split('\n')
        hbpr_line_index = -1
        for i, line in enumerate(lines):
            if line.strip().startswith('>HBPR:'):
                hbpr_line_index = i
                break
        if hbpr_line_index == -1:
            result['errors'].append("No line starting with '>HBPR:' found in the content")
            return result
        # 创建HbprProcessor实例验证
        processor = HbprProcessor("temp_input")
        parsed_hbnb, parsed_content, next_index = processor.parse_full_record(lines, hbpr_line_index)
        if parsed_hbnb is None:
            result['errors'].append("HbprProcessor failed to parse the full record format")
            return result
        if parsed_hbnb != hbnb_number:
            result['errors'].append(f"HBNB number mismatch: regex found {hbnb_number}, parser found {parsed_hbnb}")
            return result
    except Exception as e:
        result['errors'].append(f"HbprProcessor validation failed: {str(e)}")
        return result
    # 步骤3: 使用CHbpr验证记录内容
    try:
        chbpr = CHbpr()
        chbpr.run(cleaned_content)
        result['chbpr_errors'] = chbpr.error_msg
        # 检查关键错误
        if chbpr.error_msg.get('Other'):
            result['errors'].append(f"CHbpr validation failed with critical errors: {'; '.join(chbpr.error_msg['Other'])}")
            return result
        # 验证HBNB号码
        if chbpr.HbnbNumber != hbnb_number:
            result['errors'].append(f"CHbpr HBNB number mismatch: expected {hbnb_number}, got {chbpr.HbnbNumber}")
            return result
    except Exception as e:
        result['errors'].append(f"CHbpr processing failed: {str(e)}")
        return result
    # 所有验证通过
    result['is_valid'] = True
    return result


def process_hbpr_record(db, hbpr_content, is_duplicate=False):
    """
    处理HBPR记录（替换或创建重复记录）
    Args:
        db: HbprDatabase instance
        hbpr_content: HBPR内容
        is_duplicate: 是否创建重复记录
    Returns:
        dict: {
            'success': bool,
            'message': str,
            'hbnb_number': int or None
        }
    """
    result = {
        'success': False,
        'message': '',
        'hbnb_number': None
    }
    if not hbpr_content.strip():
        result['message'] = "⚠️ Please enter content first."
        return result
    # 验证HBPR记录
    validation_result = validate_full_hbpr_record(hbpr_content)
    if not validation_result['is_valid']:
        result['message'] = f"❌ HBPR Record Validation Failed: {'; '.join(validation_result['errors'])}"
        return result
    try:
        corrected_content = validation_result['corrected_content']
        # 创建CHbpr实例进行处理
        chbpr = CHbpr()
        chbpr.run(corrected_content)
        # 验证无关键错误
        if chbpr.error_msg.get('Other'):
            result['message'] = f"❌ Critical errors occurred during CHbpr processing: {'; '.join(chbpr.error_msg['Other'])}"
            return result
        # 验证航班信息匹配
        if not validate_flight_info(db, corrected_content):
            result['message'] = "❌ Flight info validation failed"
            return result
        # 处理记录
        if is_duplicate:
            # 创建重复记录
            hbnb_exists = db.check_hbnb_exists(chbpr.HbnbNumber)
            if not hbnb_exists['full_record']:
                result['message'] = f"❌ Cannot create duplicate: No full record exists for HBNB {chbpr.HbnbNumber}."
                return result
            db.create_duplicate_record(chbpr.HbnbNumber, chbpr.HbnbNumber, corrected_content)
            db.update_with_chbpr_results(chbpr)
            result['success'] = True
            result['message'] = f"✅ Created duplicate record for HBNB {chbpr.HbnbNumber}"
            result['hbnb_number'] = chbpr.HbnbNumber
        else:
            # 替换记录
            process_result = process_record_common(db, chbpr, corrected_content, is_duplicate=False)
            result['success'] = process_result['success']
            result['message'] = process_result['message']
            result['hbnb_number'] = chbpr.HbnbNumber
        # 触发自动保存
        from ui.common import trigger_auto_save
        trigger_auto_save()
    except Exception as e:
        result['message'] = f"❌ Error processing HBPR record: {str(e)}"
    return result


def process_record_common(db, chbpr, hbpr_content, is_duplicate=False):
    """
    通用HBPR记录处理逻辑
    Args:
        db: HbprDatabase instance
        chbpr: CHbpr instance with processed data
        hbpr_content: HBPR content
        is_duplicate: Whether this is a duplicate record operation
    Returns:
        dict: Processing result
    """
    result = {
        'success': False,
        'message': '',
        'hbnb_number': chbpr.HbnbNumber
    }
    # 获取HBNB的simple_record和full_record信息
    hbnb_exists = db.check_hbnb_exists(chbpr.HbnbNumber)
    # 验证航班信息匹配
    if not validate_flight_info(db, hbpr_content):
        result['message'] = "❌ Flight info validation failed"
        return result
    # 处理记录替换/创建逻辑
    if hbnb_exists['exists']:
        # 如果存在完整记录，自动备份
        if hbnb_exists['full_record']:
            try:
                backup_success = db.auto_backup_before_replace(chbpr.HbnbNumber)
                if not backup_success:
                    st.warning(f"⚠️ Original record NOT found for HBNB {chbpr.HbnbNumber}")
            except Exception as e:
                st.warning(f"⚠️ Backup failed for HBNB {chbpr.HbnbNumber}: {str(e)}")
        if hbnb_exists['simple_record']:
            # 删除简单记录
            db.delete_simple_record(chbpr.HbnbNumber)
        # 创建或更新完整记录
        db.create_full_record(chbpr.HbnbNumber, hbpr_content)
        result['success'] = True
        if hbnb_exists['full_record']:
            result['message'] = f"✅ Replaced full record for HBNB {chbpr.HbnbNumber} (original backed up)"
        else:
            result['message'] = f"✅ Updated record for HBNB {chbpr.HbnbNumber}"
    else:
        # 创建新的完整记录
        db.create_full_record(chbpr.HbnbNumber, hbpr_content)
        result['success'] = True
        result['message'] = f"✅ Created new full record for HBNB {chbpr.HbnbNumber}"
    # 更新验证结果
    db.update_with_chbpr_results(chbpr)
    return result


def validate_flight_info(db, hbpr_content):
    """
    验证航班信息匹配
    Args:
        db: HbprDatabase instance
        hbpr_content: HBPR content to validate
    Returns:
        bool: True if validation passes, False otherwise
    """
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
        return False
    return True


def get_processing_info(db, hbnb_number, hbnb_exists):
    """
    获取处理信息（用于UI显示）
    Args:
        db: HbprDatabase instance
        hbnb_number: HBNB number
        hbnb_exists: HBNB existence info from db.check_hbnb_exists()
    Returns:
        dict: Processing information for UI display
    """
    flight_info = db.get_flight_info()
    return {
        'flight_info': flight_info,
        'hbnb_exists': hbnb_exists,
        'hbnb_number': hbnb_number
    }

