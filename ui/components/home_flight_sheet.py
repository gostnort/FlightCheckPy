#!/usr/bin/env python3
"""
Home Flight Sheet组件 - 显示航班运行表格

提供类似sample_home_sheet.csv格式的航班信息展示，包括：
- 到达/出发航班信息
- 舱位配置
- 机型信息
- 乘客统计
- 特殊乘客分类
"""

import streamlit as st
import streamlit.components.v1
import json
import os
import re
from typing import Dict, List, Optional, Set
from scripts.commands_parsing.sy import (
    extract_flight_number_from_command_full,
    extract_date_from_command_full,
    extract_route_from_sy_content,
    extract_cnf_original_from_sy_content,
    extract_aircraft_type_from_sy_content,
    extract_passenger_counts_from_sy_content,
    extract_gtd_from_sy_content,
    extract_bdt_from_sy_content,
    is_departure_sy
)
from scripts.commands_parsing.airc import extract_inop_seats_from_airc_content


def load_home_sheet_filter_config() -> tuple:
    """加载flight sheet专用的属性过滤配置
    
    Returns:
        (排除的属性集合, 排除的属性模式列表) 元组
    """
    try:
        config_path = os.path.join('resources', 'filter_config.json')
        if os.path.exists(config_path):
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
                excluded = set(config.get('excluded_properties_home_sheet', []))
                # 也加载通用的excluded_properties和excluded_property_patterns
                excluded.update(config.get('excluded_properties', []))
                patterns = config.get('excluded_property_patterns', [])
                return excluded, patterns
        return set(), []
    except Exception:
        return set(), []


def normalize_property(prop: str) -> str:
    """标准化Properties：去除数字和斜杠后缀
    
    Args:
        prop: 原始属性字符串
        
    Returns:
        标准化后的属性
    """
    if not prop:
        return prop
    # 去除数字开始的后缀，如 INF1/0 -> INF, PAD-2/ -> PAD
    normalized = re.sub(r'[0-9/\-].*$', '', prop.strip())
    return normalized if normalized else prop


def should_exclude_property(prop: str, excluded_props: Set[str], excluded_patterns: List[str]) -> bool:
    """检查属性是否应该被排除
    
    Args:
        prop: 属性字符串
        excluded_props: 排除的属性集合
        excluded_patterns: 排除的属性模式列表（支持*通配符）
        
    Returns:
        True表示应该排除
    """
    if not prop or prop.strip() == '':
        return True
    prop = prop.strip()
    
    # 排除单字符属性（舱位等）
    if len(prop) == 1:
        return True
    
    # 检查是否在排除列表中
    if prop in excluded_props:
        return True
    
    # 检查标准化后的属性是否在排除列表中
    normalized_prop = normalize_property(prop)
    if normalized_prop in excluded_props:
        return True
    
    # 检查是否匹配排除模式
    for pattern in excluded_patterns:
        if pattern.endswith('*'):
            # 前缀匹配
            prefix = pattern[:-1]
            if prop.startswith(prefix) or normalized_prop.startswith(prefix):
                return True
        elif pattern == prop or pattern == normalized_prop:
            # 精确匹配
            return True
    
    return False


def get_special_passenger_counts(db) -> Dict[str, int]:
    """从数据库查询特殊乘客属性统计
    
    过滤掉home_sheet配置中排除的属性和模式
    特殊处理SXPS从ckin_msg列提取
    
    Args:
        db: 数据库客户端实例
        
    Returns:
        属性名称到数量的字典
    """
    excluded_props, excluded_patterns = load_home_sheet_filter_config()
    property_counts = {}
    
    try:
        conn = db.get_connection()
        cursor = conn.cursor()
        
        # 查询所有乘客的properties (排除XRES)
        cursor.execute("""
            SELECT DISTINCT hbnb_number, properties
            FROM hbpr_full_records
            WHERE properties IS NOT NULL AND properties != ''
                  AND properties NOT LIKE '%XRES%'
        """)
        
        rows = cursor.fetchall()
        
        # 统计每个属性的出现次数
        for hbnb_number, properties_str in rows:
            if properties_str:
                props = [p.strip() for p in properties_str.split(',') if p.strip()]
                for prop in props:
                    # 检查是否应该排除
                    if not should_exclude_property(prop, excluded_props, excluded_patterns):
                        # 标准化属性名
                        normalized = normalize_property(prop)
                        if normalized:
                            property_counts[normalized] = property_counts.get(normalized, 0) + 1
        
        # 特殊处理SXPS：从ckin_msg提取
        cursor.execute("""
            SELECT COUNT(DISTINCT hbnb_number)
            FROM hbpr_full_records
            WHERE boarding_number IS NOT NULL AND boarding_number > 0
                  AND ckin_msg IS NOT NULL
                  AND ckin_msg LIKE '%SXPS%'
        """)
        sxps_count = cursor.fetchone()[0]
        if sxps_count > 0:
            property_counts['SXPS'] = sxps_count
        
    except Exception as e:
        st.error(f"查询特殊乘客统计时出错: {e}")
    
    return property_counts


def has_required_sy_commands(db) -> bool:
    """检查数据库是否同时包含到达和出发SY命令
    Args:
        db: 数据库客户端实例
        
    Returns:
        True表示同时存在到达和出发SY命令
    """
    try:
        conn = db.get_connection()
        cursor = conn.cursor()    
        # 查询所有最新的SY命令
        cursor.execute("""
            SELECT command_full
            FROM commands
            WHERE command_type = 'SY' AND is_latest = 1
        """)       
        sy_commands = cursor.fetchall()       
        has_arrival = False
        has_departure = False        
        # 检查是否同时存在到达和出发SY
        for (command_full,) in sy_commands:
            if is_departure_sy(command_full):
                has_departure = True
            else:
                has_arrival = True          
            # 如果两者都找到了，可以提前返回
            if has_arrival and has_departure:
                return True      
        return False       
    except Exception:
        return False


def get_sy_commands(db) -> tuple:
    """获取最新的到达和出发SY命令   
    Args:
        db: 数据库客户端实例        
    Returns:
        (arrival_sy_dict, departure_sy_dict) 元组，每个dict包含command_full和content
    """
    try:
        conn = db.get_connection()
        cursor = conn.cursor()        
        # 查询所有最新的SY命令
        cursor.execute("""
            SELECT command_full, content
            FROM commands
            WHERE command_type = 'SY' AND is_latest = 1
            ORDER BY created_at DESC
        """)       
        sy_commands = cursor.fetchall()        
        arrival_sy = None
        departure_sy = None       
        # 区分到达和出发SY
        for command_full, content in sy_commands:
            if is_departure_sy(command_full):
                if not departure_sy:  # 只取第一个（最新的）
                    departure_sy = {'command_full': command_full, 'content': content}
            else:
                if not arrival_sy:
                    arrival_sy = {'command_full': command_full, 'content': content}       
        return arrival_sy, departure_sy        
    except Exception as e:
        st.error(f"获取SY命令时出错: {e}")
        return None, None


def get_airc_command(db) -> Optional[Dict[str, str]]:
    """获取最新的AIRC命令
    
    Args:
        db: 数据库客户端实例
        
    Returns:
        包含command_full和content的字典，如果不存在返回None
    """
    try:
        conn = db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT command_full, content
            FROM commands
            WHERE command_type = 'AIRC' AND is_latest = 1
            ORDER BY created_at DESC
            LIMIT 1
        """)
        
        row = cursor.fetchone()
        if row:
            return {'command_full': row[0], 'content': row[1]}
        return None
        
    except Exception as e:
        st.error(f"获取AIRC命令时出错: {e}")
        return None


def get_duplicate_seats(db) -> str:
    """查询数据库中重复的座位号及对应的乘客姓名
    Args:
        db: 数据库客户端实例
    Returns:
        格式化的重复座位字符串，例如: "31K: SMITH/JOHN, DOE/JANE; 45A: WANG/LI, CHEN/WEI"
    """
    try:
        conn = db.get_connection()
        cursor = conn.cursor()
        # 查询重复的座位 (只统计非XRES乘客)
        cursor.execute("""
            SELECT seat,
                   GROUP_CONCAT(name, ',') as names,
                   COUNT(*) as count
            FROM (
                SELECT seat, name
                FROM hbpr_full_records
                WHERE properties IS NOT NULL
                      AND properties != ''
                      AND properties NOT LIKE '%XRES%'
                      AND seat IS NOT NULL
                      AND seat != ''
            )
            GROUP BY seat
            HAVING COUNT(*) > 1
            ORDER BY seat
        """)
        duplicate_rows = cursor.fetchall()
        if duplicate_rows:
            # 格式化为字符串
            dup_list = []
            for seat, names, count in duplicate_rows:
                dup_list.append(f"{seat} = {names}")
            return ' ; '.join(dup_list)
        return ""
        
    except Exception as e:
        st.error(f"查询重复座位时出错: {e}")
        return ""


def build_flight_sheet_data(db) -> List[List[str]]:
    """构建8列x13行的flight sheet数据（带常量模板）
    返回二维列表，每个元素是单元格内容
    Args:
        db: 数据库客户端实例
    Returns:
        8列x13行的二维列表
    """
    # 初始化13行8列的空表格，包含常量值（模板）
    sheet_data = [
        # Row 1: Flight Info
        ["", "", "", "", "", "DATE:", "", ""],
        # Row 2: Seat Conf. and Times
        ["Seat Conf.", "", "", "", '="STD: " & IFERROR(VLOOKUP(M1,Parameter!$O:$S,3,0),"---")', '="ETD: " & IFERROR(VLOOKUP(M1,Parameter!$O:$S,4,0),"---")', '="ETA: " & IFERROR(VLOOKUP(M1,Parameter!$O:$S,5,0),"---")', ""],
        # Row 3: MAX
        ["MAX", "", "", "", "", "", "", ""],
        # Row 4: A/C Reg.
        ["A/C Reg.", "", "", "", "BDT", "", "", ""],
        # Row 5: Pax Counts
        ["J/Y = TTL", "", "", "", "J/Y=TTL", "", "", ""],
        # Row 6: ETA/GTD
        ["ETA", "", "", "", "GTD", "","",'=IFERROR(VLOOKUP(LEFT(N6,3),Parameter!$L:$M,2,0),"---")'],
        # Row 7: Comment
        ["Commemt", "", "", "", "", "", "", ""],
        # Row 8: INOP seats
        ["", "", "", "", "", "", "", ""],
        # Row 9: Duplicate seats
        ["", "", "", "", "", "", "", ""],
        # Row 10: empty / overflow
        ["", "", "", "", "", "", "", ""],
        # Row 11: Overflow properties / Special pax
        ["", "", "", "", "", "", "", ""],
        # Row 12: Special passengers
        ["", "", "", "", "", "", "", ""],
        # Row 13: Special passengers
        ["", "", "", "", "", "", "", ""],
    ]
    # 获取命令数据
    arrival_sy, departure_sy = get_sy_commands(db)
    airc_cmd = get_airc_command(db)
    duplicate_seats = get_duplicate_seats(db) 
    # Row 1 - 航班信息
    if arrival_sy:
        # col 2 (idx 1): arrival flight number
        sheet_data[0][1] = extract_flight_number_from_command_full(arrival_sy['command_full']) or ""
        # col 3 (idx 2): arrival flight route
        sheet_data[0][2] = extract_route_from_sy_content(arrival_sy['content']) or ""
    if departure_sy:
        # col 5 (idx 4): departure flight number
        sheet_data[0][4] = extract_flight_number_from_command_full(departure_sy['command_full']) or ""
        # col 6 (idx 5): departure flight route
        sheet_data[0][5] = extract_route_from_sy_content(departure_sy['content']) or ""
        # col 8 (idx 7): departure flight date
        sheet_data[0][7] = extract_date_from_command_full(departure_sy['command_full']) or ""
    # Row 2 - 舱位配置
    if departure_sy:
        # col 3 (idx 2): CNF配置
        cnf_str = extract_cnf_original_from_sy_content(departure_sy['content'])
        if cnf_str:
            sheet_data[1][2] = cnf_str
    # Row 3 - MAX, no data to fill
    # Row 4 - 机型
    if departure_sy:
        # col 3 (idx 2): 出发机型
        aircraft = extract_aircraft_type_from_sy_content(departure_sy['content'])
        if aircraft:
            sheet_data[3][2] = aircraft
        # col 8 (idx 7): "BDT"
        bdt = extract_bdt_from_sy_content(departure_sy['content'])
        if bdt:
            sheet_data[3][7] = bdt
    # Row 5 - 乘客统计
    if arrival_sy:
        # 列3(索引2): 到达乘客统计
        pax_count = extract_passenger_counts_from_sy_content(arrival_sy['content'])
        if pax_count:
            sheet_data[4][2] = pax_count
            # 根据pax_count中的斜杠数量设置列1(索引0)的标签
            slash_count = pax_count.count('/')
            if slash_count == 2:
                sheet_data[4][0] = 'F/J/Y = TTL'
    if departure_sy:
        # 列7(索引6): 出发乘客统计
        pax_count = extract_passenger_counts_from_sy_content(departure_sy['content'])
        if pax_count:
            sheet_data[4][6] = pax_count
            # 根据pax_count中的斜杠数量设置列5(索引4)的标签
            slash_count = pax_count.count('/')
            if slash_count == 2:
                sheet_data[4][4] = 'F/J/Y = TTL'
    # Row 6 - GTD值
    if departure_sy:
        # col 6 (idx 5): GTD值
        gtd = extract_gtd_from_sy_content(departure_sy['content'])
        if gtd:
            sheet_data[5][5] = gtd
    # Row 8 - INOP座位（索引7）
    if airc_cmd:
        inop_seats = extract_inop_seats_from_airc_content(airc_cmd['content'])
        sheet_data[7][0] = inop_seats
    # Row 9 - 重复座位（索引8）
    if duplicate_seats:
        sheet_data[8][0] = duplicate_seats
    # Rows 12-13 - 特殊乘客统计（列2-8，即索引1-7）
    special_pax = get_special_passenger_counts(db)
    # 按字母顺序排序属性
    sorted_props = sorted(special_pax.items())
    # 填充到表格的第12和13行（索引11和12），列2-8（索引1-7）
    # 每行7个单元格（列2-8），共14个位置
    cell_index = 0
    overflow_props = []
    for prop, count in sorted_props:
        if cell_index < 14:  # 最多14个单元格（两行×7列）
            row_idx = 11 + (cell_index // 7)  # 第12或13行（索引11和12）
            col_idx = 1 + (cell_index % 7)  # 列索引1-7（列2-8）
            sheet_data[row_idx][col_idx] = f"{count} {prop}"
            cell_index += 1
        else:
            # 超过14个的属性放入溢出列表
            overflow_props.append(f"{count} {prop}")
    # 如果有溢出属性，将它们作为字符串放入第11行（索引10）
    if overflow_props:
        overflow_str = ', '.join(overflow_props)
        sheet_data[10][0] = overflow_str
    return sheet_data


def convert_to_html_table(data: List[List[str]]) -> str:
    """将表格数据转换为HTML格式，用于Excel剪贴板
    
    Args:
        data: 8列x13行的二维列表
        
    Returns:
        HTML格式的表格字符串（Excel兼容）
    """
    # 构建HTML表格，使用Excel兼容的格式
    html_parts = ['<table xmlns:x="urn:schemas-microsoft-com:office:excel">']
    
    for row in data:
        html_parts.append('<tr>')
        for cell in row:
            cell_str = str(cell)
            # 转义HTML特殊字符
            cell_content = cell_str.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
            
            # 检查是否是Excel公式
            if cell_str.startswith('='):
                # 保留公式
                html_parts.append(f'<td x:fmla="{cell_content}">{cell_content}</td>')
            else:
                html_parts.append(f'<td>{cell_content}</td>')
        html_parts.append('</tr>')
    
    html_parts.append('</table>')
    return ''.join(html_parts)


def render_flight_sheet_table(data: List[List[str]]) -> None:
    """渲染flight sheet表格（紧凑显示+复制按钮）
    Args:
        data: 8列x13行的二维列表
    """
    # 生成HTML格式的表格用于复制
    html_table_full = convert_to_html_table(data)
    
    # 使用JSON编码来安全地传递HTML到JavaScript
    html_full_json = json.dumps(html_table_full)
    
    # 构建显示用的HTML表格
    table_rows = []
    for row_idx, row in enumerate(data):
        # 行8-11（索引7-10）：INOP座位、重复座位、溢出属性等，需要跨列显示
        if row_idx == 2:
            continue
        if row_idx in [7, 8, 9, 10]:
            # 获取第一列的内容（完整字符串）
            cell_content = str(row[0]).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
            if not cell_content.strip():
                cell_content = "&nbsp;"
            # 创建跨8列的单元格
            table_rows.append(f"<tr><td colspan='8'>{cell_content}</td></tr>")
        else:
            # 普通行，逐列显示
            cells = []
            for cell in row:
                cell_str = str(cell)
                # 对于Excel公式，在显示时只显示提示文本，不显示完整公式
                if cell_str.startswith('='):
                    display_content = '(ExcelFormula)'
                else:
                    # 转义HTML特殊字符
                    display_content = cell_str.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
                # 空单元格使用&nbsp;
                if not display_content.strip():
                    display_content = "&nbsp;"
                cells.append(f"<td>{display_content}</td>")
            table_rows.append("<tr>" + "".join(cells) + "</tr>")
    
    # HTML样式和表格
    html_table = f"""
    <style>
        .flight-sheet-table {{
            width: 100%;
            border-collapse: collapse;
            font-family: 'Courier New', monospace;
            font-size: 13px;
            table-layout: fixed;
        }}
        .flight-sheet-table td {{
            border: 1px solid #ddd;
            padding: 8px 6px;
            text-align: left;
            vertical-align: middle;
            white-space: pre-wrap;
            word-wrap: break-word;
            line-height: 1.2;
            max-height: 40px;
            overflow: hidden;
        }}
        .flight-sheet-table tr {{
            line-height: 1.2;
        }}
        .flight-sheet-table tr:nth-child(even) {{
            background-color: #f9f9f9;
        }}
        .flight-sheet-table td[colspan] {{
            font-weight: normal;
        }}
    </style>
    <table class="flight-sheet-table">{"".join(table_rows)}</table>
    """
    
    # 渲染HTML表格
    st.markdown(html_table, unsafe_allow_html=True)
    
    # 创建复制到剪贴板的HTML和JavaScript（放在表格底部）
    copy_button_html = f"""
    <div style="margin: 10px 0 0 0; padding: 0;">
        <button onclick="copyToClipboard()" style="
            background-color: #FF4B4B;
            color: white;
            border: none;
            padding: 6px 12px;
            border-radius: 4px;
            cursor: pointer;
            font-size: 13px;
        ">📋 Copy to Clipboard</button>
        
        <div id="copyStatus" style="color: green; font-size: 11px; margin: 5px 0 0 0; padding: 0;"></div>
    </div>
    
    <script>
    function copyToClipboard() {{
        const htmlContent = {html_full_json};
        
        // 创建HTML Blob用于剪贴板
        const htmlBlob = new Blob([htmlContent], {{ type: 'text/html' }});
        const textBlob = new Blob([htmlContent], {{ type: 'text/plain' }});
        
        const clipboardItem = new ClipboardItem({{
            'text/html': htmlBlob,
            'text/plain': textBlob
        }});
        
        navigator.clipboard.write([clipboardItem]).then(function() {{
            document.getElementById('copyStatus').innerText = '✓ 已复制到剪贴板（可直接粘贴到Excel）';
            document.getElementById('copyStatus').style.color = 'green';
            setTimeout(function() {{
                document.getElementById('copyStatus').innerText = '';
            }}, 3000);
        }}, function(err) {{
            console.error('复制失败:', err);
            document.getElementById('copyStatus').innerText = '✗ 复制失败: ' + err.message;
            document.getElementById('copyStatus').style.color = 'red';
        }});
    }}
    </script>
    """
    
    # 显示复制按钮（放在底部）
    st.components.v1.html(copy_button_html, height=70)
    
    # 添加说明
    st.caption("💡 点击按钮复制完整表格到剪贴板（可直接粘贴到Excel）")

