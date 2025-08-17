#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Commands表迁移脚本
用于为现有commands表添加缺失的列，确保所有commands表结构一致
"""

import os
import glob
import sqlite3
from typing import List, Tuple


class CommandsMigrator:
    """Commands表迁移器，用于修复现有commands表结构"""


    def __init__(self):
        """初始化迁移器"""
        self.databases_folder = "databases"
        self.required_columns = [
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


    def migrate_commands_table(self, db_file: str) -> bool:
        """迁移单个数据库的commands表"""
        print(f"\n🔄 正在迁移数据库: {os.path.basename(db_file)}")
        
        # 检查commands表是否存在
        conn = sqlite3.connect(db_file)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='commands'")
        if not cursor.fetchone():
            print(f"⚠️  {os.path.basename(db_file)} 中不存在 commands 表，跳过")
            conn.close()
            return False
        
        # 获取现有列
        cursor.execute("PRAGMA table_info(commands)")
        existing_columns = [column[1] for column in cursor.fetchall()]
        
        # 检查需要添加的列
        missing_columns = []
        for column_name, column_type in self.required_columns:
            if column_name not in existing_columns:
                missing_columns.append((column_name, column_type))
        
        if not missing_columns:
            print(f"✅  {os.path.basename(db_file)} commands表结构完整，无需迁移")
            conn.close()
            return True
        
        print(f"📝  需要添加 {len(missing_columns)} 个列")
        
        # 添加缺失的列
        try:
            for column_name, column_type in missing_columns:
                cursor.execute(f"ALTER TABLE commands ADD COLUMN {column_name} {column_type}")
                print(f"   ➕ 添加列: {column_name}")
            
            # 创建必要的索引
            print("   🔧 创建索引...")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_commands_timeline ON commands(command_full, version)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_commands_parent ON commands(parent_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_commands_latest ON commands(command_full, is_latest)")
            
            # 更新现有记录的默认值
            print("   🔄 更新现有记录...")
            cursor.execute("UPDATE commands SET version = 1 WHERE version IS NULL")
            cursor.execute("UPDATE commands SET is_latest = TRUE WHERE is_latest IS NULL")
            
            conn.commit()
            print(f"✅  {os.path.basename(db_file)} commands表迁移成功")
            return True
            
        except sqlite3.Error as e:
            print(f"❌ 迁移 {os.path.basename(db_file)} 失败: {e}")
            conn.rollback()
            return False
        finally:
            conn.close()


    def migrate_all_databases(self) -> None:
        """迁移所有数据库的commands表"""
        print("🚀 开始commands表迁移...")
        print("=" * 50)
        
        db_files = self.find_databases()
        if not db_files:
            print("❌ 没有找到需要迁移的数据库")
            return
        
        success_count = 0
        total_count = len(db_files)
        
        for db_file in db_files:
            if self.migrate_commands_table(db_file):
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
        
        columns = self.get_table_structure(db_file, "commands")
        if not columns:
            return False
        
        existing_column_names = [col[1] for col in columns]
        required_column_names = [col[0] for col in self.required_columns]
        
        missing_columns = set(required_column_names) - set(existing_column_names)
        
        if missing_columns:
            print(f"❌  缺少列: {list(missing_columns)}")
            return False
        else:
            print(f"✅  所有必需列都存在")
            return True


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
    migrator = CommandsMigrator()
    
    # 执行迁移
    migrator.migrate_all_databases()
    
    # 验证迁移结果
    migrator.verify_all_databases()


if __name__ == "__main__":
    main()
