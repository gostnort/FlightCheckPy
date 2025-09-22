#!/usr/bin/env python3
"""
Database Data Cleaning Utility
清理数据库中包含二进制/hex字符的数据，使其可以安全导出
"""

import sqlite3
import re


def clean_text_for_database(text: str) -> str:
    """
    清理文本数据，移除或替换无法在数据库中正常使用的字符
    Args:
        text (str): 原始文本
    Returns:
        str: 清理后的文本
    """
    if not text or not isinstance(text, str):
        return ""
    # 移除或替换控制字符（ASCII 0-31, 127）
    cleaned = re.sub(r'[\x00-\x1f\x7f]', ' ', text)
    # 移除或替换其他问题字符
    # 替换常见的二进制/hex字符
    cleaned = re.sub(r'[^\x20-\x7e\n\r\t]', ' ', cleaned)
    # 移除多余的空白字符
    cleaned = re.sub(r' +', ' ', cleaned)
    cleaned = re.sub(r'\n\s*\n', '\n', cleaned)
    # 确保文本以可打印字符结尾
    cleaned = cleaned.strip()
    return cleaned


