#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据库迁移脚本
用于为现有数据库添加缺失的列确保所有数据库结构一致
包括HBPR表和Commands表的迁移
从集中的JSON配置文件读取数据库结构
"""

import os
import json
import sqlite3
from typing import List, Tuple, Dict, Any
from pathlib import Path


class DatabaseMigrator:
    """数据库迁移器用于修复现有数据库结构"""


    def __init__(self, conn: sqlite3.Connection, schema_file: str = None):
        """
        初始化迁移器
        Args:
            conn (sqlite3.Connection): 数据库连接对象
            schema_file (str): JSON配置文件路径如果为None则使用默认路径
        """
        if not conn:
            raise ValueError("A valid database connection must be provided.")
        self.conn = conn
        # 加载数据库结构配置
        if schema_file is None:
            # 默认使用scripts/database_schema.json
            schema_file = Path(__file__).parent / 'database_schema.json'
        self.schema = self._load_schema(schema_file)
        # 从JSON配置中提取必需的列用于迁移
        self.hbpr_required_columns = self._extract_columns('hbpr_full_records')
        self.commands_required_columns = self._extract_columns('commands')
        self.commands_indexes = self._extract_indexes('commands')


    def _load_schema(self, schema_file: str) -> Dict[str, Any]:
        """
        从JSON文件加载数据库结构配置
        Args:
            schema_file (str): JSON文件路径
        Returns:
            Dict[str, Any]: 数据库结构配置
        """
        try:
            with open(schema_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            raise Exception(f"Failed to load schema file {schema_file}: {e}")


    def _extract_columns(self, table_name: str) -> List[Tuple[str, str]]:
        """
        从JSON配置中提取表的列定义
        Args:
            table_name (str): 表名
        Returns:
            List[Tuple[str, str]]: [(列名, 列类型+约束), ...]
        """
        if table_name not in self.schema['tables']:
            return []
        # 提取除PRIMARY KEY列之外的所有列用于迁移检查
        columns = []
        for col in self.schema['tables'][table_name]['columns']:
            # 跳过主键列因为它们在建表时已经存在
            if 'PRIMARY KEY' in col['constraint']:
                continue
            col_def = f"{col['type']} {col['constraint']}".strip()
            columns.append((col['name'], col_def))
        return columns


    def _extract_indexes(self, table_name: str) -> List[Dict[str, Any]]:
        """
        从JSON配置中提取表的索引定义
        Args:
            table_name (str): 表名
        Returns:
            List[Dict[str, Any]]: 索引定义列表
        """
        if table_name not in self.schema['tables']:
            return []
        return self.schema['tables'][table_name].get('indexes', [])


    def migrate_hbpr_table(self) -> bool:
        """迁移HBPR表"""
        print("   🔄 迁移HBPR表...")
        
        # 检查表是否存在
        cursor = self.conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='hbpr_full_records'")
        if not cursor.fetchone():
            print("     ⚠️  hbpr_full_records表不存在，跳过")
            return True
        
        # 获取现有列
        cursor.execute("PRAGMA table_info(hbpr_full_records)")
        existing_columns = [column[1] for column in cursor.fetchall()]
        
        # 检查需要添加的列
        missing_columns = []
        for column_name, column_type in self.hbpr_required_columns:
            if column_name not in existing_columns:
                missing_columns.append((column_name, column_type))
        
        if not missing_columns:
            print("     ✅ HBPR表结构完整，无需迁移")
            return True
        
        print(f"     📝  需要添加 {len(missing_columns)} 个列")
        
        # 添加缺失的列
        try:
            for column_name, column_type in missing_columns:
                cursor.execute(f"ALTER TABLE hbpr_full_records ADD COLUMN {column_name} {column_type}")
                print(f"       ➕ 添加列: {column_name}")
            
            self.conn.commit()
            print("     ✅ HBPR表迁移成功")
            return True
            
        except sqlite3.Error as e:
            print(f"     ❌ HBPR表迁移失败: {e}")
            self.conn.rollback()
            return False


    def migrate_commands_table(self) -> bool:
        """迁移Commands表"""
        print("   🔄 迁移Commands表...")
        # 检查表是否存在
        cursor = self.conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='commands'")
        if not cursor.fetchone():
            print("     ⚠️  commands表不存在跳过")
            return True
        # 获取现有列
        cursor.execute("PRAGMA table_info(commands)")
        existing_columns = [column[1] for column in cursor.fetchall()]
        # 检查需要添加的列
        missing_columns = []
        for column_name, column_type in self.commands_required_columns:
            if column_name not in existing_columns:
                missing_columns.append((column_name, column_type))
        if not missing_columns:
            print("     ✅ Commands表结构完整无需迁移")
            # 即使列完整也确保索引存在
            self._create_commands_indexes(cursor)
            return True
        print(f"     📝  需要添加 {len(missing_columns)} 个列")
        # 添加缺失的列
        try:
            for column_name, column_type in missing_columns:
                cursor.execute(f"ALTER TABLE commands ADD COLUMN {column_name} {column_type}")
                print(f"       ➕ 添加列: {column_name}")
            # 创建必要的索引
            self._create_commands_indexes(cursor)
            # 更新现有记录的默认值
            print("       🔄 更新现有记录...")
            cursor.execute("UPDATE commands SET version = 1 WHERE version IS NULL")
            cursor.execute("UPDATE commands SET is_latest = TRUE WHERE is_latest IS NULL")
            self.conn.commit()
            print("     ✅ Commands表迁移成功")
            return True
        except sqlite3.Error as e:
            print(f"     ❌ Commands表迁移失败: {e}")
            self.conn.rollback()
            return False


    def _create_commands_indexes(self, cursor: sqlite3.Cursor):
        """创建Commands表的索引从JSON配置读取"""
        print("       🔧 创建索引...")
        for index in self.commands_indexes:
            index_name = index['name']
            columns = ', '.join(index['columns'])
            cursor.execute(f"CREATE INDEX IF NOT EXISTS {index_name} ON commands({columns})")
            print(f"         📌 索引: {index_name}")


    def migrate_database(self, silent: bool = False) -> Dict[str, Any]:
        """
        迁移当前连接的数据库
        Args:
            silent (bool): 是否静默模式不打印输出
        Returns:
            Dict[str, Any]: 迁移结果包含各表迁移状态
        """
        if not silent:
            print(f"\n🔄 正在迁移数据库...")
        # 迁移HBPR表
        hbpr_success = self.migrate_hbpr_table()
        # 迁移Commands表
        commands_success = self.migrate_commands_table()
        # 迁移其他表只添加缺失的列
        missing_numbers_success = self._ensure_table_exists('missing_numbers')
        duplicate_record_success = self._ensure_table_exists('duplicate_record')
        hbpr_simple_success = self._ensure_table_exists('hbpr_simple_records')
        flight_info_success = self._ensure_table_exists('flight_info')
        # 总体成功状态
        success = all([
            hbpr_success, 
            commands_success,
            missing_numbers_success,
            duplicate_record_success,
            hbpr_simple_success,
            flight_info_success
        ])
        if not silent:
            if success:
                print("\n🎉 数据库迁移成功！")
            else:
                print("\n⚠️  部分表迁移失败")
        result = {
            'success': success,
            'hbpr_full_records': hbpr_success,
            'commands': commands_success,
            'missing_numbers': missing_numbers_success,
            'duplicate_record': duplicate_record_success,
            'hbpr_simple_records': hbpr_simple_success,
            'flight_info': flight_info_success,
            'message': '迁移成功' if success else '部分迁移失败'
        }
        return result


    def _ensure_table_exists(self, table_name: str) -> bool:
        """
        确保表存在如果不存在则创建
        Args:
            table_name (str): 表名
        Returns:
            bool: True表示成功False表示失败
        """
        try:
            cursor = self.conn.cursor()
            # 检查表是否存在
            cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table_name}'")
            if cursor.fetchone():
                # 表已存在检查列
                return self._migrate_table_columns(table_name)
            else:
                # 表不存在创建它
                from scripts.schema_utils import SchemaUtils
                utils = SchemaUtils()
                create_sql = utils.generate_create_table_sql(table_name)
                cursor.execute(create_sql)
                self.conn.commit()
                print(f"   ✅ 创建表: {table_name}")
                return True
        except Exception as e:
            print(f"   ❌ 处理表 {table_name} 失败: {e}")
            return False


    def _migrate_table_columns(self, table_name: str) -> bool:
        """
        迁移表的列添加缺失的列
        Args:
            table_name (str): 表名
        Returns:
            bool: True表示成功False表示失败
        """
        try:
            cursor = self.conn.cursor()
            # 获取现有列
            cursor.execute(f"PRAGMA table_info({table_name})")
            existing_columns = [column[1] for column in cursor.fetchall()]
            # 从JSON获取应该存在的列
            required_columns = self._extract_columns(table_name)
            # 检查缺失的列
            missing_columns = []
            for column_name, column_type in required_columns:
                if column_name not in existing_columns:
                    missing_columns.append((column_name, column_type))
            if not missing_columns:
                return True
            # 添加缺失的列
            for column_name, column_type in missing_columns:
                cursor.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type}")
                print(f"       ➕ 添加列: {table_name}.{column_name}")
            self.conn.commit()
            return True
        except Exception as e:
            print(f"   ❌ 迁移表 {table_name} 的列失败: {e}")
            self.conn.rollback()
            return False


    def get_schema_version(self) -> str:
        """获取数据库结构版本号"""
        return self.schema.get('version', 'unknown')


    def verify_migration(self) -> bool:
        """验证迁移结果"""
        print(f"\n🔍 验证数据库...")
        
        all_valid = True
        
        try:
            cursor = self.conn.cursor()
            
            # 验证HBPR表
            cursor.execute("PRAGMA table_info(hbpr_full_records)")
            columns = cursor.fetchall()
            if columns:
                existing_column_names = [col[1] for col in columns]
                required_column_names = [col[0] for col in self.hbpr_required_columns]
                missing_columns = set(required_column_names) - set(existing_column_names)
                
                if missing_columns:
                    print(f"   ❌ HBPR表缺少列: {list(missing_columns)}")
                    all_valid = False
                else:
                    print("   ✅ HBPR表所有必需列都存在")
            
            # 验证Commands表
            cursor.execute("PRAGMA table_info(commands)")
            columns = cursor.fetchall()
            if columns:
                existing_column_names = [col[1] for col in columns]
                required_column_names = [col[0] for col in self.commands_required_columns]
                missing_columns = set(required_column_names) - set(existing_column_names)
                
                if missing_columns:
                    print(f"   ❌ Commands表缺少列: {list(missing_columns)}")
                    all_valid = False
                else:
                    print("   ✅ Commands表所有必需列都存在")
            
        except sqlite3.Error as e:
            print(f"   ❌ 验证时发生数据库错误: {e}")
            all_valid = False
            
        return all_valid


def main():
    """主函数 - 示例"""
    print("🚀 数据库迁移脚本 (内存模式)")
    print("=" * 50)
    print("该脚本现在应该作为模块导入，而不是直接运行。")
    print("用法示例:")
    print("  from scripts.database_migration import DatabaseMigrator")
    print("  from ui.common import get_hbpr_database_client # Assuming UI is running")
    print("")
    print("  db_client = get_hbpr_database_client()")
    print("  if db_client:")
    print("      conn = db_client.get_connection()")
    print("      migrator = DatabaseMigrator(conn)")
    print("      migrator.migrate_database()")
    print("      migrator.verify_migration()")


if __name__ == "__main__":
    main()
