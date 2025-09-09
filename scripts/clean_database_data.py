#!/usr/bin/env python3
"""
Database Data Cleaning Utility
清理数据库中包含二进制/hex字符的数据，使其可以安全导出
"""

import sqlite3
import re


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


def clean_database_connection(conn: sqlite3.Connection) -> dict:
    """
    清理指定数据库连接中的所有问题数据
    Args:
        conn (sqlite3.Connection): 数据库连接对象
    Returns:
        dict: 包含清理结果的字典 {'success': bool, 'total_cleaned': int, 'messages': list}
    """
    messages = []
    if not conn:
        messages.append("❌ 数据库连接无效")
        return {"success": False, "total_cleaned": 0, "messages": messages}
    total_cleaned = 0
    try:
        cursor = conn.cursor()
        # 获取所有表名
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        messages.append(f"📊 发现 {len(tables)} 个表")
        for table in tables:
            if table.startswith("sqlite_"):
                continue  # 跳过系统表
            messages.append(f"🔍 处理表: {table}")
            # 获取表结构
            cursor.execute(f"PRAGMA table_info({table})")
            columns = cursor.fetchall()
            # 找到文本类型的列
            text_columns = []
            for col in columns:
                col_name = col[1]
                col_type = col[2].upper()
                if "TEXT" in col_type or "CHAR" in col_type or "VARCHAR" in col_type:
                    text_columns.append(col_name)
            if not text_columns:
                messages.append(f"   ⚠️  表 {table} 没有文本列，跳过")
                continue
            messages.append(f"   📝  发现 {len(text_columns)} 个文本列: {', '.join(text_columns)}")
            # 获取所有数据
            cursor.execute(f"SELECT * FROM {table}")
            rows = cursor.fetchall()
            if not rows:
                messages.append(f"   ℹ️  表 {table} 没有数据，跳过")
                continue
            messages.append(f"   📊  处理 {len(rows)} 行数据")
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
                    set_clause = ", ".join(
                        [f"{columns[i][1]} = ?" for i in range(len(columns))]
                    )
                    where_clause = " AND ".join(
                        [f"{columns[i][1]} = ?" for i in range(len(columns))]
                    )
                    update_sql = f"UPDATE {table} SET {set_clause} WHERE {where_clause}"
                    # 执行更新
                    cursor.execute(update_sql, new_values + list(row))
                    cleaned_count += 1
            if cleaned_count > 0:
                messages.append(f"   ✅  清理了 {cleaned_count} 行数据")
                total_cleaned += cleaned_count
            else:
                messages.append("   ℹ️  无需清理")
        # 提交更改
        conn.commit()
        messages.append("🎉 数据库清理完成！")
        messages.append(f"📊 总共清理了 {total_cleaned} 行数据")
        return {
            "success": True,
            "total_cleaned": total_cleaned,
            "messages": messages,
        }
    except Exception as e:
        messages.append(f"❌ 清理数据库时发生错误: {e}")
        conn.rollback()
        return {
            "success": False,
            "total_cleaned": total_cleaned,
            "messages": messages,
        }


def main():
    """
    主函数 - 现在作为一个示例，展示如何使用清理功能。
    这个脚本现在被设计为从其他模块导入和使用。
    """
    print("🧹 数据库数据清理工具")
    print("=" * 50)
    print("该脚本现在应该作为模块导入，而不是直接运行。")
    print("用法示例:")
    print("  from scripts.clean_database_data import clean_database_connection")
    print("  import sqlite3")
    print("  conn = sqlite3.connect(':memory:')")
    print("  # ... populate your database ...")
    print("  result = clean_database_connection(conn)")
    print("  if result['success']: print('清理成功')")


if __name__ == "__main__":
    main()

