#!/usr/bin/env python3
"""
Data Cleaning Utility for HBPR Processing
在数据输入和存储阶段清理问题字符，防止导出错误
"""

import re
import logging
from typing import List, Tuple


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
    # 特殊处理 U+0010 (\x10) —— 将其替换为 '>' 而不是简单删除
    cleaned = cleaned.replace('\x10', '>')
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


def clean_hbpr_record_content(content: str, hbnb_number: int = None) -> str:
    """
    专门清理HBPR记录内容
    Args:
        content (str): HBPR记录内容
        hbnb_number (int): HBNB编号（可选，用于日志）
    Returns:
        str: 清理后的内容
    """
    if not content:
        return content
    original_content = content
    cleaned_content = clean_text_for_input(content, aggressive=True)
    # 只有在实际清理了内容时才记录
    if cleaned_content != original_content:
        # 找到第一个被清理的字符位置
        for i, (orig_char, clean_char) in enumerate(zip(original_content, cleaned_content)):
            if orig_char != clean_char:
                # 获取前后10个字符的上下文
                start = max(0, i - 10)
                end = min(len(original_content), i + 10)
                context_orig = original_content[start:end]
                context_clean = cleaned_content[start:end]
                hbnb_info = f"HBNB {hbnb_number}: " if hbnb_number else ""
                logger.warning(
                    f"{hbnb_info}HBPR内容包含问题字符，已清理\n"
                    f"  位置: 第{i+1}个字符\n"
                    f"  原文: {repr(context_orig)}\n"
                    f"  清理后: {repr(context_clean)}"
                )
                break
    
    return cleaned_content


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


if __name__ == "__main__":
    # 测试功能


    # 读取并处理 sample_hbpr.txt（如果存在）
    try:
        sample_path = "sample_hbpr.txt"
        cleaned_lines, changed = validate_and_clean_file_content(sample_path)
        joined = "".join(cleaned_lines)
        print("\n📄 Processed sample_hbpr.txt content:\n")
        print(joined)
        print(f"\n🔁 Changes applied: {changed}")
    except Exception as e:
        logger.error(f"Failed to process sample_hbpr.txt: {e}")