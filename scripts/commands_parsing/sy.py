#!/usr/bin/env python3
"""
SY Command Parsing Utilities
"""
from typing import Optional


def extract_reg_from_sy_content(sy_content: str) -> Optional[str]:
    """从SY命令内容中提取飞机注册号"""
    lines = sy_content.split('\n')
    try:
        cwt_line_index = -1
        for i, line in enumerate(lines):
            if line.strip().startswith('CWT'):
                cwt_line_index = i
                break
        
        if cwt_line_index != -1 and cwt_line_index + 1 < len(lines):
            target_line = lines[cwt_line_index + 1].strip()
            if not target_line:
                return None
            first_section = target_line.split()[0]
            parts = first_section.split('/')
            if len(parts) >= 3:
                return parts[2]
    except (IndexError, ValueError):
        return None
    return None
