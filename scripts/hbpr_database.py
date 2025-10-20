#!/usr/bin/env python3
"""
HBPR Database Operations
Contains HbprDatabase class for managing HBPR-related database operations.
"""

import os
import sqlite3
from .data_cleaner import clean_hbpr_record_content
import pandas as pd


class HbprDatabase:
    """数据库操作类，管理HBPR相关的所有数据库操作"""


    def __init__(self, conn: sqlite3.Connection):
        """初始化数据库连接"""
        # Initialize cache before setting db_file
        self._chbpr_fields_initialized = False  # Cache to avoid repeated field additions
        if not conn:
            raise ValueError("Database connection must be provided.")
        self.conn = conn
        # Caching is disabled for memory database, as it's fast enough
        self.stats_manager = None
        # 确保所有VIEWs存在
        self.ensure_all_views(verbose=False)


    def get_connection(self):
        """获取数据库连接"""
        return self.conn


    def build_from_hbpr_list(self, input_file: str = "sample_hbpr_list.txt"):
        """使用hbpr_list_processor从文件构建数据库"""
        print(f"=== Building database from {input_file} ===")
        if not os.path.exists(input_file):
            raise FileNotFoundError(f"Input file {input_file} not found!")
        # 创建处理器并处理文件
        # This function creates a new DB file, which is not what we want with a single memory db.
        # This should be handled at a higher level.
        # For now, this function is considered out of scope for the memory DB refactoring.
        raise NotImplementedError("build_from_hbpr_list is not supported with in-memory database.")


    def _add_chbpr_fields(self):
        """向hbpr_full_records表添加CHbpr解析的字段"""
        if self._chbpr_fields_initialized:
            return
        try:
            cursor = self.conn.cursor()
            # 检查表结构
            cursor.execute("PRAGMA table_info(hbpr_full_records)")
            existing_columns = [column[1] for column in cursor.fetchall()]
            # 定义需要添加的字段
            new_fields = [
                ('is_validated', 'BOOLEAN DEFAULT 0'),
                ('is_valid', 'BOOLEAN'),
                ('boarding_number', 'INTEGER'),
                ('pnr', 'TEXT'),
                ('name', 'TEXT'),
                ('seat', 'TEXT'),
                ('class', 'TEXT'),
                ('destination', 'TEXT'),
                ('bag_piece', 'INTEGER'),
                ('bag_weight', 'INTEGER'),
                ('bag_allowance', 'INTEGER'),
                ('ff', 'TEXT'),
                ('pspt_name', 'TEXT'),
                ('pspt_exp_date', 'TEXT'),
                ('ckin_msg', 'TEXT'),
                ('asvc_msg', 'TEXT'),
                ('expc_piece', 'INTEGER'),
                ('expc_weight', 'INTEGER'),
                ('asvc_piece', 'INTEGER'),
                ('fba_piece', 'INTEGER'),
                ('ifba_piece', 'INTEGER'),
                ('has_infant', 'BOOLEAN DEFAULT 0'),
                ('flyer_benefit', 'INTEGER'),
                ('is_ca_flyer', 'BOOLEAN'),
                ('inbound_flight', 'TEXT'),
                ('outbound_flight', 'TEXT'),
                ('properties', 'TEXT'),
                ('tkne', 'TEXT'),  # Add TKNE field
                ('error_count', 'INTEGER'),
                ('error_baggage', 'TEXT'),
                ('error_passport', 'TEXT'),
                ('error_name', 'TEXT'),
                ('error_visa', 'TEXT'),
                ('error_other', 'TEXT'),
                ('validated_at', 'TIMESTAMP'),
                ('bol_duplicate', 'BOOLEAN DEFAULT 0')
            ]
            # 添加不存在的字段
            fields_added = 0
            for field_name, field_type in new_fields:
                if field_name not in existing_columns:
                    try:
                        cursor.execute(f"ALTER TABLE hbpr_full_records ADD COLUMN {field_name} {field_type}")
                        print(f"Added field: {field_name}")
                        fields_added += 1
                    except sqlite3.Error as e:
                        print(f"Warning: Could not add field {field_name}: {e}")
            self.conn.commit()
            # Only print summary message if fields were actually added
            if fields_added > 0:
                print(f"CHbpr fields added to hbpr_full_records table ({fields_added} new fields)")
            # Mark as initialized for this instance
            self._chbpr_fields_initialized = True
        except sqlite3.Error as e:
            raise Exception(f"Database error: {e}")


    def get_hbpr_record(self, hbnb_number: int):
        """从数据库获取HBPR记录内容"""
        self._add_chbpr_fields()
        try:
            cursor = self.conn.cursor()
            cursor.execute("SELECT record_content FROM hbpr_full_records WHERE hbnb_number = ?", (hbnb_number,))
            result = cursor.fetchone()
            if result:
                return result[0]
            else:
                raise ValueError(f"No HBPR record found for HBNB {hbnb_number}")
        except sqlite3.Error as e:
            raise Exception(f"Database error: {e}")


    def update_with_chbpr_results(self, chbpr_instance):
        """使用CHbpr实例的结果更新hbpr_full_records表"""
        self._add_chbpr_fields()
        # 获取结构化数据
        data = chbpr_instance.get_structured_data()
        hbnb_number = data['hbnb_number']
        try:
            cursor = self.conn.cursor()
            # 检查记录是否存在
            cursor.execute("SELECT 1 FROM hbpr_full_records WHERE hbnb_number = ?", (hbnb_number,))
            if not cursor.fetchone():
                raise ValueError(f"HBNB {hbnb_number} not found in hbpr_full_records")
            # 更新记录
            cursor.execute('''
                UPDATE hbpr_full_records SET
                    is_validated = 1,
                    is_valid = ?,
                    boarding_number = ?,
                    pnr = ?,
                    name = ?,
                    seat = ?,


                    class = ?,
                    destination = ?,
                    bag_piece = ?,
                    bag_weight = ?,
                    bag_allowance = ?,
                    ff = ?,
                    pspt_name = ?,
                    pspt_exp_date = ?,
                    ckin_msg = ?,
                    asvc_msg = ?,
                    expc_piece = ?,
                    expc_weight = ?,
                    asvc_piece = ?,
                    fba_piece = ?,
                    ifba_piece = ?,
                    has_infant = ?,
                    flyer_benefit = ?,
                    is_ca_flyer = ?,
                    inbound_flight = ?,
                    outbound_flight = ?,
                    properties = ?,
                    tkne = ?,
                    error_count = ?,
                    error_baggage = ?,
                    error_passport = ?,
                    error_name = ?,
                    error_visa = ?,
                    error_other = ?,
                    validated_at = CURRENT_TIMESTAMP
                WHERE hbnb_number = ?
            ''', (
                chbpr_instance.is_valid(),
                data['boarding_number'],
                data['PNR'],
                data['NAME'],
                data['SEAT'],
                data['CLASS'],
                data['DESTINATION'],
                data['BAG_PIECE'],
                data['BAG_WEIGHT'],
                data['BAG_ALLOWANCE'],
                data['FF'],
                data['PSPT_NAME'],
                data['PSPT_EXP_DATE'],
                data['CKIN_MSG'],
                data['ASVC_MSG'],
                data['EXPC_PIECE'],
                data['EXPC_WEIGHT'],
                data['ASVC_PIECE'],
                data['FBA_PIECE'],
                data['IFBA_PIECE'],
                1 if data['HAS_INFANT'] else 0,
                data['FLYER_BENEFIT'],
                data['IS_CA_FLYER'],
                data['INBOUND_FLIGHT'],
                data['OUTBOUND_FLIGHT'],
                data['PROPERTIES'],
                data['TKNE'],
                data['error_count'],
                data['error_baggage'],
                data['error_passport'],
                data['error_name'],
                data['error_visa'],
                data['error_other'],
                hbnb_number
            ))
            self.conn.commit()
            print(f"Updated HBNB {hbnb_number} in hbpr_full_records table")
            return True
        except sqlite3.Error as e:
            raise Exception(f"Database error: {e}")


    def get_validation_stats(self):
        """获取验证统计信息"""
        try:
            cursor = self.conn.cursor()
            # 总记录数
            cursor.execute("SELECT COUNT(*) FROM hbpr_full_records")
            total_records = cursor.fetchone()[0]
            # 已验证记录数
            cursor.execute("SELECT COUNT(*) FROM hbpr_full_records WHERE is_validated = 1")
            validated_records = cursor.fetchone()[0]
            # 有效记录数
            cursor.execute("SELECT COUNT(*) FROM hbpr_full_records WHERE is_valid = 1")
            valid_records = cursor.fetchone()[0]
            # 无效记录数
            cursor.execute("SELECT COUNT(*) FROM hbpr_full_records WHERE is_validated = 1 AND is_valid = 0")
            invalid_records = cursor.fetchone()[0]
            return {
                'total_records': total_records,
                'validated_records': validated_records,
                'valid_records': valid_records,
                'invalid_records': invalid_records
            }
        except sqlite3.Error as e:
            raise Exception(f"Database error: {e}")


    def get_missing_hbnb_numbers(self):
        """获取缺失的HBNB号码列表（不连续的号码）"""
        try:
            cursor = self.conn.cursor()
            
            # 尝试从新VIEW查询（优先）
            try:
                cursor.execute("SELECT hbnb_number FROM vw_discontinuous_hbnb ORDER BY hbnb_number")
                missing_numbers = [row[0] for row in cursor.fetchall()]
                return missing_numbers
            except Exception as e:
                print(f"Warning: vw_discontinuous_hbnb query failed: {e}")
            
            # 尝试查询旧的missing_numbers表（向后兼容）
            try:
                cursor.execute("SELECT hbnb_number FROM missing_numbers ORDER BY hbnb_number")
                missing_numbers = [row[0] for row in cursor.fetchall()]
                return missing_numbers
            except Exception as e:
                print(f"Warning: missing_numbers table query failed: {e}")
            
            # 如果都失败，返回空列表（允许应用继续运行）
            print("Warning: Could not fetch missing HBNB numbers, returning empty list")
            return []
            
        except Exception as e:
            # 最后的防线 - 任何其他错误也返回空列表
            print(f"Warning: Unexpected error in get_missing_hbnb_numbers: {e}")
            return []


    def ensure_all_views(self, verbose: bool = True):
        """确保所有VIEWs存在（迁移旧表到VIEW）"""
        try:
            cursor = self.conn.cursor()
            # 检查并删除旧的missing_numbers表（已迁移到vw_discontinuous_hbnb）
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='missing_numbers'")
            if cursor.fetchone():
                cursor.execute("DROP TABLE IF EXISTS missing_numbers")
                self.conn.commit()
                if verbose:
                    print("🔄 迁移: 删除旧的missing_numbers表")
            
            # 使用统一的SchemaUtils方法创建所有VIEWs
            from scripts.schema_utils import SchemaUtils
            utils = SchemaUtils()
            return utils.create_all_views(self.conn, verbose=verbose)
        except Exception as e:
            print(f"Error ensuring views: {e}")
            return False


    def get_hbnb_range_info(self):
        """从VIEW获取HBNB号码范围信息"""
        # 定义默认值
        default_range = {
            'min': 0,
            'max': 0,
            'total_found': 0,
            'total_expected': 0
        }
        
        try:
            cursor = self.conn.cursor()
            # 从VIEW查询范围信息
            cursor.execute("SELECT * FROM vw_hbnb_range")
            row = cursor.fetchone()
            if row and row[0] is not None:
                return {
                    'min': row[0],
                    'max': row[1],
                    'total_found': row[2],
                    'total_expected': row[3]
                }
            else:
                # 无数据返回默认值
                return default_range
        except sqlite3.Error as e:
            # 数据库错误返回默认值而不是抛出异常
            print(f"Warning: Failed to fetch HBNB range info: {e}")
            return default_range


    def erase_splited_records(self):
        """删除hbpr_full_records表中除hbnb_number和record_content外的所有记录"""
        try:
            cursor = self.conn.cursor()
            # 获取当前记录数
            cursor.execute("SELECT COUNT(*) FROM hbpr_full_records")
            total_records = cursor.fetchone()[0]
            # 获取表的所有列名
            cursor.execute("PRAGMA table_info(hbpr_full_records)")
            columns = cursor.fetchall()
            column_names = [col[1] for col in columns]
            print(f"发现表字段: {column_names}")
            # 找出需要清除的字段（除了hbnb_number和record_content）
            fields_to_clear = [col for col in column_names if col not in ['hbnb_number', 'record_content']]
            print(f"需要清除的字段: {fields_to_clear}")
            if fields_to_clear:
                # 构建UPDATE语句，将所有其他字段设置为NULL
                set_clause = ", ".join([f"{field} = NULL" for field in fields_to_clear])
                update_sql = f"UPDATE hbpr_full_records SET {set_clause}"
                print(f"执行SQL: {update_sql}")
                cursor.execute(update_sql)
                self.conn.commit()
                print(f"已清除 {len(fields_to_clear)} 个字段的数据，保留 {total_records} 条记录")
            else:
                print("没有需要清除的字段")
            return True
        except sqlite3.Error as e:
            raise Exception(f"Database error: {e}")


    def get_flight_info(self):
        """获取当前数据库的航班信息"""
        try:
            cursor = self.conn.cursor()
            # 检查是否存在flight_info表
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='flight_info'")
            if not cursor.fetchone():
                raise ValueError("Flight info table not found.")
            cursor.execute("SELECT flight_id, flight_number, flight_date FROM flight_info LIMIT 1")
            result = cursor.fetchone()
            if result:
                return {
                    'flight_id': result[0],
                    'flight_number': result[1],
                    'flight_date': result[2]
                }
            else:
                raise ValueError("No flight info found in flight_info table.")
        except sqlite3.Error as e:
            raise Exception(f"Database error: {e}")


    def check_hbnb_exists(self, hbnb_number: int):
        """检查HBNB号码是否存在于数据库中（完整记录或简单记录）"""
        try:
            cursor = self.conn.cursor()
            # 检查完整记录
            cursor.execute("SELECT 1 FROM hbpr_full_records WHERE hbnb_number = ?", (hbnb_number,))
            full_exists = cursor.fetchone() is not None
            # 检查简单记录
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='hbpr_simple_records'")
            if cursor.fetchone():
                cursor.execute("SELECT 1 FROM hbpr_simple_records WHERE hbnb_number = ?", (hbnb_number,))
                simple_exists = cursor.fetchone() is not None
            else:
                simple_exists = False
            return {
                'exists': full_exists or simple_exists,
                'full_record': full_exists,
                'simple_record': simple_exists
            }
        except sqlite3.Error as e:
            raise Exception(f"Database error: {e}")


    def create_simple_record(self, hbnb_number: int, record_line: str):
        """创建简单HBPR记录"""
        try:
            # 清理记录内容移除问题字符
            cleaned_line = clean_hbpr_record_content(record_line, hbnb_number)
            if cleaned_line != record_line:
                print(f"⚠️  HBNB {hbnb_number} simple record cleaned before saving: {len(record_line)} -> {len(cleaned_line)} characters")
            cursor = self.conn.cursor()
            # 确保hbpr_simple_records表存在从JSON配置读取
            from scripts.schema_utils import SchemaUtils
            utils = SchemaUtils()
            create_sql = utils.generate_create_table_sql('hbpr_simple_records')
            cursor.execute(create_sql)
            # 插入简单记录
            cursor.execute(
                'INSERT OR REPLACE INTO hbpr_simple_records (hbnb_number, record_line) VALUES (?, ?)',
                (hbnb_number, cleaned_line)
            )
            self.conn.commit()
            print(f"Created simple record for HBNB {hbnb_number}")
            return True
        except sqlite3.Error as e:
            raise Exception(f"Database error: {e}")


    def create_full_record(self, hbnb_number: int, record_content: str):
        """创建完整HBPR记录"""
        try:
            # 清理记录内容，移除问题字符
            cleaned_content = clean_hbpr_record_content(record_content, hbnb_number)
            if cleaned_content != record_content:
                print(f"⚠️  HBNB {hbnb_number} record content cleaned before saving: {len(record_content)} -> {len(cleaned_content)} characters")
            cursor = self.conn.cursor()
            # 插入完整记录
            cursor.execute(
                'INSERT OR REPLACE INTO hbpr_full_records (hbnb_number, record_content) VALUES (?, ?)',
                (hbnb_number, cleaned_content)
            )
            # 如果存在简单记录，删除它
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='hbpr_simple_records'")
            if cursor.fetchone():
                cursor.execute("DELETE FROM hbpr_simple_records WHERE hbnb_number = ?", (hbnb_number,))
            self.conn.commit()
            print(f"Created full record for HBNB {hbnb_number}")
            return True
        except sqlite3.Error as e:
            raise Exception(f"Database error: {e}")


    def delete_simple_record(self, hbnb_number: int):
        """删除简单HBPR记录"""
        try:
            cursor = self.conn.cursor()
            cursor.execute("DELETE FROM hbpr_simple_records WHERE hbnb_number = ?", (hbnb_number,))
            self.conn.commit()
            # 更新missing_numbers表
            try:
                self.update_missing_numbers_table()
                print(f"Updated missing numbers table after deleting HBNB {hbnb_number}")
            except Exception as e:
                print(f"Warning: Could not update missing numbers table: {e}")
            print(f"Deleted simple record for HBNB {hbnb_number}")
            return True
        except sqlite3.Error as e:
            raise Exception(f"Database error: {e}")


    def extract_flight_info_from_hbpr(self, hbpr_content: str):
        """从HBPR内容中提取航班信息"""
        import re
        # 查找航班信息模式
        match = re.search(r'>HBPR:\s*([^*,]+)', hbpr_content)
        if match:
            flight_info = match.group(1).strip()
            # 解析航班号和日期
            if '/' in flight_info:
                parts = flight_info.split('/')
                if len(parts) >= 2:
                    flight_number = parts[0]
                    date = parts[1].split('*')[0] if '*' in parts[1] else parts[1]
                    return {
                        'flight_number': flight_number,
                        'flight_date': date,
                        'flight_info': flight_info
                    }
            return {
                'flight_number': flight_info,
                'flight_date': 'Unknown',
                'flight_info': flight_info
            }
        return None


    def validate_flight_info_match(self, hbpr_content: str):
        """验证HBPR内容中的航班信息是否与数据库匹配"""
        # 获取数据库中的航班信息
        db_flight_info = self.get_flight_info()
        if not db_flight_info:
            return {'match': False, 'reason': 'No flight info in database'}
        # 从HBPR内容中提取航班信息
        hbpr_flight_info = self.extract_flight_info_from_hbpr(hbpr_content)
        if not hbpr_flight_info:
            return {'match': False, 'reason': 'No flight info found in HBPR content'}
        # 比较航班信息
        db_flight_number = db_flight_info['flight_number']
        hbpr_flight_number = hbpr_flight_info['flight_number']
        if db_flight_number == hbpr_flight_number:
            return {
                'match': True,
                'db_flight': db_flight_info,
                'hbpr_flight': hbpr_flight_info
            }
        else:
            return {
                'match': False,
                'reason': f'Flight number mismatch: DB={db_flight_number}, HBPR={hbpr_flight_number}',
                'db_flight': db_flight_info,
                'hbpr_flight': hbpr_flight_info
            }


    def get_simple_records(self):
        """获取所有简单记录"""
        try:
            cursor = self.conn.cursor()
            # 检查是否存在hbpr_simple_records表
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='hbpr_simple_records'")
            if not cursor.fetchone():
                raise ValueError("hbpr_simple_records table not found.")
            cursor.execute("SELECT hbnb_number, record_line FROM hbpr_simple_records ORDER BY hbnb_number")
            results = cursor.fetchall()
            return [{'hbnb_number': row[0], 'record_line': row[1]} for row in results]
        except sqlite3.Error as e:
            raise Exception(f"Database error: {e}")


    def get_record_summary(self):
        """获取记录摘要信息"""
        return self._fetch_record_summary()


    def _fetch_record_summary(self):
        """Internal method to fetch record summary from database"""
        try:
            cursor = self.conn.cursor()
            # 获取完整记录数量
            cursor.execute("SELECT COUNT(*) FROM hbpr_full_records")
            full_count = cursor.fetchone()[0]
            # 获取简单记录数量
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='hbpr_simple_records'")
            if cursor.fetchone():
                cursor.execute("SELECT COUNT(*) FROM hbpr_simple_records")
                simple_count = cursor.fetchone()[0]
            else:
                simple_count = 0
            # 获取已验证记录数量
            cursor.execute("SELECT COUNT(*) FROM hbpr_full_records WHERE is_validated = 1")
            validated_count = cursor.fetchone()[0]
            # 获取已接受乘客数量（有登机号的记录）
            cursor.execute("SELECT COUNT(*) FROM hbpr_full_records WHERE boarding_number IS NOT NULL AND boarding_number > 0")
            accepted_pax_count = cursor.fetchone()[0]
            # 获取TKNE数量（检查列是否存在）
            try:
                cursor.execute("SELECT COUNT(*) FROM hbpr_full_records WHERE tkne IS NOT NULL AND tkne != ''")
                tkne_count = cursor.fetchone()[0]
            except sqlite3.OperationalError:
                # 如果tkne列不存在，返回0
                tkne_count = 0
            return {
                'full_records': full_count,
                'simple_records': simple_count,
                'validated_records': validated_count,
                'accepted_pax': accepted_pax_count,
                'tkne_count': tkne_count,
                'total_records': full_count + simple_count
            }
        except sqlite3.Error as e:
            raise Exception(f"Database error: {e}")


    def get_accepted_passengers(self, sort_by='boarding_number', limit=None):
        """获取已接受乘客列表（有登机号的记录）"""
        try:
            # 构建查询语句
            query = """
                SELECT hbnb_number, boarding_number, name, seat, class, destination,
                       bag_piece, bag_weight, ff, properties, ckin_msg, asvc_msg, error_count
                FROM hbpr_full_records
                WHERE boarding_number IS NOT NULL AND boarding_number > 0
            """
            # 添加排序
            if sort_by == 'boarding_number':
                query += " ORDER BY boarding_number"
            elif sort_by == 'hbnb_number':
                query += " ORDER BY hbnb_number"
            elif sort_by == 'name':
                query += " ORDER BY name"
            else:
                query += " ORDER BY boarding_number"
            # 添加限制
            if limit:
                query += f" LIMIT {limit}"
            df = pd.read_sql_query(query, self.conn)
            return df
        except sqlite3.Error as e:
            raise Exception(f"Database error: {e}")


    def get_accepted_passengers_count(self):
        """获取已接受乘客数量"""
        try:
            cursor = self.conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM hbpr_full_records WHERE boarding_number IS NOT NULL AND boarding_number > 0")
            count = cursor.fetchone()[0]
            return count
        except sqlite3.Error as e:
            raise Exception(f"Database error: {e}")


    def get_accepted_passengers_stats(self):
        """获取已接受乘客统计信息"""
        return self._fetch_accepted_passengers_stats()


    def _fetch_accepted_passengers_stats(self):
        """从VIEW获取已接受乘客统计信息"""
        cursor = self.conn.cursor()
        # 确保视图存在
        self.ensure_all_views()
        
        # 定义默认值
        default_stats = {
            'total_accepted': 0,
            'min_boarding': 0,
            'max_boarding': 0,
            'avg_bag_piece': 0,
            'avg_bag_weight': 0,
            'total_bag_pieces': 0,
            'total_bag_weight': 0,
            'infant_count': 0,
            'accepted_first': 0,
            'accepted_business': 0,
            'accepted_economy': 0
        }
        
        # 尝试从VIEW查询所有统计信息
        try:
            cursor.execute("SELECT * FROM vw_home_accepted_counts")
            row = cursor.fetchone()
            if row and len(row) >= 11:
                # 成功获取数据
                return {
                    'total_accepted': row[0] or 0,
                    'min_boarding': row[1] or 0,
                    'max_boarding': row[2] or 0,
                    'avg_bag_piece': row[3] or 0,
                    'avg_bag_weight': row[4] or 0,
                    'total_bag_pieces': row[5] or 0,
                    'total_bag_weight': row[6] or 0,
                    'infant_count': row[7] or 0,
                    'accepted_first': row[8] or 0,
                    'accepted_business': row[9] or 0,
                    'accepted_economy': row[10] or 0
                }
            else:
                # VIEW返回无结果或数据不完整，返回默认值
                return default_stats
        except Exception as e:
            # 捕获所有异常（包括远程连接的HTTP错误）返回默认值
            # 这样可以防止服务器500错误
            print(f"Warning: Failed to fetch accepted passengers stats: {e}")
            return default_stats


    def get_deleted_passengers_stats(self):
        """获取删除乘客统计信息"""
        return self._fetch_deleted_passengers_stats()


    def _fetch_deleted_passengers_stats(self):
        """从VIEW获取删除乘客统计数据"""
        try:
            # 确保is_deleted字段存在
            self.add_is_deleted_field_if_not_exists()
            cursor = self.conn.cursor()
            # 检查是_deleted字段
            cursor.execute("PRAGMA table_info(hbpr_full_records)")
            columns = [col[1] for col in cursor.fetchall()]
            has_is_deleted = 'is_deleted' in columns
            if has_is_deleted:
                # 从VIEW获取统计信息
                cursor.execute("SELECT * FROM vw_home_flags")
                row = cursor.fetchone()
                if row:
                    total_deleted = row[0] or 0
                    deleted_with_xres = row[1] or 0
                    deleted_without_xres = row[2] or 0
                else:
                    total_deleted = deleted_with_xres = deleted_without_xres = 0
                # 从VIEW获取登机号列表
                cursor.execute("SELECT boarding_number, is_xres FROM vw_deleted_boarding_numbers")
                boarding_data = cursor.fetchall()
                original_boarding_numbers = [row[0] for row in boarding_data if row[1] == 0]
                xres_boarding_numbers = [row[0] for row in boarding_data if row[1] == 1]
            else:
                # 使用旧方式计算
                # 计算总删除乘客数量（boarding_number = 0 且record_content中包含"DELETED"）
                cursor.execute(
                    """
                    SELECT COUNT(*)
                    FROM hbpr_full_records
                    WHERE boarding_number = 0 AND record_content LIKE '%DELETED%'
                    """
                )
                total_deleted = cursor.fetchone()[0]
                # 计算带XRES属性的删除乘客数量
                cursor.execute(
                    """
                    SELECT COUNT(*)
                    FROM hbpr_full_records
                    WHERE boarding_number = 0 AND record_content LIKE '%DELETED%' AND properties LIKE '%XRES%'
                    """
                )
                deleted_with_xres = cursor.fetchone()[0]
                # 计算不带XRES属性的删除乘客数量
                cursor.execute(
                    """
                    SELECT COUNT(*)
                    FROM hbpr_full_records
                    WHERE boarding_number = 0 AND record_content LIKE '%DELETED%' AND (properties NOT LIKE '%XRES%' OR properties IS NULL)
                    """
                )
                deleted_without_xres = cursor.fetchone()[0]
                original_boarding_numbers = []
                # 尝试提取不带XRES的删除乘客的原始登机号
                cursor.execute(
                    """
                    SELECT record_content
                    FROM hbpr_full_records
                    WHERE boarding_number = 0 AND record_content LIKE '%DELETED%' AND (properties NOT LIKE '%XRES%' OR properties IS NULL)
                    """
                )
                import re
                boarding_numbers = []
                for (content,) in cursor.fetchall():
                    match = re.search(r'\n\s+DEL\s+.*?/BN(\d+)\s', content)
                    if match:
                        boarding_numbers.append(int(match.group(1)))
                original_boarding_numbers = sorted(boarding_numbers)
                # 更新删除乘客统计：只计算能找到原始登机号的删除乘客
                deleted_without_xres = len(original_boarding_numbers)
                # 尝试提取带XRES的删除乘客的原始登机号
                cursor.execute(
                    """
                    SELECT record_content
                    FROM hbpr_full_records
                    WHERE boarding_number = 0 AND record_content LIKE '%DELETED%' AND properties LIKE '%XRES%'
                    """
                )
                xres_boarding_numbers = []
                for (content,) in cursor.fetchall():
                    match = re.search(r'\n\s+DEL\s+.*?/BN(\d+)\s', content)
                    if match:
                        xres_boarding_numbers.append(int(match.group(1)))
                xres_boarding_numbers = sorted(xres_boarding_numbers)
                # 更新删除乘客统计：只计算能找到原始登机号的删除乘客
                deleted_with_xres = len(xres_boarding_numbers)
                total_deleted = deleted_with_xres + deleted_without_xres
            return {
                'total_deleted': total_deleted,
                'deleted_with_xres': deleted_with_xres,
                'deleted_without_xres': deleted_without_xres,
                'original_boarding_numbers': original_boarding_numbers,
                'xres_boarding_numbers': xres_boarding_numbers
            }
        except Exception as e:
            # 捕获所有异常（包括远程连接的HTTP错误）返回默认值
            print(f"Warning: Failed to fetch deleted passengers stats: {e}")
            return {
                'total_deleted': 0,
                'deleted_with_xres': 0,
                'deleted_without_xres': 0,
                'original_boarding_numbers': [],
                'xres_boarding_numbers': []
            }


    def add_is_deleted_field_if_not_exists(self):
        """添加is_deleted字段到数据库（如果不存在）并更新现有记录"""
        try:
            cursor = self.conn.cursor()
            # 检查字段是否已存在
            cursor.execute("PRAGMA table_info(hbpr_full_records)")
            columns = [col[1] for col in cursor.fetchall()]
            field_exists = 'is_deleted' in columns
            if not field_exists:
                # 添加is_deleted字段(整型)
                cursor.execute("ALTER TABLE hbpr_full_records ADD COLUMN is_deleted INTEGER DEFAULT 0")
                # 获取所有删除记录
                cursor.execute(
                    """
                    SELECT hbnb_number, record_content
                    FROM hbpr_full_records
                    WHERE boarding_number = 0 AND record_content LIKE '%DELETED%'
                    """
                )
                deleted_records = cursor.fetchall()
                # 更新每条记录
                update_count = 0
                import re
                for hbnb, record_content in deleted_records:
                    # 查找原始登机号
                    # 查找DEL行
                    del_pattern = r'\n\s+DEL\s+.*?/BN(\d+)\s'
                    match = re.search(del_pattern, record_content)
                    if match:
                        original_bn = int(match.group(1))
                        cursor.execute(
                            """
                            UPDATE hbpr_full_records
                            SET is_deleted = ?
                            WHERE hbnb_number = ?
                            """, (original_bn, hbnb)
                        )
                        update_count += 1
                    # 如果找不到原始登机号，不设置is_deleted（保持为0，不计入统计）
                self.conn.commit()
                print(f"Added is_deleted field and updated {update_count} records")
            else:
                # 字段存在，检查是否需要重新填充数据
                # 检查是否有deleted记录但is_deleted为0
                cursor.execute(
                    """
                    SELECT COUNT(*) FROM hbpr_full_records
                    WHERE boarding_number = 0 AND record_content LIKE '%DELETED%'
                    """
                )
                total_deleted_records = cursor.fetchone()[0]
                cursor.execute(
                    """
                    SELECT COUNT(*) FROM hbpr_full_records
                    WHERE is_deleted > 0
                    """
                )
                processed_deleted_records = cursor.fetchone()[0]
                need_update = total_deleted_records > 0 and processed_deleted_records == 0
                if need_update:
                    print("Resetting and recalculating deleted records...")
                    # 获取需要更新的删除记录
                    cursor.execute(
                        """
                        SELECT hbnb_number, record_content
                        FROM hbpr_full_records
                        WHERE boarding_number = 0 AND record_content LIKE '%DELETED%'
                        """
                    )
                    deleted_records = cursor.fetchall()
                    # 重置所有is_deleted字段为0
                    cursor.execute("UPDATE hbpr_full_records SET is_deleted = 0")
                    # 更新每条记录
                    update_count = 0
                    import re
                    for hbnb, record_content in deleted_records:
                        # 查找原始登机号
                        del_pattern = r'\n\s+DEL\s+.*?/BN(\d+)\s'
                        match = re.search(del_pattern, record_content)
                        if match:
                            original_bn = int(match.group(1))
                            cursor.execute(
                                """
                                UPDATE hbpr_full_records
                                SET is_deleted = ?
                                WHERE hbnb_number = ?
                                """, (original_bn, hbnb)
                            )
                            update_count += 1
                        # 如果找不到原始登机号，不设置is_deleted（保持为0，不计入统计）
                    self.conn.commit()
                    print(f"Updated {update_count} existing deleted records")
            return True
        except sqlite3.Error as e:
            raise Exception(f"Database error: {e}")


    def get_missing_boarding_numbers(self):
        """
        从VIEW中获取缺失的登机号（自动排除已删除乘客）
        Returns:
            list: 缺失的登机号列表
        """
        try:
            cursor = self.conn.cursor()
            cursor.execute("SELECT boarding_number FROM vw_missing_boarding_numbers")
            missing_numbers = [row[0] for row in cursor.fetchall()]
            return missing_numbers
        except Exception as e:
            # 捕获所有异常（包括远程连接的HTTP错误）
            print(f"Warning: Error getting missing boarding numbers: {e}")
            return []


    def get_all_statistics(self):
        """Get all statistics with automatic caching and fallback"""
        stats = {}
        # Get accepted passengers stats
        stats['accepted_passengers_stats'] = self.get_accepted_passengers_stats()
        # Get HBNB range info
        stats['hbnb_range_info'] = self.get_hbnb_range_info()
        # Get missing numbers
        stats['missing_numbers'] = self.get_missing_hbnb_numbers()
        # Get deleted passengers stats
        stats['deleted_passengers_stats'] = self.get_deleted_passengers_stats()
        # Get missing boarding numbers
        stats['missing_boarding_numbers'] = self.get_missing_boarding_numbers()
        # Get duplicate seats
        stats['duplicate_seats'] = self.get_duplicate_seats()
        # Get duplicate names
        stats['duplicate_names'] = self.get_duplicate_names()
        return stats


    def get_duplicate_seats(self):
        """获取重复座位的统计数据
        Returns:
            List[Dict]: 包含座位号、乘客姓名和计数的列表
                [{'seat': '31K', 'names': 'SMITH/JOHN,DOE/JANE', 'count': 2}, ...]
        """
        try:
            cursor = self.conn.cursor()
            self.ensure_all_views(verbose=False)
            cursor.execute("SELECT seat, names, count FROM vw_duplicate_seats ORDER BY seat")
            results = []
            for row in cursor.fetchall():
                results.append({
                    'seat': row[0],
                    'names': row[1],
                    'count': row[2]
                })
            return results
        except Exception as e:
            print(f"Warning: Error getting duplicate seats: {e}")
            return []


    def get_duplicate_names(self):
        """获取重复姓名的统计数据（去除后缀后）
        Returns:
            List[Dict]: 包含姓名和计数的列表
                [{'name': 'SMITH/JOHN', 'count': 2}, ...]
        """
        try:
            cursor = self.conn.cursor()
            self.ensure_all_views(verbose=False)
            cursor.execute("SELECT cleaned_name, count FROM vw_duplicate_names ORDER BY count DESC, cleaned_name")
            results = []
            for row in cursor.fetchall():
                results.append({
                    'name': row[0],
                    'count': row[1]
                })
            return results
        except Exception as e:
            print(f"Warning: Error getting duplicate names: {e}")
            return []


    def create_duplicate_record_table(self):
        """创建duplicate_record表从JSON配置读取"""
        try:
            cursor = self.conn.cursor()
            # 创建duplicate_record表从JSON配置读取
            from scripts.schema_utils import SchemaUtils
            utils = SchemaUtils()
            create_sql = utils.generate_create_table_sql('duplicate_record')
            cursor.execute(create_sql)
            self.conn.commit()
            print("Created duplicate_record table")
        except sqlite3.Error as e:
            raise Exception(f"Database error: {e}")


    def create_duplicate_record(self, hbnb_number: int, original_hbnb_id: int, record_content: str):
        """创建重复记录"""
        try:
            # 确保duplicate_record表存在
            self.create_duplicate_record_table()
            cursor = self.conn.cursor()
            # 插入重复记录
            cursor.execute(
                'INSERT INTO duplicate_record (hbnb_number, original_hbnb_id, record_content) VALUES (?, ?, ?)',
                (hbnb_number, original_hbnb_id, record_content)
            )
            # 更新原始记录的bol_duplicate标志
            cursor.execute(
                'UPDATE hbpr_full_records SET bol_duplicate = 1 WHERE hbnb_number = ?',
                (original_hbnb_id,)
            )
            self.conn.commit()
            print(f"Created duplicate record for HBNB {hbnb_number} (original: {original_hbnb_id})")
            return True
        except sqlite3.Error as e:
            raise Exception(f"Database error: {e}")


    def create_duplicate_record_with_time(self, hbnb_number: int, original_hbnb_id: int, record_content: str, created_at: str):
        """创建重复记录并指定创建时间"""
        try:
            # 确保duplicate_record表存在
            self.create_duplicate_record_table()
            cursor = self.conn.cursor()
            # 插入重复记录并指定创建时间
            cursor.execute(
                'INSERT INTO duplicate_record (hbnb_number, original_hbnb_id, record_content, created_at) VALUES (?, ?, ?, ?)',
                (hbnb_number, original_hbnb_id, record_content, created_at)
            )
            # 更新原始记录的bol_duplicate标志
            cursor.execute(
                'UPDATE hbpr_full_records SET bol_duplicate = 1 WHERE hbnb_number = ?',
                (original_hbnb_id,)
            )
            self.conn.commit()
            print(f"Created duplicate record for HBNB {hbnb_number} (original: {original_hbnb_id}) with original timestamp")
            return True
        except sqlite3.Error as e:
            raise Exception(f"Database error: {e}")


    def get_original_record_info(self, hbnb_number: int):
        """获取原始记录的内容和创建时间"""
        try:
            cursor = self.conn.cursor()
            cursor.execute(
                "SELECT record_content, created_at FROM hbpr_full_records WHERE hbnb_number = ?",
                (hbnb_number,)
            )
            result = cursor.fetchone()
            if result:
                return {
                    'record_content': result[0],
                    'created_at': result[1]
                }
            else:
                raise ValueError(f"No original record found for HBNB {hbnb_number}")
        except sqlite3.Error as e:
            raise Exception(f"Database error: {e}")


    def auto_backup_before_replace(self, hbnb_number: int):
        """在替换记录前自动备份原始记录"""
        try:
            # 获取原始记录信息
            original_info = self.get_original_record_info(hbnb_number)
            if original_info:
                # 创建备份记录，保持原始创建时间
                self.create_duplicate_record_with_time(
                    hbnb_number,
                    hbnb_number,
                    original_info['record_content'],
                    original_info['created_at']
                )
                return True
            else:
                raise ValueError(f"Original record not found for HBNB {hbnb_number} to backup.")
        except Exception as e:
            raise Exception(f"Auto backup failed: {e}")


    def get_duplicate_records(self, original_hbnb_id: int):
        """获取指定HBNB的所有重复记录"""
        try:
            cursor = self.conn.cursor()
            # 检查duplicate_record表是否存在
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='duplicate_record'")
            if not cursor.fetchone():
                raise ValueError("duplicate_record table not found.")
            # 获取重复记录
            cursor.execute(
                'SELECT id, hbnb_number, record_content, created_at FROM duplicate_record WHERE original_hbnb_id = ? ORDER BY created_at',
                (original_hbnb_id,)
            )
            results = cursor.fetchall()
            return [{'id': row[0], 'hbnb_number': row[1], 'record_content': row[2], 'created_at': row[3]} for row in results]
        except sqlite3.Error as e:
            raise Exception(f"Database error: {e}")


    def get_all_duplicate_hbnbs(self):
        """获取所有有重复记录的HBNB号码"""
        try:
            cursor = self.conn.cursor()
            # 检查duplicate_record表是否存在
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='duplicate_record'")
            if not cursor.fetchone():
                raise ValueError("duplicate_record table not found.")
            # 获取所有有重复记录的HBNB号码
            cursor.execute(
                'SELECT DISTINCT original_hbnb_id FROM duplicate_record ORDER BY original_hbnb_id'
            )
            results = cursor.fetchall()
            return [row[0] for row in results]
        except sqlite3.Error as e:
            raise Exception(f"Database error: {e}")


    def get_duplicate_record_content(self, duplicate_id: int):
        """根据duplicate record ID获取记录内容"""
        try:
            cursor = self.conn.cursor()
            cursor.execute(
                'SELECT record_content FROM duplicate_record WHERE id = ?',
                (duplicate_id,)
            )
            result = cursor.fetchone()
            if result:
                return result[0]
            else:
                raise ValueError(f"No duplicate record found with ID {duplicate_id}")
        except sqlite3.Error as e:
            raise Exception(f"Database error: {e}")


    def get_combined_records_for_display(self):
        """获取用于显示的组合记录（包括原始记录和重复记录）"""
        try:
            cursor = self.conn.cursor()
            records = []
            # 获取所有完整记录
            cursor.execute(
                'SELECT hbnb_number, record_content, created_at, bol_duplicate FROM hbpr_full_records ORDER BY hbnb_number'
            )
            full_records = cursor.fetchall()
            for record in full_records:
                hbnb_number, content, created_at, bol_duplicate = record
                records.append({
                    'type': 'original',
                    'hbnb_number': hbnb_number,
                    'record_content': content,
                    'created_at': created_at,
                    'has_duplicates': bool(bol_duplicate),
                    'duplicate_id': None
                })
                # 如果有重复记录，也添加进来
                if bol_duplicate:
                    duplicates = self.get_duplicate_records(hbnb_number)
                    for dup in duplicates:
                        records.append({
                            'type': 'duplicate',
                            'hbnb_number': dup['hbnb_number'],
                            'record_content': dup['record_content'],
                            'created_at': dup['created_at'],
                            'has_duplicates': False,
                            'duplicate_id': dup['id'],
                            'original_hbnb': hbnb_number
                        })
            return records
        except sqlite3.Error as e:
            raise Exception(f"Database error: {e}")


    def get_tkne_count(self):
        """获取TKNE数量（有TKNE字段的记录数）"""
        try:
            cursor = self.conn.cursor()
            try:
                cursor.execute("SELECT COUNT(*) FROM hbpr_full_records WHERE tkne IS NOT NULL AND tkne != ''")
                count = cursor.fetchone()[0]
            except sqlite3.OperationalError:
                # 如果tkne列不存在，返回0
                count = 0
            return count
        except sqlite3.Error as e:
            raise Exception(f"Database error: {e}")

