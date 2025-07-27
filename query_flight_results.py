#!/usr/bin/env python3
"""
Query Flight HBPR Results
Display results from flight-specific HBPR databases including missing numbers.
"""
import sqlite3
import sys
import os
import glob


def list_available_flights() -> None:
    """列出所有可用的航班数据库"""
    db_files = glob.glob("*.db")
    flight_dbs = [f for f in db_files if f.endswith('.db')]
    # 显示可用航班
    print("=" * 60)
    print("AVAILABLE FLIGHT DATABASES")
    print("=" * 60)
    if not flight_dbs:
        print("No flight databases found!")
        return
    # 遍历每个数据库显示基本信息
    for db_file in sorted(flight_dbs):
        flight_id = db_file.replace('.db', '')
        try:
            conn = sqlite3.connect(db_file)
            cursor = conn.cursor()
            # 检查是否包含航班信息表
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='flight_info'")
            has_flight_info = cursor.fetchone() is not None
            # 获取记录统计
            cursor.execute("SELECT COUNT(*) FROM hbpr_full_records")
            full_count = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM hbpr_simple_records")
            simple_count = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM missing_numbers")
            missing_count = cursor.fetchone()[0]
            # 显示航班信息
            if has_flight_info:
                cursor.execute("SELECT flight_number, flight_date FROM flight_info")
                flight_info = cursor.fetchone()
                if flight_info:
                    print(f"Flight: {flight_info[0]} ({flight_info[1]}) - Database: {db_file}")
                else:
                    print(f"Flight: {flight_id} - Database: {db_file}")
            else:
                print(f"Legacy Database: {db_file}")
            print(f"  Records: {full_count} full, {simple_count} simple, {missing_count} missing")
            conn.close()
        except sqlite3.Error as e:
            print(f"Error reading {db_file}: {e}")
    print("=" * 60)
def query_flight_database(flight_db: str) -> None:
    """查询指定航班数据库并显示结果"""
    if not os.path.exists(flight_db):
        print(f"Database file '{flight_db}' not found!")
        return
    try:
        conn = sqlite3.connect(flight_db)
        cursor = conn.cursor()
        # 显示查询结果标题
        print("=" * 60)
        print(f"FLIGHT DATABASE QUERY RESULTS: {flight_db}")
        print("=" * 60)
        # 显示航班信息（如果存在）
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='flight_info'")
        if cursor.fetchone():
            cursor.execute("SELECT flight_id, flight_number, flight_date FROM flight_info")
            flight_info = cursor.fetchone()
            if flight_info:
                print(f"Flight ID: {flight_info[0]}")
                print(f"Flight Number: {flight_info[1]}")
                print(f"Flight Date: {flight_info[2]}")
                print()
        # 获取记录统计
        cursor.execute("SELECT COUNT(*) FROM hbpr_full_records")
        full_count = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM hbpr_simple_records")
        simple_count = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM missing_numbers")
        missing_count = cursor.fetchone()[0]
        print(f"Full HBPR records: {full_count}")
        print(f"Simple HBPR records: {simple_count}")
        print(f"Missing HBNB numbers: {missing_count}")
        print()
        # 显示HBNB号码范围
        cursor.execute("""
            SELECT MIN(hbnb_number), MAX(hbnb_number) 
            FROM (
                SELECT hbnb_number FROM hbpr_full_records
                UNION
                SELECT hbnb_number FROM hbpr_simple_records
            )
        """)
        result = cursor.fetchone()
        if result and result[0] is not None:
            min_num, max_num = result
            print(f"HBNB number range: {min_num} to {max_num}")
            print()
        # 显示前几条完整记录
        if full_count > 0:
            print("First 5 Full Records:")
            print("-" * 40)
            cursor.execute("""
                SELECT hbnb_number, substr(record_content, 1, 100) || '...' as preview
                FROM hbpr_full_records 
                ORDER BY hbnb_number 
                LIMIT 5
            """)
            for row in cursor.fetchall():
                print(f"HBNB {row[0]}: {row[1]}")
            print()
        # 显示前几条简单记录
        if simple_count > 0:
            print("First 10 Simple Records:")
            print("-" * 40)
            cursor.execute("""
                SELECT hbnb_number, record_line
                FROM hbpr_simple_records 
                ORDER BY hbnb_number 
                LIMIT 10
            """)
            for row in cursor.fetchall():
                print(f"HBNB {row[0]}: {row[1]}")
            print()
        # 显示缺失号码
        print("Missing HBNB Numbers:")
        print("-" * 40)
        cursor.execute("SELECT hbnb_number FROM missing_numbers ORDER BY hbnb_number")
        missing_numbers = [row[0] for row in cursor.fetchall()]
        # 显示缺失号码详情
        if missing_numbers:
            if len(missing_numbers) <= 50:
                print(f"All missing numbers: {missing_numbers}")
            else:
                print(f"First 50 missing numbers: {missing_numbers[:50]}")
                print(f"... and {len(missing_numbers) - 50} more")
            # 将连续缺失号码分组显示
            print("\nMissing numbers grouped:")
            groups = []
            current_group = [missing_numbers[0]]
            for i in range(1, len(missing_numbers)):
                if missing_numbers[i] == missing_numbers[i-1] + 1:
                    current_group.append(missing_numbers[i])
                else:
                    groups.append(current_group)
                    current_group = [missing_numbers[i]]
            groups.append(current_group)
            # 显示前10个分组
            for group in groups[:10]:
                if len(group) == 1:
                    print(f"  {group[0]}")
                else:
                    print(f"  {group[0]}-{group[-1]} ({len(group)} numbers)")
            if len(groups) > 10:
                print(f"  ... and {len(groups) - 10} more groups")
        else:
            print("No missing numbers found!")
        print()
        print("=" * 60)
        conn.close()
    except sqlite3.Error as e:
        print(f"Database error: {e}")
    except FileNotFoundError:
        print(f"Database file '{flight_db}' not found!")


def show_specific_record(hbnb_number: int, flight_db: str = None) -> None:
    """显示特定HBNB记录"""
    # 如果未指定数据库，搜索所有数据库
    if flight_db is None:
        db_files = glob.glob("*.db")
        found = False
        for db_file in db_files:
            if search_record_in_db(hbnb_number, db_file):
                found = True
        if not found:
            print(f"No record found for HBNB {hbnb_number} in any database")
    else:
        search_record_in_db(hbnb_number, flight_db)


def search_record_in_db(hbnb_number: int, db_file: str) -> bool:
    """在指定数据库中搜索记录"""
    try:
        conn = sqlite3.connect(db_file)
        cursor = conn.cursor()
        # 检查完整记录
        cursor.execute("SELECT record_content FROM hbpr_full_records WHERE hbnb_number = ?", (hbnb_number,))
        result = cursor.fetchone()
        if result:
            print(f"\nFull Record for HBNB {hbnb_number} in {db_file}:")
            print("-" * 60)
            print(result[0])
            conn.close()
            return True
        # 检查简单记录
        cursor.execute("SELECT record_line FROM hbpr_simple_records WHERE hbnb_number = ?", (hbnb_number,))
        result = cursor.fetchone()
        if result:
            print(f"\nSimple Record for HBNB {hbnb_number} in {db_file}:")
            print("-" * 60)
            print(result[0])
            conn.close()
            return True
        conn.close()
        return False
    except sqlite3.Error as e:
        print(f"Database error in {db_file}: {e}")
        return False
    

def main():
    """主函数处理命令行参数"""
    if len(sys.argv) == 1:
        # 无参数：显示所有可用航班
        list_available_flights()
    elif len(sys.argv) == 2:
        arg = sys.argv[1]
        # 检查是否为HBNB号码
        try:
            hbnb_num = int(arg)
            show_specific_record(hbnb_num)
        except ValueError:
            # 不是数字，当作数据库文件名处理
            if not arg.endswith('.db'):
                arg += '.db'
            query_flight_database(arg)
    elif len(sys.argv) == 3:
        # 两个参数：HBNB号码和数据库文件
        try:
            hbnb_num = int(sys.argv[1])
            db_file = sys.argv[2]
            if not db_file.endswith('.db'):
                db_file += '.db'
            show_specific_record(hbnb_num, db_file)
        except ValueError:
            print("First argument must be a valid HBNB number")
    else:
        # 显示使用说明
        print("Usage:")
        print("  python query_flight_results.py                    # List all flights")
        print("  python query_flight_results.py <flight_db>        # Query specific flight")
        print("  python query_flight_results.py <hbnb_number>      # Search HBNB in all flights")
        print("  python query_flight_results.py <hbnb_number> <flight_db>  # Search HBNB in specific flight")
if __name__ == "__main__":
    main() 