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
