#!/usr/bin/env python3
"""
SY Command Parsing Utilities
"""
import json
from pathlib import Path
from typing import Optional


def _load_departure_airport_code() -> Optional[str]:
    """从database_schema.json配置中加载出发机场代码
    Returns None if not found.
    """
    try:
        schema_path = Path(__file__).parent.parent / 'database_schema.json'
        with schema_path.open('r', encoding='utf-8') as f:
            schema = json.load(f)
            return schema.get('config', {}).get('departure_airport_code')
    except Exception:
        return None


def get_sy_flight_type(command_full: str) -> str:
    """从command_full判断SY是出发还是到达航班
    自动从配置加载出发机场代码
    
    Args:
        command_full: 命令完整字符串 (例如: 'SY:CA984/11AUG25 LAX/0')
        
    Returns:
        'departure' 如果匹配配置的出发机场, 否则返回 'arrival'
    """
    if not command_full:
        return 'arrival'
    
    departure_airport_code = _load_departure_airport_code()
    if not departure_airport_code:
        return 'arrival'  # 无配置时无法确定
    
    # 格式: 'SY:CA984/11AUG25 LAX/0' -> 'LAX/0' -> 'LAX'
    parts = command_full.strip().split()
    if parts:
        last_part = parts[-1].upper()
        if last_part.startswith(departure_airport_code.upper()):
            return 'departure'
    return 'arrival'


def is_departure_sy(command_full: str) -> bool:
    """检查SY命令是否为出发航班
    
    Args:
        command_full: SY命令完整字符串
        
    Returns:
        True 如果是出发SY, False 否则
    """
    return get_sy_flight_type(command_full) == 'departure'


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
