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


    def __init__(self, conn: sqlite3.Connection):
        """
        初始化迁移器
        Args:
            conn (sqlite3.Connection): 数据库连接对象
        """
        if not conn:
            raise ValueError("A valid database connection must be provided.")
        self.conn = conn
        self.required_columns = [
            ('version', 'INTEGER DEFAULT 1'),
            ('parent_id', 'INTEGER'),
            ('is_latest', 'BOOLEAN DEFAULT TRUE')
        ]


    def migrate_commands_table(self) -> bool:
        """迁移当前连接的数据库中的commands表"""
        print(f"\n🔄 正在迁移Commands表...")
        
        # 检查commands表是否存在
        cursor = self.conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='commands'")
        if not cursor.fetchone():
            print(f"⚠️  数据库中不存在 commands 表，跳过")
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
            print(f"✅  Commands表结构完整，无需迁移")
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
            
            self.conn.commit()
            print(f"✅  Commands表迁移成功")
            return True
            
        except sqlite3.Error as e:
            print(f"❌ 迁移失败: {e}")
            self.conn.rollback()
            return False


    def verify_migration(self) -> bool:
        """验证迁移结果"""
        print(f"\n🔍 验证数据库Commands表...")
        
        try:
            cursor = self.conn.cursor()
            cursor.execute("PRAGMA table_info(commands)")
            columns = cursor.fetchall()
            if not columns:
                print("   ❌ Commands表不存在")
                return False
        except sqlite3.Error as e:
            print(f"   ❌ 无法读取Commands表结构: {e}")
            return False
            
        existing_column_names = [col[1] for col in columns]
        required_column_names = [col[0] for col in self.required_columns]
        
        missing_columns = set(required_column_names) - set(existing_column_names)
        
        if missing_columns:
            print(f"❌  缺少列: {list(missing_columns)}")
            return False
        else:
            print("✅  所有必需列都存在")
            return True


def main():
    """主函数 - 示例"""
    print("🚀 Commands表迁移脚本 (内存模式)")
    print("=" * 50)
    print("该脚本现在应该作为模块导入，而不是直接运行。")
    print("用法示例:")
    print("  from scripts.commands_migration import CommandsMigrator")
    print("  from ui.common import get_hbpr_database_client # Assuming UI is running")
    print("")
    print("  db_client = get_hbpr_database_client()")
    print("  if db_client:")
    print("      conn = db_client.get_connection()")
    print("      migrator = CommandsMigrator(conn)")
    print("      migrator.migrate_commands_table()")
    print("      migrator.verify_migration()")


if __name__ == "__main__":
    main()
