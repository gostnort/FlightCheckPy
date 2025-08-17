#!/usr/bin/env python3
"""
Database Data Cleaning Utility
清理数据库中包含二进制/hex字符的数据，使其可以安全导出
"""

import sqlite3
import re
import os
import sys
from typing import List, Tuple


def clean_text_for_database(text: str) -> str:
    """
    清理文本数据，移除或替换无法在数据库中正常使用的字符
    Args:
        text (str): 原始文本
    Returns:
        str: 清理后的文本
    """
    if not text or not isinstance(text, str):
        return ""
    
    # 移除或替换控制字符（ASCII 0-31, 127）
    cleaned = re.sub(r'[\x00-\x1f\x7f]', ' ', text)
    
    # 移除或替换其他问题字符
    # 替换常见的二进制/hex字符
    cleaned = re.sub(r'[^\x20-\x7e\n\r\t]', ' ', cleaned)
    
    # 移除多余的空白字符
    cleaned = re.sub(r' +', ' ', cleaned)
    cleaned = re.sub(r'\n\s*\n', '\n', cleaned)
    
    # 确保文本以可打印字符结尾
    cleaned = cleaned.strip()
    
    return cleaned


def clean_database_file(db_file: str, backup: bool = True) -> bool:
    """
    清理指定数据库文件中的所有问题数据
    Args:
        db_file (str): 数据库文件路径
        backup (bool): 是否创建备份
    Returns:
        bool: 是否成功清理
    """
    if not os.path.exists(db_file):
        print(f"❌ 数据库文件不存在: {db_file}")
        return False
    
    try:
        # 创建备份
        if backup:
            backup_file = f"{db_file}.backup_{int(os.path.getmtime(db_file))}"
            import shutil
            shutil.copy2(db_file, backup_file)
            print(f"✅ 已创建备份: {backup_file}")
        
        # 连接数据库
        conn = sqlite3.connect(db_file)
        cursor = conn.cursor()
        
        # 获取所有表名
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        
        print(f"📊 发现 {len(tables)} 个表")
        
        total_cleaned = 0
        
        for table in tables:
            if table.startswith('sqlite_'):
                continue  # 跳过系统表
                
            print(f"🔍 处理表: {table}")
            
            # 获取表结构
            cursor.execute(f"PRAGMA table_info({table})")
            columns = cursor.fetchall()
            
            # 找到文本类型的列
            text_columns = []
            for col in columns:
                col_name = col[1]
                col_type = col[2].upper()
                if 'TEXT' in col_type or 'CHAR' in col_type or 'VARCHAR' in col_type:
                    text_columns.append(col_name)
            
            if not text_columns:
                print(f"   ⚠️  表 {table} 没有文本列，跳过")
                continue
            
            print(f"   📝  发现 {len(text_columns)} 个文本列: {', '.join(text_columns)}")
            
            # 获取所有数据
            cursor.execute(f"SELECT * FROM {table}")
            rows = cursor.fetchall()
            
            if not rows:
                print(f"   ℹ️  表 {table} 没有数据，跳过")
                continue
            
            print(f"   📊  处理 {len(rows)} 行数据")
            
            # 处理每一行
            cleaned_count = 0
            for row in rows:
                row_cleaned = False
                new_values = []
                
                for i, value in enumerate(row):
                    if i < len(columns) and columns[i][1] in text_columns:
                        if isinstance(value, str) and value:
                            cleaned_value = clean_text_for_database(value)
                            if cleaned_value != value:
                                row_cleaned = True
                            new_values.append(cleaned_value)
                        else:
                            new_values.append(value)
                    else:
                        new_values.append(value)
                
                # 如果行被清理了，更新数据库
                if row_cleaned:
                    # 构建UPDATE语句
                    set_clause = ", ".join([f"{columns[i][1]} = ?" for i in range(len(columns))])
                    where_clause = " AND ".join([f"{columns[i][1]} = ?" for i in range(len(columns))])
                    
                    update_sql = f"UPDATE {table} SET {set_clause} WHERE {where_clause}"
                    
                    # 执行更新
                    cursor.execute(update_sql, new_values + list(row))
                    cleaned_count += 1
            
            if cleaned_count > 0:
                print(f"   ✅  清理了 {cleaned_count} 行数据")
                total_cleaned += cleaned_count
            else:
                print(f"   ℹ️  无需清理")
        
        # 提交更改
        conn.commit()
        conn.close()
        
        print(f"\n🎉 数据库清理完成！")
        print(f"📊 总共清理了 {total_cleaned} 行数据")
        
        return True
        
    except Exception as e:
        print(f"❌ 清理数据库时发生错误: {e}")
        if 'conn' in locals():
            conn.rollback()
            conn.close()
        return False


def main():
    """主函数"""
    print("🧹 数据库数据清理工具")
    print("=" * 50)
    
    if len(sys.argv) < 2:
        print("使用方法: python clean_database_data.py <数据库文件路径> [--no-backup]")
        print("示例: python clean_database_data.py databases/CA984_15AUG25.db")
        print("选项:")
        print("  --no-backup    不创建备份文件")
        return
    
    db_file = sys.argv[1]
    backup = "--no-backup" not in sys.argv
    
    if not os.path.exists(db_file):
        print(f"❌ 数据库文件不存在: {db_file}")
        return
    
    print(f"🎯 目标数据库: {db_file}")
    print(f"📦 备份模式: {'启用' if backup else '禁用'}")
    print()
    
    # 确认操作
    if backup:
        print("⚠️  警告: 此操作将清理数据库中的问题数据")
        print("💡 建议: 首次运行前请手动备份数据库文件")
    else:
        print("⚠️  警告: 此操作将清理数据库中的问题数据，且不会创建备份")
    
    confirm = input("\n是否继续？(y/N): ").strip().lower()
    if confirm not in ['y', 'yes']:
        print("❌ 操作已取消")
        return
    
    # 执行清理
    success = clean_database_file(db_file, backup)
    
    if success:
        print("\n✅ 数据库清理成功完成！")
        print("💡 现在可以尝试导出数据了")
    else:
        print("\n❌ 数据库清理失败")
        print("💡 请检查错误信息并重试")


if __name__ == "__main__":
    main()
