#!/usr/bin/env python3
"""
Command processor for airline system commands
Processes and analyzes commands from command text files
"""

import re
import sqlite3
import os
from datetime import datetime
from typing import Dict, List, Optional, Any


class CommandProcessor:
    """Process and manage airline system commands"""


    def __init__(self, db_file: str = None):
        """
        Initialize command processor
        Args:
            db_file (str, optional): Path to database file for flight info validation
        """
        self.db_file = db_file
        self.flight_info = None
        if db_file:
            self._load_flight_info()


    def _load_flight_info(self):
        """Load flight information from HBPR database"""
        if not self.db_file or not os.path.exists(self.db_file):
            return
        try:
            conn = sqlite3.connect(self.db_file)
            # 检查flight_info表是否存在
            cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='flight_info'")
            if not cursor.fetchone():
                conn.close()
                return
            cursor = conn.execute("SELECT flight_id, flight_number, flight_date FROM flight_info LIMIT 1")
            row = cursor.fetchone()
            if row:
                self.flight_info = {
                    'flight_id': row[0],
                    'flight_number': row[1], 
                    'flight_date': row[2]
                }
            conn.close()
        except Exception as e:
            pass


    def parse_commands_from_text(self, text_content: str) -> List[Dict[str, Any]]:
        """
        Parse commands from text content
        Args:
            text_content (str): Raw text content containing commands
        Returns:
            List[Dict[str, Any]]: List of parsed commands
        """
        commands = []
        lines = text_content.split('\n')
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            # 跳过空行
            if not line:
                i += 1
                continue
            # 检查是否包含命令（有':'）
            if ':' in line:
                command_info = self._parse_command_line(line)
                if command_info:
                    # 提取命令内容直到下一个'>'或结束
                    content_lines = []
                    content_start = i + 1
                    # 查找内容直到下一个命令或'>'
                    j = content_start
                    while j < len(lines):
                        content_line = lines[j]
                        # 在下一个以'>'开头的命令处停止
                        if content_line.strip().startswith('>') and j > i:
                            break
                        content_lines.append(content_line)
                        j += 1
                    # 合并命令信息和内容
                    # 存储完整的原始输入（包括命令行和后续内容）
                    raw_command_line = lines[i]  # 保留原始命令行（完全原样）
                    if content_lines:
                        # 保留原始格式，包括所有空格和格式
                        full_raw_content = raw_command_line + '\n' + '\n'.join(content_lines)
                    else:
                        full_raw_content = raw_command_line
                    command_data = {
                        **command_info,
                        'content': full_raw_content,  # 存储完整的原始输入，不使用strip()以保留格式
                        'line_number': i + 1
                    }
                    commands.append(command_data)
                    i = j  # 移动到下一个命令
                else:
                    i += 1
            else:
                i += 1
        return self._merge_duplicate_commands(commands)


    def _parse_command_line(self, line: str) -> Optional[Dict[str, str]]:
        """
        Parse a command line to extract command information
        Args:
            line (str): Command line to parse
        Returns:
            Optional[Dict[str, str]]: Parsed command info or None
        """
        # 应用特殊字符处理
        corrected_line = self._apply_character_corrections(line)
        # 移除前导'>'如果存在
        corrected_line = corrected_line.lstrip('>')
        # 使用正则表达式提取命令：r"[A-Z]{2,4}:\s?.+?(?=\s{2})"
        # 修改后可以兼容毫无空格的指令
        pattern = r"([A-Z]{2,4}):\s?(.+?)(?=\s{2,}|\s*$)"
        match = re.search(pattern, corrected_line)
        if match:
            command_prefix = match.group(1).strip()
            command_part = match.group(2).strip()
            # 完整命令是prefix:command_part
            full_command = f"{command_prefix}:{command_part}"
            # 从命令中提取航班信息
            flight_info = self._extract_flight_info(full_command)
            return {
                'command_type': command_prefix,
                'command_full': full_command,
                'flight_number': flight_info.get('flight_number', ''),
                'flight_date': flight_info.get('flight_date', '')
            }
        return None


    def _apply_character_corrections(self, line: str) -> str:
        """
        Apply character corrections to command line
        Similar to validate_full_hbpr_record logic for special characters
        Args:
            line (str): Command line to correct
        Returns:
            str: Corrected command line
        """
        corrected_line = line
        # 处理DLE字符(ASCII 16, \x10)
        if '\x10' in corrected_line:
            corrected_line = corrected_line.replace('\x10', '>')
        # 处理DEL字符(ASCII 127, \x7f)
        elif '\x7f' in corrected_line:
            corrected_line = corrected_line.replace('\x7f', '>')
        # 处理其他控制字符
        elif re.search(r'[\x00-\x1f\x7f]', corrected_line):
            corrected_line = re.sub(r'[\x00-\x1f\x7f]', '>', corrected_line)
        # 处理可见的"del"文本(不区分大小写)
        elif re.search(r'del[A-Z]{2,4}:', corrected_line, re.IGNORECASE):
            corrected_line = re.sub(r'del([A-Z]{2,4}:)', r'>\1', corrected_line, flags=re.IGNORECASE)
        # 如果命令行没有>前缀且严格符合命令模式，添加它
        elif re.match(r'^[A-Z]{2,4}:\s*[A-Z0-9]', corrected_line):
            corrected_line = '>' + corrected_line
        return corrected_line


    def _extract_flight_info(self, command: str) -> Dict[str, str]:
        """
        Extract flight number and date from command
        Args:
            command (str): Command string
        Returns:
            Dict[str, str]: Flight info with flight_number and flight_date
        """
        # 匹配航班信息的模式，如CA984/25JUL25或CA0984/25JUL
        pattern = r'(CA\d+)/(\d{1,2}[A-Z]{3}\d{0,2})'
        match = re.search(pattern, command, re.IGNORECASE)
        if match:
            flight_number = match.group(1).upper()
            flight_date = match.group(2).upper()
            return {'flight_number': flight_number, 'flight_date': flight_date}
        return {'flight_number': '', 'flight_date': ''}


    def _parse_flight_info(self, flight_info_str: str) -> Dict[str, Any]:
        """
        Parse flight info string like "CA984/25JUL25" into components
        Args:
            flight_info_str (str): Flight info string
        Returns:
            Dict[str, Any]: Parsed flight info with airline, flight_number, flight_date
        """
        if not flight_info_str or '/' not in flight_info_str:
            return {'airline': '', 'flight_number': '', 'flight_date': ''}
        parts = flight_info_str.split('/', 1)
        if len(parts) != 2:
            return {'airline': '', 'flight_number': '', 'flight_date': ''}
        flight_part = parts[0].strip().upper()
        date_part = parts[1].strip().upper()
        # 提取航空公司和航班号
        if flight_part.startswith('CA'):
            airline = 'CA'
            flight_number = flight_part[2:]  # 移除'CA'前缀
        else:
            airline = ''
            flight_number = flight_part
        # 解析日期
        date_obj = self._parse_flight_date(date_part)
        return {
            'airline': airline,
            'flight_number': flight_number,
            'flight_date': date_part,
            'date_obj': date_obj
        }


    def _parse_flight_date(self, date_str: str) -> Optional[datetime]:
        """
        Parse flight date string to datetime object using built-in datetime
        Args:
            date_str (str): Date string like "25JUL25" or "25JUL"
        Returns:
            Optional[datetime]: Parsed date or None
        """
        if not date_str:
            return None
        try:
            # 首先尝试解析年份（DDMMMYY格式）
            if len(date_str) >= 7:  # 有年份
                return datetime.strptime(date_str.upper(), "%d%b%y")
            else:  # 没有年份，使用当前年份
                date_with_year = f"{date_str.upper()}{datetime.now().year % 100}"
                return datetime.strptime(date_with_year, "%d%b%y")
        except ValueError:
            return None


    def _merge_duplicate_commands(self, commands: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Merge commands that have the same command_full but different content
        Args:
            commands (List[Dict[str, Any]]): List of parsed commands
        Returns:
            List[Dict[str, Any]]: List of merged commands
        """
        merged_commands = {}
        for cmd in commands:
            key = (cmd['command_full'], cmd['flight_number'], cmd['flight_date'])
            if key in merged_commands:
                # 合并内容
                existing_content = merged_commands[key]['content']
                new_content = cmd['content']
                # 仅在不同内容时添加
                if new_content and new_content not in existing_content:
                    merged_commands[key]['content'] += '\n' + new_content
            else:
                merged_commands[key] = cmd.copy()
        return list(merged_commands.values())


    def validate_flight_info(self, flight_number: str, flight_date: str) -> bool:
        """
        Validate if flight info matches database
        Args:
            flight_number (str): Flight number to validate (e.g., "CA984")
            flight_date (str): Flight date to validate (e.g., "25JUL25")
        Returns:
            bool: True if matches database flight info
        """
        if not self.flight_info:
            return True  # 如果没有加载航班信息则不验证
        # 解析命令航班信息
        flight_info_str = f"{flight_number}/{flight_date}"
        parsed_info = self._parse_flight_info(flight_info_str)
        if not parsed_info['airline'] or not parsed_info['flight_number']:
            return False
        # 构建完整航班号（航空公司+航班号）
        command_flight_number = f"{parsed_info['airline']}{parsed_info['flight_number']}"
        db_flight_number = self.flight_info['flight_number']
        # 处理CA984 vs CA0984匹配
        command_normalized = command_flight_number.replace('CA0', 'CA')
        db_normalized = db_flight_number.replace('CA0', 'CA')
        # 匹配航班号
        number_match = (command_normalized.upper() == db_normalized.upper())
        # 匹配航班日期
        date_match = self._compare_flight_dates(flight_date, self.flight_info['flight_date'])
        return number_match and date_match


    def _compare_flight_dates(self, date1: str, date2: str) -> bool:
        """
        Compare flight dates in different formats
        Args:
            date1 (str): First date
            date2 (str): Second date
        Returns:
            bool: True if dates match
        """
        # 将两个日期标准化为相同格式
        normalized_date1 = self._normalize_flight_date(date1)
        normalized_date2 = self._normalize_flight_date(date2)
        return normalized_date1 == normalized_date2


    def _normalize_flight_date(self, date_str: str) -> str:
        """
        Normalize flight date to standard format
        Args:
            date_str (str): Date string to normalize
        Returns:
            str: Normalized date string
        """
        if not date_str:
            return ''
        # 处理像25JUL25、25JUL等格式
        date_str = date_str.upper().strip()
        # 如果已经是DDMMMYY格式，直接返回
        if re.match(r'\d{1,2}[A-Z]{3}\d{0,2}', date_str):
            return date_str
        return date_str


    def store_commands(self, commands: List[Dict[str, Any]]) -> Dict[str, int]:
        """
        Store commands in database with atomic transaction
        Args:
            commands (List[Dict[str, Any]]): Commands to store
        Returns:
            Dict[str, int]: Statistics about stored commands
        Raises:
            Exception: If database operation fails
        """
        if not self.db_file:
            raise Exception("No database file specified")
        if not commands:
            return {'new': 0, 'updated': 0, 'skipped': 0, 'errors': 0}
        stats = {'new': 0, 'updated': 0, 'skipped': 0, 'errors': 0}
        conn = None
        try:
            conn = sqlite3.connect(self.db_file)
            # 关键：启用外键并设置超时
            conn.execute("PRAGMA foreign_keys = ON")
            conn.execute("PRAGMA busy_timeout = 30000")  # 30秒超时
            # 关键：开始事务以确保原子性
            conn.execute("BEGIN TRANSACTION")
            # 如果不存在则创建commands表（支持时间线版本控制）
            conn.execute("""
                CREATE TABLE IF NOT EXISTS commands (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    command_full TEXT NOT NULL,
                    command_type TEXT,
                    flight_number TEXT,
                    flight_date TEXT,
                    content TEXT,
                    version INTEGER DEFAULT 1,
                    parent_id INTEGER,
                    is_latest BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            # 创建索引以提高查询性能
            conn.execute("CREATE INDEX IF NOT EXISTS idx_commands_timeline ON commands(command_full, version)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_commands_parent ON commands(parent_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_commands_latest ON commands(command_full, is_latest)")
            # 过滤命令，只存储匹配数据库航班信息的命令
            matching_commands = []
            mismatched_commands = []
            for cmd in commands:
                if self.validate_flight_info(cmd['flight_number'], cmd['flight_date']):
                    matching_commands.append(cmd)
                else:
                    mismatched_commands.append(cmd)
            # 只存储匹配的命令（支持版本控制）
            for cmd in matching_commands:
                try:
                    # 检查命令是否已存在的最新版本
                    cursor = conn.execute("""
                        SELECT id, version, content 
                        FROM commands 
                        WHERE command_full = ? AND is_latest = TRUE
                    """, (cmd['command_full'],))
                    existing = cursor.fetchone()
                    if existing:
                        existing_id, existing_version, existing_content = existing
                        # 如果内容不同，创建新版本
                        if existing_content != cmd['content']:
                            # 标记旧版本为不是最新
                            conn.execute("""
                                UPDATE commands 
                                SET is_latest = FALSE 
                                WHERE id = ?
                            """, (existing_id,))
                            # 插入新版本
                            new_version = existing_version + 1
                            conn.execute("""
                                INSERT INTO commands (
                                    command_full, command_type, flight_number, flight_date, 
                                    content, version, parent_id, is_latest, created_at, updated_at
                                ) VALUES (?, ?, ?, ?, ?, ?, ?, TRUE, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                            """, (
                                cmd['command_full'], cmd['command_type'],
                                cmd['flight_number'], cmd['flight_date'],
                                cmd['content'], new_version, existing_id
                            ))
                            stats['updated'] += 1
                        else:
                            # 内容相同，只更新时间戳
                            conn.execute("""
                                UPDATE commands 
                                SET updated_at = CURRENT_TIMESTAMP 
                                WHERE id = ?
                            """, (existing_id,))
                            stats['skipped'] += 1
                    else:
                        # 新命令
                        conn.execute("""
                            INSERT INTO commands (
                                command_full, command_type, flight_number, flight_date, 
                                content, version, is_latest, created_at, updated_at
                            ) VALUES (?, ?, ?, ?, ?, 1, TRUE, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                        """, (
                            cmd['command_full'], cmd['command_type'],
                            cmd['flight_number'], cmd['flight_date'],
                            cmd['content']
                        ))
                        stats['new'] += 1
                except Exception as e:
                    stats['errors'] += 1
                    # 关键：如果任何命令失败，回滚整个事务
                    raise Exception(f"Failed to store command {cmd['command_full']}: {e}")
            # 关键：只有在所有命令都成功存储后才提交事务
            conn.commit()
            # 将跳过计数设置为不匹配命令的数量以供参考
            stats['skipped'] = len(mismatched_commands)
        except Exception as e:
            # 关键：任何错误时回滚事务
            if conn:
                try:
                    conn.rollback()
                except Exception:
                    pass
            # 重新抛出异常供调用者处理
            raise Exception(f"Database operation failed: {e}")
        finally:
            # 关键：始终关闭连接
            if conn:
                try:
                    conn.close()
                except Exception:
                    pass
        return stats


    def get_all_commands_data(self) -> List[Dict[str, Any]]:
        """Get all commands data from database"""
        if not self.db_file:
            return []
        try:
            conn = sqlite3.connect(self.db_file)
            # 首先检查commands表是否存在
            cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='commands'")
            if not cursor.fetchone():
                conn.close()
                return []
            cursor = conn.execute("""
                SELECT id, command_full, command_type, flight_number, flight_date, 
                       content, version, parent_id, is_latest, created_at, updated_at 
                FROM commands 
                WHERE is_latest = TRUE
                ORDER BY created_at DESC
            """)
            columns = [desc[0] for desc in cursor.description]
            rows = cursor.fetchall()
            conn.close()
            return [dict(zip(columns, row)) for row in rows]
        except Exception as e:
            return []


    def get_command_types(self) -> List[str]:
        """Get all unique command types"""
        if not self.db_file:
            return []
        try:
            conn = sqlite3.connect(self.db_file)
            cursor = conn.execute("SELECT DISTINCT command_type FROM commands WHERE command_type IS NOT NULL AND is_latest = TRUE")
            command_types = [row[0] for row in cursor.fetchall()]
            conn.close()
            return sorted(command_types)
        except Exception as e:
            print(f"Error getting command types: {e}")
            return []


    def get_command_timeline(self, command_full: str) -> List[Dict[str, Any]]:
        """Get timeline data for a specific command"""
        if not self.db_file:
            return []
        try:
            conn = sqlite3.connect(self.db_file)
            cursor = conn.execute("""
                SELECT id, command_full, command_type, flight_number, flight_date, 
                       content, version, parent_id, is_latest, created_at, updated_at 
                FROM commands 
                WHERE command_full = ? 
                ORDER BY version ASC
            """, (command_full,))
            columns = [desc[0] for desc in cursor.description]
            rows = cursor.fetchall()
            conn.close()
            return [dict(zip(columns, row)) for row in rows]
        except Exception as e:
            print(f"Error getting command timeline: {e}")
            return []


    def get_all_commands_with_versions(self) -> List[Dict[str, Any]]:
        """Get all commands including all versions (for timeline view)"""
        if not self.db_file:
            return []
        try:
            conn = sqlite3.connect(self.db_file)
            cursor = conn.execute("""
                SELECT id, command_full, command_type, flight_number, flight_date, 
                       content, version, parent_id, is_latest, created_at, updated_at 
                FROM commands 
                ORDER BY command_full, version ASC
            """)
            columns = [desc[0] for desc in cursor.description]
            rows = cursor.fetchall()
            conn.close()
            return [dict(zip(columns, row)) for row in rows]
        except Exception as e:
            print(f"Error getting all commands with versions: {e}")
            return []


    def erase_commands_table(self) -> bool:
        """
        Erase all data from the commands table
        Returns:
            bool: True if successful, False otherwise
        """
        if not self.db_file or not os.path.exists(self.db_file):
            return False
        conn = None
        try:
            conn = sqlite3.connect(self.db_file)
            # 检查commands表是否存在
            cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='commands'")
            if not cursor.fetchone():
                return True
            # 删除前获取计数
            cursor = conn.execute("SELECT COUNT(*) FROM commands")
            count = cursor.fetchone()[0]
            # 开始事务
            conn.execute("BEGIN TRANSACTION")
            # 从commands表删除所有记录
            conn.execute("DELETE FROM commands")
            # 重置自增计数器
            conn.execute("DELETE FROM sqlite_sequence WHERE name='commands'")
            # 提交事务
            conn.commit()
            return True
        except Exception as e:
            # 错误时回滚
            if conn:
                try:
                    conn.rollback()
                except Exception:
                    pass
            return False
        finally:
            # 始终关闭连接
            if conn:
                try:
                    conn.close()
                except Exception:
                    pass


    def close(self):
        """Close database connections"""
        pass  # No persistent connections to close


def main():
    """
    Comprehensive test function for CommandProcessor
    Tests parsing sample commands, database operations, and flight info validation
    """
    print("🚀 COMMAND PROCESSOR TEST")
    print("=" * 50)
    # 测试配置
    db_file = "databases/CA984_25JUL25.db"
    sample_file = "sample_commands.txt"
    # 检查文件是否存在
    if not os.path.exists(db_file):
        print(f"❌ Database file not found: {db_file}")
        return
    if not os.path.exists(sample_file):
        print(f"❌ Sample commands file not found: {sample_file}")
        return
    # 初始化命令处理器
    processor = CommandProcessor(db_file)
    # 清除现有commands表数据
    if not processor.erase_commands_table():
        print("❌ Failed to clear commands table")
        return
    # 加载航班信息
    if processor.flight_info:
        print(f"✅ Flight: {processor.flight_info['flight_number']}/{processor.flight_info['flight_date']}")
    else:
        print("⚠️ No flight info loaded")
    # 读取和解析示例命令
    try:
        with open(sample_file, 'r', encoding='utf-8') as f:
            sample_content = f.read()
        commands = processor.parse_commands_from_text(sample_content)
        print(f"📖 Parsed {len(commands)} commands")
    except Exception as e:
        print(f"❌ Error parsing sample file: {e}")
        return
    # 验证航班信息
    matching_commands = []
    non_matching_commands = []
    for cmd in commands:
        if processor.validate_flight_info(cmd['flight_number'], cmd['flight_date']):
            matching_commands.append(cmd)
        else:
            non_matching_commands.append(cmd)
    print(f"✅ Matching: {len(matching_commands)}, Non-matching: {len(non_matching_commands)}")
    # 在数据库中存储命令
    try:
        stats = processor.store_commands(commands)
        print(f"💾 Stored: {stats['new']} new, {stats['updated']} updated, {stats['skipped']} skipped")
    except Exception as e:
        print(f"❌ Error storing commands: {e}")
        return
    # 检索存储的命令
    try:
        stored_commands = processor.get_all_commands_data()
        command_types = processor.get_command_types()
        print(f"📋 Retrieved {len(stored_commands)} commands, Types: {', '.join(command_types)}")
    except Exception as e:
        print(f"❌ Error retrieving commands: {e}")
    # 最终摘要
    print(f"\n📊 RESULTS: {len(commands)} parsed, {len(matching_commands)} stored")
    if non_matching_commands:
        print(f"\n❌ NON-MATCHING COMMANDS:")
        for cmd in non_matching_commands:
            print(f"   {cmd['command_type']}: {cmd['command_full']}")
    print("\n✅ TEST COMPLETED")
if __name__ == "__main__":
    main()

