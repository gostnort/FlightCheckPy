#!/usr/bin/env python3
"""
SY Command Parsing Utilities
"""

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional


PassengerCountsDict = Dict[str, List[int]]


def _load_departure_airport_code() -> Optional[str]:
    """从database_schema.json配置中加载出发机场代码
    Returns None if not found.
    """
    try:
        schema_path = Path(__file__).parent.parent / "database_schema.json"
        with schema_path.open("r", encoding="utf-8") as f:
            schema = json.load(f)
            return schema.get("config", {}).get("departure_airport_code")
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
        return "arrival"

    departure_airport_code = _load_departure_airport_code()
    if not departure_airport_code:
        return "arrival"  # 无配置时无法确定

    # 格式: 'SY:CA984/11AUG25 LAX/0' -> 'LAX/0' -> 'LAX'
    parts = command_full.strip().split()
    if parts:
        last_part = parts[-1].upper()
        if last_part.startswith(departure_airport_code.upper()):
            return "departure"
    return "arrival"


def is_departure_sy(command_full: str) -> bool:
    """检查SY命令是否为出发航班

    Args:
        command_full: SY命令完整字符串

    Returns:
        True 如果是出发SY, False 否则
    """
    return get_sy_flight_type(command_full) == "departure"


def extract_reg_from_sy_content(sy_content: str) -> Optional[str]:
    """从SY命令内容中提取飞机注册号"""
    lines = sy_content.split("\n")
    try:
        cwt_line_index = -1
        for i, line in enumerate(lines):
            if line.strip().startswith("CWT"):
                cwt_line_index = i
                break

        if cwt_line_index != -1 and cwt_line_index + 1 < len(lines):
            target_line = lines[cwt_line_index + 1].strip()
            if not target_line:
                return None
            first_section = target_line.split()[0]
            parts = first_section.split("/")
            if len(parts) >= 3:
                return parts[2]
    except (IndexError, ValueError):
        return None
    return None


def extract_flight_number_from_command_full(command_full: str) -> Optional[str]:
    """从command_full提取航班号

    例如: 'SY:CA984/11AUG25 LAX/0' -> 'CA984'

    Args:
        command_full: 完整命令字符串

    Returns:
        航班号，如果解析失败返回None
    """
    try:
        # 格式: 'SY:CA984/11AUG25 LAX/0'
        # 提取冒号后、第一个斜杠前的部分
        after_colon = command_full.split(":", 1)[1].strip()
        flight_number = after_colon.split("/")[0].strip()
        return flight_number if flight_number else None
    except (IndexError, ValueError):
        return None


def extract_date_from_command_full(command_full: str) -> Optional[str]:
    """从command_full提取并格式化日期

    例如: 'SY:CA984/11AUG25 LAX/0' -> '8/11/2025'
    将日期从DDMMMYY格式转换为MM/DD/YYYY格式

    Args:
        command_full: 完整命令字符串

    Returns:
        格式化的日期字符串(MM/DD/YYYY)，如果解析失败返回None
    """
    try:
        # 格式: 'SY:CA984/11AUG25 LAX/0'
        # 提取日期部分: '11AUG25'
        date_part = command_full.split("/")[1].split()[0].strip()

        # 使用datetime解析日期: 11AUG25
        # 格式: %d%b%y (日-月缩写-年)
        dt = datetime.strptime(date_part, "%d%b%y")

        # 返回格式: MM/DD/YYYY（去除前导零）
        return f"{dt.month}/{dt.day}/{dt.year}"
    except (IndexError, ValueError):
        return None


def extract_route_from_sy_content(sy_content: str) -> Optional[str]:
    """从SY内容提取航线
    查找以'*'开头的行，提取航线代码
    例如: '*LAXPEK R035/326...' -> 'LAXPEK'
    Args:
        sy_content: SY命令内容
    Returns:
        航线代码，如果未找到返回None
    """
    try:
        lines = sy_content.split("\n")
        for line in lines:
            stripped = line.strip()
            if stripped.startswith("*"):
                # 提取'*'后面的第一个单词（航线代码）
                route = stripped[1:].split()[0] if len(stripped) > 1 else None
                return route if route else None
    except (IndexError, ValueError):
        return None
    return None


def extract_destination_from_sy_content(sy_content: str) -> Optional[str]:
    """从SY内容提取目的地代码（航线后3个字母）

    例如: '*LAXPEK R035/326...' -> 'PEK'
    从航线代码中提取后3个字母作为目的地
    Args:
        sy_content: SY命令内容
    Returns:
        目的地代码（3字母），如果未找到返回None
    """
    try:
        route = extract_route_from_sy_content(sy_content)
        if route and len(route) >= 6:
            # 航线通常是6个字母，前3个是出发地，后3个是目的地
            destination = route[-3:].upper()
            return destination if destination else None
    except (IndexError, ValueError):
        return None
    return None


def extract_cnf_from_text(text: str) -> Optional[tuple]:
    """从文本中提取CNF舱位配置，返回元组格式

    支持的格式:
    - CNF/J36Y356 → (0, 36, 356)
    - CNF/F8J42Y261 → (8, 42, 261)

    Args:
        text: 包含CNF信息的文本（可以是命令全文或内容）

    Returns:
        (f_count, j_count, y_count) 元组，如果未找到返回None
        注意：如果只有2个舱位（J/Y），F设为0
    """
    if not text:
        return None
    # 匹配 CNF/ 后跟 2 或 3 个 字母+数字 组合
    # 捕获3个数字组，第3个可选
    match = re.search(
        r"CNF\s*/?\s*[A-Z]\s*(\d+)\s*[A-Z]\s*(\d+)\s*(?:[A-Z]\s*(\d+))?", text
    )
    if match:
        groups = match.groups()
        if groups[2] is None:
            # 只有2个舱位 (J, Y)，F设为0
            return (0, int(groups[0]), int(groups[1]))
        else:
            # 有3个舱位 (F, J, Y)
            return (int(groups[0]), int(groups[1]), int(groups[2]))
    return None


def extract_cnf_original_from_sy_content(sy_content: str) -> Optional[str]:
    """提取CNF原始字符串并转换为展示格式（向后兼容）

    例如: 'CNF/J36Y356' -> 'J/36 Y/356'
         'CNF/F8J42Y261' -> 'F/8 J/42 Y/261'
    从CNF字符串中提取各舱位和座位数，格式化输出

    Args:
        sy_content: SY命令内容

    Returns:
        格式化后的舱位配置字符串，如果未找到返回None
    """
    cnf_tuple = extract_cnf_from_text(sy_content)
    if cnf_tuple:
        f, j, y = cnf_tuple
        parts = []
        if f > 0:
            parts.append(f"F/{f}")
        parts.append(f"J/{j}")
        parts.append(f"Y/{y}")
        return " ".join(parts)
    return None


def extract_aircraft_type_from_sy_content(sy_content: str) -> Optional[str]:
    """从SY内容提取机型

    查找包含机型信息的行
    例如: '777/30WA/B1428' -> '777/300A/B2045'

    Args:
        sy_content: SY命令内容

    Returns:
        机型字符串，如果未找到返回None
    """
    try:
        lines = sy_content.split("\n")
        # 机型信息通常在CWT行的下一行
        for i, line in enumerate(lines):
            if line.strip().startswith("CWT"):
                if i + 1 < len(lines):
                    next_line = lines[i + 1].strip()
                    if next_line:
                        # 提取第一个字段，格式类似 '777/30WA/B1428'
                        aircraft = next_line.split()[0]
                        return aircraft if aircraft else None
    except (IndexError, ValueError):
        return None
    return None


def extract_passenger_counts_from_sy_content(sy_content: str) -> PassengerCountsDict:
    """从SY内容提取乘客数量统计（R, C, SB, SA, RET, CET）
    从'*'开头的行开始，依次提取各行的乘客统计信息
    例如:
    - '*LAXPEK R035/326 C035/314...' -> {"R": [35, 326], "C": [35, 314]}
    - 'SB000/000' -> {"SB": [0, 0]}
    - 'SA000/004' -> {"SA": [0, 4]}
    - 'RET035/325 CET035/314' -> {"RET": [35, 325], "CET": [35, 314]}
    支持2个或3个数字的格式
    Args:
        sy_content: SY命令内容
    Returns:
        包含R, C, SB, SA, RET, CET乘客统计的字典，每个值为整数列表
        如果某个字段未找到，则不在字典中包含该字段
    """
    result: PassengerCountsDict = {}
    if not sy_content:
        return result
    try:
        lines = sy_content.split("\n")
        star_line_index = -1
        # 找到'*'开头的行
        for i, line in enumerate(lines):
            if line.strip().startswith("*"):
                star_line_index = i
                break
        if star_line_index == -1:
            return result
        # 从'*'行提取R
        star_line = lines[star_line_index].strip()
        r_match = re.search(r"R(\d+)/(\d+)(?:/(\d+))?", star_line)
        if r_match:
            if r_match.group(3):
                result["R"] = [
                    int(r_match.group(1)),
                    int(r_match.group(2)),
                    int(r_match.group(3)),
                ]
            else:
                result["R"] = [
                    int(r_match.group(1)),
                    int(r_match.group(2)),
                ]
        # 从'*'行提取C
        c_match = re.search(r"C(\d+)/(\d+)(?:/(\d+))?", star_line)
        if c_match:
            if c_match.group(3):
                result["C"] = [
                    int(c_match.group(1)),
                    int(c_match.group(2)),
                    int(c_match.group(3)),
                ]
            else:
                result["C"] = [
                    int(c_match.group(1)),
                    int(c_match.group(2)),
                ]
        # 从下一行提取SB
        if star_line_index + 1 < len(lines):
            sb_line = lines[star_line_index + 1].strip()
            sb_match = re.search(r"SB(\d+)/(\d+)(?:/(\d+))?", sb_line)
            if sb_match:
                if sb_match.group(3):
                    result["SB"] = [
                        int(sb_match.group(1)),
                        int(sb_match.group(2)),
                        int(sb_match.group(3)),
                    ]
                else:
                    result["SB"] = [
                        int(sb_match.group(1)),
                        int(sb_match.group(2)),
                    ]
        # 从再下一行提取SA
        if star_line_index + 2 < len(lines):
            sa_line = lines[star_line_index + 2].strip()
            sa_match = re.search(r"SA(\d+)/(\d+)(?:/(\d+))?", sa_line)
            if sa_match:
                if sa_match.group(3):
                    result["SA"] = [
                        int(sa_match.group(1)),
                        int(sa_match.group(2)),
                        int(sa_match.group(3)),
                    ]
                else:
                    result["SA"] = [
                        int(sa_match.group(1)),
                        int(sa_match.group(2)),
                    ]
        # 从再下一行提取RET和CET
        if star_line_index + 3 < len(lines):
            ret_cet_line = lines[star_line_index + 3].strip()
            # 提取RET
            ret_match = re.search(r"RET(\d+)/(\d+)(?:/(\d+))?", ret_cet_line)
            if ret_match:
                if ret_match.group(3):
                    result["RET"] = [
                        int(ret_match.group(1)),
                        int(ret_match.group(2)),
                        int(ret_match.group(3)),
                    ]
                else:
                    result["RET"] = [
                        int(ret_match.group(1)),
                        int(ret_match.group(2)),
                    ]
            # 提取CET
            cet_match = re.search(r"CET(\d+)/(\d+)(?:/(\d+))?", ret_cet_line)
            if cet_match:
                if cet_match.group(3):
                    result["CET"] = [
                        int(cet_match.group(1)),
                        int(cet_match.group(2)),
                        int(cet_match.group(3)),
                    ]
                else:
                    result["CET"] = [
                        int(cet_match.group(1)),
                        int(cet_match.group(2)),
                    ]
    except (IndexError, ValueError):
        pass
    return result


def extract_gtd_from_sy_content(sy_content: str) -> Optional[str]:
    """从SY内容提取GTD值

    例如: 'GTD/132' -> '132'

    Args:
        sy_content: SY命令内容

    Returns:
        GTD值，如果未找到返回None
    """
    try:
        lines = sy_content.split("\n")
        for line in lines:
            if "GTD/" in line:
                # 提取GTD/后面的值
                match = re.search(r"GTD/(\w+)", line)
                if match:
                    return match.group(1)
    except (IndexError, ValueError):
        return None
    return None


def extract_bdt_from_sy_content(content: str) -> Optional[str]:
    """从SY命令内容中提取BDT（Boarding Deadline Time）

    Args:
        content: SY命令的内容字符串

    Returns:
        提取的BDT时间（例如 "2230"），如果未找到则返回None
    """
    if not content:
        return None

    match = re.search(r"BDT(\d{4})", content)
    if match:
        return match.group(1)

    return None
