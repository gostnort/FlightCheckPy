#!/usr/bin/env python3
"""
PR Processor - Simplified PR to HBPR converter
Handles PR command processing by replacing PR headers with original HBPR headers from database
"""

import re
import streamlit as st
from scripts.data_cleaner import clean_text_for_input


def split_commands(content):
    """
    将PR内容按命令边界分割
    注意：此函数仅处理PR命令，HBPR由HbprProcessor处理
    Args:
        content: PR命令内容
    Returns:
        list: 命令列表
    """
    # 清理内容
    cleaned_content = clean_text_for_input(content)
    # 合并相同头部的PR段
    merged_content = merge_pr_sections(cleaned_content)
    # 使用正则表达式分割命令
    command_pattern = r'^(>PR:.*?)(?=^>PR:|\Z)'
    commands = []
    matches = re.findall(command_pattern, merged_content, re.MULTILINE | re.DOTALL)
    for match in matches:
        commands.append({
            'type': 'PR',
            'content': match.strip()
        })
    return commands


def extract_tkne_from_pr(pr_content):
    """
    从PR内容中提取TKNE号码
    Args:
        pr_content: PR命令内容
    Returns:
        list: TKNE号码列表
    """
    tkne_numbers = []
    # 匹配格式: ET TKNE/数字/数字 或 TKNE/数字/数字
    tkne_pattern = r'(?:ET\s+)?TKNE/(\d+)(?:/\d+)?'
    matches = re.findall(tkne_pattern, pr_content)
    for match in matches:
        tkne_numbers.append(match)  # 只返回主要的TKNE号码
    # 如果没有找到，尝试分解内容行来查找TKNE
    if not tkne_numbers:
        lines = pr_content.split('\n')
        for line in lines:
            # 分割每行的单词来查找TKNE属性
            words = line.split()
            for word in words:
                if word.startswith('TKNE/'):
                    tkne_part = word[5:]  # Remove "TKNE/" prefix
                    parts = tkne_part.split('/')
                    if len(parts) >= 1:
                        tkne_numbers.append(parts[0])  # 只返回主要的TKNE号码
                    break
    return list(set(tkne_numbers))  # 去重


def merge_pr_sections(pr_content):
    """
    合并多个相同头部的PR命令段
    只处理PR命令（>PR:），HBPR由HbprProcessor处理
    Args:
        pr_content: PR命令内容（仅包含>PR:段）
    Returns:
        str: 合并后的PR命令内容
    """
    # 按行分割
    lines = pr_content.splitlines()
    i = 0
    current_pr_header = None
    pr_sections_by_header = {}  # 按头部存储PR段
    while i < len(lines):
        current_line = lines[i].rstrip()
        # 检查是否是PR命令头行
        if current_line.strip().startswith('>PR:'):
            # 提取PR头部（去掉末尾的+ 或 -）
            pr_header = current_line.rstrip('+-').rstrip()
            current_pr_header = pr_header
            # 如果这个头部未见过，初始化
            if current_pr_header not in pr_sections_by_header:
                pr_sections_by_header[current_pr_header] = []
            i += 1
        elif current_line.strip() == '>':
            # 单独的>标记行，表示一个PR段的结束
            i += 1
        elif current_line.lstrip().startswith('-'):
            # 这是继续行的标记，移除行首的-标记
            if current_pr_header:
                content_line = current_line.lstrip().lstrip('-').rstrip()
                if content_line:  # 只加入非空行
                    pr_sections_by_header[current_pr_header].append(content_line)
            i += 1
        else:
            # 其他行直接属于当前PR
            if current_pr_header:
                pr_sections_by_header[current_pr_header].append(current_line)
            i += 1
    # 重新构建内容，将相同头部的PR段合并
    result_lines = []
    for pr_header, content_lines in pr_sections_by_header.items():
        result_lines.append(pr_header)
        result_lines.extend(content_lines)
        result_lines.append('')  # 添加空行分隔不同的PR命令
    return '\n'.join(result_lines)


def find_hbpr_header_by_tkne(db, tkne_number):
    """
    根据TKNE号码查找对应的HBPR记录头部
    Args:
        db: HbprDatabase instance
        tkne_number: TKNE number to search for
    Returns:
        dict: {
            'found': bool,
            'hbnb_number': int or None,
            'hbpr_header': str or None (从HBPR开始到点线之前的所有内容)
        }
    """
    try:
        conn = db.get_connection()
        cursor = conn.cursor()
        # 在tkne字段中查找匹配的TKNE号码
        cursor.execute("""
            SELECT hbnb_number, record_content
            FROM hbpr_full_records
            WHERE tkne LIKE ? OR tkne = ?
        """, (f'{tkne_number}/%', tkne_number))
        results = cursor.fetchall()
        if results:
            # 如果找到多个，返回第一个
            hbnb_number, record_content = results[0]
            # 提取HBPR头部（从开始到点线之前的所有内容）
            lines = record_content.split('\n')
            header_lines = []
            for line in lines:
                # 检查是否是点线（例如 "  1. "）
                if re.match(r'^\s*\d+\.', line):
                    break
                header_lines.append(line)
            hbpr_header = '\n'.join(header_lines)
            return {
                'found': True,
                'hbnb_number': hbnb_number,
                'hbpr_header': hbpr_header
            }
        else:
            return {
                'found': False,
                'hbnb_number': None,
                'hbpr_header': None
            }
    except Exception as e:
        return {
            'found': False,
            'hbnb_number': None,
            'hbpr_header': None,
            'error': str(e)
        }


def convert_pr_to_hbpr(pr_content, db):
    """
    将PR命令转换为HBPR命令
    通过查找数据库中的HBPR记录并替换头部
    Args:
        pr_content: PR命令内容
        db: HbprDatabase instance
    Returns:
        dict: {
            'success': bool,
            'converted_content': str or None,
            'hbnb_number': int or None,
            'error': str or None
        }
    """
    # 第一步：合并所有相同头部的PR段
    merged_pr_content = merge_pr_sections(pr_content)
    # 提取TKNE
    tkne_numbers = extract_tkne_from_pr(merged_pr_content)
    if not tkne_numbers:
        return {
            'success': False,
            'converted_content': None,
            'hbnb_number': None,
            'error': 'No TKNE found in PR command'
        }
    # 尝试每个TKNE查找匹配的HBPR记录
    for tkne in tkne_numbers:
        result = find_hbpr_header_by_tkne(db, tkne)
        if result['found']:
            # 找到匹配的HBPR记录
            hbpr_header = result['hbpr_header']
            hbnb_number = result['hbnb_number']
            # 分割PR内容，找到点线位置
            pr_lines = merged_pr_content.split('\n')
            dot_line_index = -1
            for i, line in enumerate(pr_lines):
                if re.match(r'^\s*\d+\.', line):
                    dot_line_index = i
                    break
            if dot_line_index == -1:
                return {
                    'success': False,
                    'converted_content': None,
                    'hbnb_number': None,
                    'error': 'No dot line found in PR command'
                }
            # 组合新内容：HBPR头部 + PR的点线及之后的内容
            pr_body = '\n'.join(pr_lines[dot_line_index:])
            converted_content = hbpr_header + '\n' + pr_body
            return {
                'success': True,
                'converted_content': converted_content,
                'hbnb_number': hbnb_number,
                'error': None
            }
    # 没有找到匹配的HBPR记录
    return {
        'success': False,
        'converted_content': None,
        'hbnb_number': None,
        'error': f'No matching HBPR record found for TKNE: {", ".join(tkne_numbers)}'
    }


def process_mixed_commands(content, db):
    """
    处理PR命令内容并转换为HBPR
    注意：此函数仅处理PR命令，HBPR由HbprProcessor处理
    Args:
        content: PR命令内容
        db: HbprDatabase instance
    Returns:
        dict: {
            'hbpr_commands': list,  # 已转换的HBPR命令列表
            'failed_pr_commands': list,  # 无法转换的PR命令列表
            'stats': dict  # 统计信息
        }
    """
    commands = split_commands(content)
    hbpr_commands = []
    failed_pr_commands = []
    stats = {
        'total_commands': len(commands),
        'pr_count': len(commands),
        'pr_converted': 0,
        'pr_failed': 0
    }
    for cmd in commands:
        if cmd['type'] == 'PR':
            # 尝试转换PR命令
            result = convert_pr_to_hbpr(cmd['content'], db)
            if result['success']:
                hbpr_commands.append({
                    'content': result['converted_content'],
                    'original_type': 'PR',
                    'hbnb_number': result['hbnb_number']
                })
                stats['pr_converted'] += 1
            else:
                failed_pr_commands.append({
                    'content': cmd['content'],
                    'error': result['error']
                })
                stats['pr_failed'] += 1
    return {
        'hbpr_commands': hbpr_commands,
        'failed_pr_commands': failed_pr_commands,
        'stats': stats
    }


def validate_pr_content(pr_content):
    """
    验证PR命令内容格式
    Args:
        pr_content: PR命令内容
    Returns:
        dict: {
            'is_valid': bool,
            'is_pr_command': bool,
            'errors': list
        }
    """
    result = {
        'is_valid': False,
        'is_pr_command': False,
        'errors': []
    }
    # 检查是否为空
    if not pr_content or not pr_content.strip():
        result['errors'].append("Content is empty")
        return result
    # 检查是否包含PR命令格式
    pr_pattern = r'>PR:\s*[^,\n]*'
    if not re.search(pr_pattern, pr_content):
        result['errors'].append("Not a valid PR command format")
        return result
    result['is_pr_command'] = True
    # 检查是否有点线
    if not re.search(r'^\s*\d+\.', pr_content, re.MULTILINE):
        result['errors'].append("No passenger line (starting with number and dot) found")
        return result
    # 检查TKNE
    if not extract_tkne_from_pr(pr_content):
        result['errors'].append("No TKNE found in PR command")
        return result
    result['is_valid'] = True
    return result


def display_processing_results(chbpr):
    """显示CHbpr处理结果"""
    # 验证状态
    if not chbpr.is_valid():
        st.error("❌ **Validation: FAILED**")
    # 错误信息
    if not chbpr.is_valid():
        st.subheader("⚠️ Validation Errors")
        for error_type, error_list in chbpr.error_msg.items():
            if error_list:  # 只显示有错误的类型
                st.subheader(f"🔴 {error_type} Errors")
                for error in error_list:
                    st.error(error)
    # 调试信息
    with st.expander("🔧 Debug Information"):
        for debug in chbpr.debug_msg:
            st.text(debug)

