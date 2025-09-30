#!/usr/bin/env python3
"""
HBPR Data Processor
Processes HBPR records from text file, extracts HBNB numbers, 
finds missing numbers, and stores data in flight-specific SQLite databases.
"""

import re
import sqlite3
from collections import defaultdict
from .data_cleaner import clean_hbpr_record_content


class HBPRProcessor:
    """HBPR数据处理器"""


    def __init__(self, conn: sqlite3.Connection):
        """
        初始化HBPR处理器
        Args:
            conn: 数据库连接对象
        """
        if not conn:
            raise ValueError("A valid database connection must be provided.")
        self.conn = conn
        # flight_data[flight_id] 航班数据，包括HBNB号码、完整记录和简单记录
        # 使用defaultdict，如果flight_id不存在，则创建一个默认值为{hbnb_numbers: set(), full_records: {}, simple_records: {}}的航班数据
        self.flight_data = defaultdict(lambda: {
            'hbnb_numbers': set(),
            'full_records': {}, # 完整记录：HBNB -> 记录内容
            'simple_records': {} # 简单记录：HBNB -> 记录内容
        })  # flight_id -> flight data
        self.flight_info = {}  # flight_id -> (flight_number, date)
        self.flight_id = "" # 当前处理的航班ID。整个文件只会有一个航班ID。
        self.all_simple_records = {}  # 全局简单记录：HBNB -> 记录内容


    def parse_file_content(self, file_content: str) -> None:
        """解析HBPR文本内容并按航班提取所有记录"""
        print("Parsing file content...")
        
        lines = file_content.splitlines()
        
        # 逐行解析处理
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            # 检查完整HBPR记录
            if line.startswith('>HBPR:') or line.startswith('HBPR:'):
                hbnb_num, record_content, next_index = self.parse_full_record(lines, i)
                if hbnb_num:
                    self.flight_data[self.flight_id]['hbnb_numbers'].add(hbnb_num)
                    # 合并同一HBNB记录的多个部分
                    if hbnb_num in self.flight_data[self.flight_id]['full_records']:
                        self.flight_data[self.flight_id]['full_records'][hbnb_num] += "\n" + record_content
                    else:
                        self.flight_data[self.flight_id]['full_records'][hbnb_num] = record_content
                i = next_index
            # 检查简单hbpr记录
            elif line.lower().startswith('hbpr'):
                hbnb_num = self._parse_simple_record(line)
                if hbnb_num:
                    # 存储到全局简单记录中，稍后分配到合适的航班
                    self.all_simple_records[hbnb_num] = line
                i += 1
            else:
                i += 1
        # 将简单记录分配到合适的航班
        self._assign_simple_records()
        # 输出解析统计
        print(f"Found {len(self.flight_data)} flights")
        #for flight_id, data in self.flight_data.items():
        #    print(f"Flight {flight_id}: {len(data['hbnb_numbers'])} HBNB numbers, "
        #          f"{len(data['full_records'])} full records, {len(data['simple_records'])} simple records")


    def _assign_simple_records(self) -> None:
        """将简单记录分配到航班（简化版本：整个文件只有一个航班）"""
        # 如果有航班ID，将所有简单记录分配给该航班
        if self.flight_id and self.flight_id in self.flight_data:
            flight_data = self.flight_data[self.flight_id]
            for hbnb_num, record_line in self.all_simple_records.items():
                flight_data['hbnb_numbers'].add(hbnb_num)
                flight_data['simple_records'][hbnb_num] = record_line
        # 如果没有航班ID，说明文件中没有完整记录，创建UNKNOWN_FLIGHT
        elif self.all_simple_records:
            self.flight_id = "UNKNOWN_FLIGHT"
            self.flight_info[self.flight_id] = ("UNKNOWN", "UNKNOWN")
            flight_data = self.flight_data[self.flight_id]
            for hbnb_num, record_line in self.all_simple_records.items():
                flight_data['hbnb_numbers'].add(hbnb_num)
                flight_data['simple_records'][hbnb_num] = record_line


    def parse_full_record(self, lines: list[str], start_index: int) -> tuple[int | None, str, int]:
        """
        解析完整HBPR记录并提取航班信息和HBNB号码
        如果解析成功，则设置self.flight_id 
        Args:
            lines: 输入的HBPR文本文件内容
            start_index: 开始解析的行索引
        Returns:
            hbnb_num: HBNB号码
            record_content: 记录内容
            i: 结束解析的行索引
        UI的手工输入将调用这个函数，所以要公开。
        """
        line = lines[start_index].strip()
        # 提取航班信息和HBNB号码
        # 格式: >HBPR: CA984/25JUL25*LAX,{NUMBER}
        match = re.search(r'>HBPR:\s*([^*,]+)', line)
        if not match:
            return None, "", start_index + 1
        flight_info = match.group(1).strip()
        # 提取HBNB号码 - 允许逗号后有空格和其他文本
        hbnb_match = re.search(r'>HBPR:\s*[^,]+,(\d+)', line)
        if not hbnb_match:
            return None, "", start_index + 1
        hbnb_num = int(hbnb_match.group(1))
        # 解析航班号和日期
        if not self.flight_id:
            self.flight_id = self._parse_flight_info(flight_info)
        # 收集记录内容直到下一个>标记
        record_lines = []
        i = start_index
        while i < len(lines):
            current_line = lines[i].rstrip()
            record_lines.append(current_line)
            i += 1
            # 检查下一行是否开始新记录
            if i < len(lines) and lines[i].strip().startswith('>'):
                break
        record_content = '\n'.join(record_lines)
        
        # 清理记录内容，移除问题字符
        cleaned_content = clean_hbpr_record_content(record_content, hbnb_num)
        if cleaned_content != record_content:
            print(f"⚠️  HBNB {hbnb_num} record content cleaned: {len(record_content)} -> {len(cleaned_content)} characters")
        
        return hbnb_num, cleaned_content, i


    def _parse_flight_info(self, flight_info: str) -> str:
        """解析航班信息并生成航班ID"""
        # 格式: CA984/25JUL25 -> CA984_25JUL25
        flight_parts = flight_info.replace('/', '_').replace('*', '_')
        # 提取航班号和日期
        if '/' in flight_info:
            parts = flight_info.split('/')
            if len(parts) >= 2:
                flight_number = parts[0]
                date = parts[1].split('*')[0] if '*' in parts[1] else parts[1]
                self.flight_info[flight_parts] = (flight_number, date)
            else:
                self.flight_info[flight_parts] = (flight_info, "UNKNOWN")
        else:
            self.flight_info[flight_parts] = (flight_info, "UNKNOWN")
        return flight_parts


    def _parse_simple_record(self, line: str) -> int | None:
        """解析简单hbpr记录提取HBNB号码"""
        # 格式: hbpr *,{NUMBER} 或 HBPR *,{NUMBER}
        match = re.search(r'hbpr\s*[^,]*,(\d+)', line, re.IGNORECASE)
        if match:
            return int(match.group(1))
        return None


    def find_missing_numbers(self, flight_id: str) -> list[int]:
        """查找指定航班的缺失HBNB号码（真正不存在的号码）"""
        hbnb_numbers = self.flight_data[flight_id]['hbnb_numbers']
        if not hbnb_numbers:
            return []
        # 计算缺失号码
        min_num = min(hbnb_numbers)
        max_num = max(hbnb_numbers)
        all_numbers = set(range(min_num, max_num + 1))
        missing = sorted(all_numbers - hbnb_numbers)
        #print(f"Flight {flight_id} HBNB range: {min_num} to {max_num}")
        #print(f"Missing {len(missing)} numbers: {missing}")
        return missing


    def create_tables_if_not_exist(self) -> None:
        """为指定航班创建SQLite数据库表（如果不存在）"""
        cursor = self.conn.cursor()
        # 创建航班信息表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS flight_info (
                flight_id TEXT PRIMARY KEY,
                flight_number TEXT NOT NULL,
                flight_date TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        # 创建完整记录表 - 包含所有必要的列
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS hbpr_full_records (
                hbnb_number INTEGER PRIMARY KEY,
                record_content TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_validated BOOLEAN DEFAULT 0,
                is_valid BOOLEAN,
                boarding_number INTEGER,
                pnr TEXT,
                name TEXT,
                seat TEXT,
                class TEXT,
                destination TEXT,
                bag_piece INTEGER,
                bag_weight INTEGER,
                bag_allowance INTEGER,
                ff TEXT,
                pspt_name TEXT,
                pspt_exp_date TEXT,
                ckin_msg TEXT,
                asvc_msg TEXT,
                expc_piece INTEGER,
                expc_weight INTEGER,
                asvc_piece INTEGER,
                fba_piece INTEGER,
                ifba_piece INTEGER,
                has_infant BOOLEAN DEFAULT 0,
                flyer_benefit INTEGER,
                is_ca_flyer BOOLEAN,
                inbound_flight TEXT,
                outbound_flight TEXT,
                properties TEXT,
                tkne TEXT,
                error_count INTEGER,
                error_baggage TEXT,
                error_passport TEXT,
                error_name TEXT,
                error_visa TEXT,
                error_other TEXT,
                validated_at TIMESTAMP,
                bol_duplicate BOOLEAN DEFAULT 0
            )
        ''')
        # 创建简单记录表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS hbpr_simple_records (
                hbnb_number INTEGER PRIMARY KEY,
                record_line TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        # 创建缺失号码表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS missing_numbers (
                hbnb_number INTEGER PRIMARY KEY,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        self.conn.commit()
        print("Database tables ensured to exist.")


    def store_records(self, flight_id: str) -> None:
        """将指定航班的记录存储到数据库"""
        cursor = self.conn.cursor()
        flight_data = self.flight_data[flight_id]
        # 存储航班信息
        flight_number, flight_date = self.flight_info[flight_id]
        cursor.execute(
            'INSERT INTO flight_info (flight_id, flight_number, flight_date) VALUES (?, ?, ?)',
            (flight_id, flight_number, flight_date)
        )
        # 存储完整记录（清理重复标题）
        for hbnb_num, content in flight_data['full_records'].items():
            cleaned_content = self._clean_duplicate_headers(content)
            # 进一步清理内容，移除问题字符
            final_content = clean_hbpr_record_content(cleaned_content, hbnb_num)
            cursor.execute(
                'INSERT INTO hbpr_full_records (hbnb_number, record_content) VALUES (?, ?)',
                (hbnb_num, final_content)
            )
        # 存储简单记录
        for hbnb_num, line in flight_data['simple_records'].items():
            # 清理简单记录内容
            cleaned_line = clean_hbpr_record_content(line, hbnb_num)
            cursor.execute(
                'INSERT INTO hbpr_simple_records (hbnb_number, record_line) VALUES (?, ?)',
                (hbnb_num, cleaned_line)
            )
        # 存储缺失号码
        missing_numbers = self.find_missing_numbers(flight_id)
        for num in missing_numbers:
            cursor.execute(
                'INSERT INTO missing_numbers (hbnb_number) VALUES (?)',
                (num,)
            )
        self.conn.commit()
        # 输出存储统计
        #print(f"Stored {len(flight_data['full_records'])} full records")
        #print(f"Stored {len(flight_data['simple_records'])} simple records")
        #print(f"Stored {len(missing_numbers)} missing number entries")


    def _clean_duplicate_headers(self, content: str) -> str:
        """清理记录内容中的重复>HBPR:标题和分页标记"""
        lines = content.split('\n')
        cleaned_lines = []
        header_seen = False
        # 遍历所有行，过滤重复标题和分页标记
        for line in lines:
            if line.strip().startswith('>HBPR:'):
                if not header_seen:
                    cleaned_lines.append(line)
                    header_seen = True
                # 跳过重复标题
            else:
                # 删除行末的分页标记"+"（通常在index79位置）
                cleaned_line = line.rstrip('+')
                cleaned_lines.append(cleaned_line)
        return '\n'.join(cleaned_lines)


    def generate_report(self, flight_id: str) -> None:
        """生成指定航班的处理报告"""
        missing_numbers = self.find_missing_numbers(flight_id)
        flight_data = self.flight_data[flight_id]
        flight_number, flight_date = self.flight_info[flight_id]
        # 打印详细报告
        print("\n" + "="*60)
        print(f"FLIGHT {flight_id} PROCESSING REPORT")
        print("="*60)
        print(f"Flight Number: {flight_number}")
        print(f"Flight Date: {flight_date}")
        print(f"Database file: {flight_id}.db")
        print(f"Total unique HBNB numbers: {len(flight_data['hbnb_numbers'])}")
        print(f"Full records: {len(flight_data['full_records'])}")
        print(f"Simple records: {len(flight_data['simple_records'])}")
        # 显示HBNB号码范围
        if flight_data['hbnb_numbers']:
            print(f"HBNB number range: {min(flight_data['hbnb_numbers'])} to {max(flight_data['hbnb_numbers'])}")
        # 显示缺失号码信息
        print(f"Missing numbers: {len(missing_numbers)}")
        if missing_numbers:
            if len(missing_numbers) <= 50:
                print(f"Missing HBNB numbers: {missing_numbers}")
            else:
                print(f"First 50 missing HBNB numbers: {missing_numbers[:50]}")
                print(f"... and {len(missing_numbers) - 50} more")
        print("="*60)


    def process(self, file_content: str) -> None:
        """执行完整的数据处理流水线"""
        # 解析文件内容
        self.parse_file_content(file_content)
        # 为每个航班处理数据
        for flight_id in self.flight_data.keys():
            print(f"\nProcessing flight: {flight_id}")
            # 确保表存在
            self.create_tables_if_not_exist()
            # 存储记录到数据库
            self.store_records(flight_id)
            # 生成处理报告
            self.generate_report(flight_id)


def parse_flight_id_from_content(file_content: str) -> str | None:
    """Parses file content to find the flight ID without full processing."""
    lines = file_content.splitlines()
    for line in lines:
        line = line.strip()
        if line.startswith('>HBPR:') or line.startswith('HBPR:'):
            match = re.search(r'>HBPR:\s*([^*,]+)', line)
            if match:
                flight_info = match.group(1).strip()
                flight_parts = flight_info.replace('/', '_').replace('*', '_')
                return flight_parts
    return None


def main():
    """主函数 - 现在作为一个示例，展示如何使用HBPR处理器"""
    print("🧹 HBPR List Processor Tool")
    print("=" * 50)
    print("该脚本现在应该作为模块导入，而不是直接运行。")
    print("用法示例:")
    print("  from scripts.hbpr_list_processor import HBPRProcessor")
    print("  from ui.common import get_hbpr_database_client # Assuming UI is running")
    print("  db_client = get_hbpr_database_client()")
    print("  if db_client:")
    print("      conn = db_client.get_connection()")
    print("      processor = HBPRProcessor(conn)")
    print("      with open('sample_hbpr_list.txt', 'r') as f:")
    print("          content = f.read()")
    print("      processor.process(content)")


if __name__ == "__main__":
    main() 

