#!/usr/bin/env python3
"""
AIRC Command Parsing Utilities
"""
from typing import Optional


def extract_reg_from_airc_command(airc_command_full: str) -> Optional[str]:
    """从AIRC命令中提取飞机注册号"""
    try:
        part_after_colon = airc_command_full.split(':', 1)[1]
        reg = part_after_colon.split('/', 1)[1]
        return reg.strip()
    except IndexError:
        return None


def extract_inop_seats_from_airc_content(airc_content: str) -> str:
    """从AIRC内容提取不可用座位列表
    
    解析带有'- C'标记的座位行，提取座位号
    返回格式: 'INOP SEAT: 31JKL, 47L, 55H'
    
    Args:
        airc_content: AIRC命令完整内容
        
    Returns:
        格式化的不可用座位字符串，如果没有座位返回空字符串
    """
    import re
    
    try:
        lines = airc_content.split('\n')
        inop_seats = []
        
        for line in lines:
            # 查找包含'- C'的行，表示座位不可用
            # 例如: ' 31K - C(LN20250921)                                          21SEP25 22:40:46'
            if '- C' in line or '- c' in line:
                # 提取行首的座位号（去除空格）
                seat_match = re.match(r'\s*(\w+)\s*-\s*[Cc]', line)
                if seat_match:
                    seat = seat_match.group(1).strip()
                    if seat:
                        inop_seats.append(seat)
        
        if inop_seats:
            return f"INOP SEAT: {', '.join(inop_seats)}"
        return ""
    except Exception:
        return ""