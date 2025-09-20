#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据库迁移脚本
用于为现有数据库添加缺失的列，确保所有数据库结构一致
包括HBPR表和Commands表的迁移
"""

import os
import glob
import sqlite3
from typing import List, Tuple


class DatabaseMigrator:
    """数据库迁移器，用于修复现有数据库结构"""


    def __init__(self, conn: sqlite3.Connection):
        """
        初始化迁移器
        Args:
            conn (sqlite3.Connection): 数据库连接对象
        """
        if not conn:
            raise ValueError("A valid database connection must be provided.")
        self.conn = conn
        # HBPR表需要的列
        self.hbpr_required_columns = [
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
            ('tkne', 'TEXT'),
            ('error_count', 'INTEGER'),
            ('error_baggage', 'TEXT'),
            ('error_passport', 'TEXT'),
            ('error_name', 'TEXT'),
            ('error_visa', 'TEXT'),
            ('error_other', 'TEXT'),
            ('validated_at', 'TIMESTAMP'),
            ('bol_duplicate', 'BOOLEAN DEFAULT 0')
        ]
        # Commands表需要的列
        self.commands_required_columns = [
            ('version', 'INTEGER DEFAULT 1'),
            ('parent_id', 'INTEGER'),
            ('is_latest', 'BOOLEAN DEFAULT TRUE')
        ]


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
            print("     ⚠️  commands表不存在，跳过")
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
            print("     ✅ Commands表结构完整，无需迁移")
            return True
        
        print(f"     📝  需要添加 {len(missing_columns)} 个列")
        
        # 添加缺失的列
        try:
            for column_name, column_type in missing_columns:
                cursor.execute(f"ALTER TABLE commands ADD COLUMN {column_name} {column_type}")
                print(f"       ➕ 添加列: {column_name}")
            
            # 创建必要的索引
            print("       🔧 创建索引...")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_commands_timeline ON commands(command_full, version)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_commands_parent ON commands(parent_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_commands_latest ON commands(command_full, is_latest)")
            
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


    def migrate_database(self) -> bool:
        """迁移当前连接的数据库"""
        print(f"\n🔄 正在迁移数据库...")
        
        # 迁移HBPR表
        hbpr_success = self.migrate_hbpr_table()
        
        # 迁移Commands表
        commands_success = self.migrate_commands_table()
        
        if hbpr_success and commands_success:
            print("\n🎉 数据库迁移成功！")
        else:
            print("\n⚠️  数据库迁移失败")
            
        return hbpr_success and commands_success


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
