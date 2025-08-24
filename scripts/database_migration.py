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


    def __init__(self):
        """初始化迁移器"""
        self.databases_folder = "databases"
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


    def find_databases(self) -> List[str]:
        """查找所有需要迁移的数据库文件"""
        if not os.path.exists(self.databases_folder):
            print(f"⚠️  {self.databases_folder} 文件夹不存在")
            return []
        
        db_files = glob.glob(os.path.join(self.databases_folder, "*.db"))
        print(f"📁 找到 {len(db_files)} 个数据库文件")
        return db_files


    def get_table_structure(self, db_file: str, table_name: str) -> List[Tuple]:
        """获取指定表的结构信息"""
        try:
            conn = sqlite3.connect(db_file)
            cursor = conn.cursor()
            cursor.execute(f"PRAGMA table_info({table_name})")
            columns = cursor.fetchall()
            conn.close()
            return columns
        except sqlite3.Error as e:
            print(f"❌ 无法读取 {db_file} 的表结构: {e}")
            return []


    def migrate_hbpr_table(self, db_file: str) -> bool:
        """迁移HBPR表"""
        print(f"   🔄 迁移HBPR表...")
        
        # 检查表是否存在
        conn = sqlite3.connect(db_file)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='hbpr_full_records'")
        if not cursor.fetchone():
            print(f"     ⚠️  hbpr_full_records表不存在，跳过")
            conn.close()
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
            print(f"     ✅ HBPR表结构完整，无需迁移")
            conn.close()
            return True
        
        print(f"     📝  需要添加 {len(missing_columns)} 个列")
        
        # 添加缺失的列
        try:
            for column_name, column_type in missing_columns:
                cursor.execute(f"ALTER TABLE hbpr_full_records ADD COLUMN {column_name} {column_type}")
                print(f"       ➕ 添加列: {column_name}")
            
            conn.commit()
            print(f"     ✅ HBPR表迁移成功")
            return True
            
        except sqlite3.Error as e:
            print(f"     ❌ HBPR表迁移失败: {e}")
            conn.rollback()
            return False
        finally:
            conn.close()


    def migrate_commands_table(self, db_file: str) -> bool:
        """迁移Commands表"""
        print(f"   🔄 迁移Commands表...")
        
        # 检查表是否存在
        conn = sqlite3.connect(db_file)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='commands'")
        if not cursor.fetchone():
            print(f"     ⚠️  commands表不存在，跳过")
            conn.close()
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
            print(f"     ✅ Commands表结构完整，无需迁移")
            conn.close()
            return True
        
        print(f"     📝  需要添加 {len(missing_columns)} 个列")
        
        # 添加缺失的列
        try:
            for column_name, column_type in missing_columns:
                cursor.execute(f"ALTER TABLE commands ADD COLUMN {column_name} {column_type}")
                print(f"       ➕ 添加列: {column_name}")
            
            # 创建必要的索引
            print(f"       🔧 创建索引...")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_commands_timeline ON commands(command_full, version)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_commands_parent ON commands(parent_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_commands_latest ON commands(command_full, is_latest)")
            
            # 更新现有记录的默认值
            print(f"       🔄 更新现有记录...")
            cursor.execute("UPDATE commands SET version = 1 WHERE version IS NULL")
            cursor.execute("UPDATE commands SET is_latest = TRUE WHERE is_latest IS NULL")
            
            conn.commit()
            print(f"     ✅ Commands表迁移成功")
            return True
            
        except sqlite3.Error as e:
            print(f"     ❌ Commands表迁移失败: {e}")
            conn.rollback()
            return False
        finally:
            conn.close()


    def migrate_database(self, db_file: str) -> bool:
        """迁移单个数据库"""
        print(f"\n🔄 正在迁移数据库: {os.path.basename(db_file)}")
        
        # 迁移HBPR表
        hbpr_success = self.migrate_hbpr_table(db_file)
        
        # 迁移Commands表
        commands_success = self.migrate_commands_table(db_file)
        
        return hbpr_success and commands_success


    def migrate_all_databases(self) -> None:
        """迁移所有数据库"""
        print("🚀 开始数据库迁移...")
        print("=" * 50)
        
        db_files = self.find_databases()
        if not db_files:
            print("❌ 没有找到需要迁移的数据库")
            return
        
        success_count = 0
        total_count = len(db_files)
        
        for db_file in db_files:
            if self.migrate_database(db_file):
                success_count += 1
        
        print("\n" + "=" * 50)
        print(f"🎉 迁移完成！成功: {success_count}/{total_count}")
        
        if success_count < total_count:
            print("⚠️  部分数据库迁移失败，请检查错误信息")
        else:
            print("✅  所有数据库迁移成功！")


    def verify_migration(self, db_file: str) -> bool:
        """验证迁移结果"""
        print(f"\n🔍 验证数据库: {os.path.basename(db_file)}")
        
        all_valid = True
        
        # 验证HBPR表
        columns = self.get_table_structure(db_file, "hbpr_full_records")
        if columns:
            existing_column_names = [col[1] for col in columns]
            required_column_names = [col[0] for col in self.hbpr_required_columns]
            missing_columns = set(required_column_names) - set(existing_column_names)
            
            if missing_columns:
                print(f"   ❌ HBPR表缺少列: {list(missing_columns)}")
                all_valid = False
            else:
                print(f"   ✅ HBPR表所有必需列都存在")
        
        # 验证Commands表
        columns = self.get_table_structure(db_file, "commands")
        if columns:
            existing_column_names = [col[1] for col in columns]
            required_column_names = [col[0] for col in self.commands_required_columns]
            missing_columns = set(required_column_names) - set(existing_column_names)
            
            if missing_columns:
                print(f"   ❌ Commands表缺少列: {list(missing_columns)}")
                all_valid = False
            else:
                print(f"   ✅ Commands表所有必需列都存在")
        
        return all_valid


    def verify_all_databases(self) -> None:
        """验证所有数据库的迁移结果"""
        print("\n🔍 验证所有数据库...")
        print("=" * 50)
        
        db_files = self.find_databases()
        if not db_files:
            return
        
        all_valid = True
        for db_file in db_files:
            if not self.verify_migration(db_file):
                all_valid = False
        
        if all_valid:
            print("\n🎉 所有数据库验证通过！")
        else:
            print("\n⚠️  部分数据库验证失败")


def main():
    """主函数"""
    migrator = DatabaseMigrator()
    
    # 执行迁移
    migrator.migrate_all_databases()
    
    # 验证迁移结果
    migrator.verify_all_databases()


if __name__ == "__main__":
    main()
