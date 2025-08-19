#!/usr/bin/env python3
"""
Data Cleaning Utility for HBPR Processing
在数据输入和存储阶段清理问题字符，防止导出错误
"""

import re
import logging
from typing import List, Tuple, Optional


# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def clean_text_for_input(text: str, aggressive: bool = False) -> str:
    """
    清理输入文本，移除或替换问题字符
    Args:
        text (str): 原始文本
        aggressive (bool): 是否使用激进的清理模式（移除更多字符）
    Returns:
        str: 清理后的文本
    """
    if not text or not isinstance(text, str):
        return ""
    
    original_text = text
    cleaned = text
    # 这些字符在大多数情况下都是有害的
    # 处理ASCII控制字符，但保留CR(\r)和LF(\n)和TAB(\t)
    cleaned = re.sub(r'[\x00-\x09]', ' ', cleaned)  # 0-9 (保留LF \x0a)
    cleaned = re.sub(r'[\x0b\x0c]', ' ', cleaned)  # 11-12 (保留TAB \x09)
    cleaned = re.sub(r'[\x0e-\x1f]', ' ', cleaned)  # 14-31 (保留CR \x0d)
    cleaned = re.sub(r'[\x7f]', ' ', cleaned)  # DEL字符
 
    
    # 记录清理情况
    if cleaned != original_text:
        logger.info(f"Text cleaned: {len(original_text)} -> {len(cleaned)} characters")
        # 记录被移除的字符类型
        removed_chars = set(original_text) - set(cleaned)
        if removed_chars:
            logger.info(f"Removed character types: {[repr(c) for c in sorted(removed_chars)]}")
    
    return cleaned


def clean_hbpr_record_content(content: str) -> str:
    """
    专门清理HBPR记录内容
    Args:
        content (str): HBPR记录内容
    Returns:
        str: 清理后的内容
    """
    if not content:
        return content
    
    # 检查是否包含控制字符
    has_control_chars = re.search(r'[\x00-\x1f\x7f]', content)
    has_binary_chars = re.search(r'[^\x20-\x7e\n\r\t]', content)
    
    if has_control_chars or has_binary_chars:
        logger.warning("HBPR content contains control or binary characters, cleaning...")
        return clean_text_for_input(content, aggressive=True)
    
    return content


def validate_and_clean_file_content(file_path: str, encoding: str = 'utf-8') -> Tuple[List[str], bool]:
    """
    验证并清理文件内容
    Args:
        file_path (str): 文件路径
        encoding (str): 文件编码
    Returns:
        Tuple[List[str], bool]: (清理后的行列表, 是否进行了清理)
    """
    try:
        # 尝试正常读取
        with open(file_path, 'r', encoding=encoding) as file:
            lines = file.readlines()
        
        # 检查是否需要清理
        needs_cleaning = False
        cleaned_lines = []
        
        for i, line in enumerate(lines):
            original_line = line
            cleaned_line = clean_text_for_input(line)
            
            if cleaned_line != original_line:
                needs_cleaning = True
                logger.info(f"Line {i+1} cleaned: {len(original_line)} -> {len(cleaned_line)} characters")
            
            cleaned_lines.append(cleaned_line)
        
        if needs_cleaning:
            logger.warning(f"File {file_path} contained problematic characters and has been cleaned")
        
        return cleaned_lines, needs_cleaning
        
    except UnicodeDecodeError as e:
        logger.error(f"Unicode decode error in {file_path}: {e}")
        # 尝试使用errors='replace'模式
        try:
            with open(file_path, 'r', encoding=encoding, errors='replace') as file:
                lines = file.readlines()
            
            # 强制清理所有行
            cleaned_lines = [clean_text_for_input(line, aggressive=True) for line in lines]
            logger.warning(f"File {file_path} decoded with replacement and cleaned")
            return cleaned_lines, True
            
        except Exception as e2:
            logger.error(f"Failed to read file {file_path} even with replacement: {e2}")
            raise
    
    except Exception as e:
        logger.error(f"Error reading file {file_path}: {e}")
        raise


def clean_database_content_before_save(content: str, field_name: str = "unknown") -> str:
    """
    在保存到数据库前清理内容
    Args:
        content (str): 要保存的内容
        field_name (str): 字段名称（用于日志）
    Returns:
        str: 清理后的内容
    """
    if not content:
        return content
    
    original_content = content
    cleaned_content = clean_text_for_input(content)
    
    if cleaned_content != original_content:
        logger.info(f"Field '{field_name}' cleaned before database save: {len(original_content)} -> {len(cleaned_content)} characters")
    
    return cleaned_content


def batch_clean_text_data(text_list: List[str], field_name: str = "unknown") -> List[str]:
    """
    批量清理文本数据
    Args:
        text_list (List[str]): 文本列表
        field_name (str): 字段名称（用于日志）
    Returns:
        List[str]: 清理后的文本列表
    """
    if not text_list:
        return text_list
    
    cleaned_list = []
    cleaned_count = 0
    
    for i, text in enumerate(text_list):
        if text:
            original_text = text
            cleaned_text = clean_text_for_input(text)
            if cleaned_text != original_text:
                cleaned_count += 1
            cleaned_list.append(cleaned_text)
        else:
            cleaned_list.append(text)
    
    if cleaned_count > 0:
        logger.info(f"Batch cleaned {cleaned_count} out of {len(text_list)} items in field '{field_name}'")
    
    return cleaned_list


def get_cleaning_statistics(text: str) -> dict:
    """
    获取文本清理统计信息
    Args:
        text (str): 原始文本
    Returns:
        dict: 清理统计信息
    """
    if not text:
        return {"total_chars": 0, "control_chars": 0, "binary_chars": 0, "needs_cleaning": False}
    
    stats = {
        "total_chars": len(text),
        "control_chars": len(re.findall(r'[\x00-\x1f\x7f]', text)),
        "binary_chars": len(re.findall(r'[^\x20-\x7e\n\r\t]', text)),
        "needs_cleaning": False
    }
    
    stats["needs_cleaning"] = stats["control_chars"] > 0 or stats["binary_chars"] > 0
    
    return stats


def preview_cleaning_effect(text: str, max_length: int = 100) -> dict:
    """
    预览清理效果
    Args:
        text (str): 原始文本
        max_length (int): 最大显示长度
    Returns:
        dict: 清理预览信息
    """
    if not text:
        return {"original": "", "cleaned": "", "changed": False}
    
    cleaned = clean_text_for_input(text)
    changed = cleaned != text
    
    # 截断显示
    original_preview = text[:max_length] + ("..." if len(text) > max_length else "")
    cleaned_preview = cleaned[:max_length] + ("..." if len(cleaned) > max_length else "")
    
    return {
        "original": original_preview,
        "cleaned": cleaned_preview,
        "changed": changed,
        "original_length": len(text),
        "cleaned_length": len(cleaned),
        "statistics": get_cleaning_statistics(text)
    }


if __name__ == "__main__":
    # 测试功能
    test_cases = [
        "Normal text",
        "Text with \x00\x01\x02 control chars",
        "Text with \x7f DEL char",
        ">HBPR: CA984/15AUG25*LAX,67 PNR RL MZBX",
        "Mixed: >HBPR: CA984/15AUG25*LAX,67 PNR RL MZBX with \x1f\x1e\x1d control chars"
    ]
    
    print("🧪 Testing Data Cleaning Utility")
    print("=" * 50)
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\nTest {i}:")
        preview = preview_cleaning_effect(test_case)
        print(f"  Original: {preview['original']}")
        print(f"  Cleaned:  {preview['cleaned']}")
        print(f"  Changed:   {preview['changed']}")
        print(f"  Length:    {preview['original_length']} -> {preview['cleaned_length']}")
        print(f"  Stats:     {preview['statistics']}")
    
    print("\n🎉 Testing completed!")
