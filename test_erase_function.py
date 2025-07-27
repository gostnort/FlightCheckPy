#!/usr/bin/env python3
"""
Test script for the erase_all_records_except_core function
"""

import sqlite3
import os
from hbpr_info_processor import HbprDatabase


def test_erase_function():
    """测试删除记录功能"""
    print("=== Testing Erase Function ===")
    
    # 创建测试数据库
    test_db = "test_erase.db"
    
    try:
        # 创建测试数据库和表
        conn = sqlite3.connect(test_db)
        cursor = conn.cursor()
        
        # 创建hbpr_full_records表
        cursor.execute('DROP TABLE IF EXISTS hbpr_full_records')
        cursor.execute('''
            CREATE TABLE hbpr_full_records (
                hbnb_number INTEGER PRIMARY KEY,
                record_content TEXT NOT NULL,
                is_validated BOOLEAN DEFAULT 0,
                is_valid BOOLEAN,
                name TEXT,
                seat TEXT,
                class TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # 插入测试数据
        test_data = [
            (1, "Test record 1", 1, 1, "John Doe", "1A", "Y"),
            (2, "Test record 2", 1, 0, "Jane Smith", "2B", "C"),
            (3, "Test record 3", 0, None, None, None, None)
        ]
        
        cursor.executemany('''
            INSERT INTO hbpr_full_records 
            (hbnb_number, record_content, is_validated, is_valid, name, seat, class)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', test_data)
        
        conn.commit()
        conn.close()
        
        print(f"✅ Created test database with {len(test_data)} records")
        
        # 测试删除功能
        db = HbprDatabase(test_db)
        
        # 检查删除前的记录数
        conn = sqlite3.connect(test_db)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM hbpr_full_records")
        before_count = cursor.fetchone()[0]
        print(f"📊 Records before erase: {before_count}")
        conn.close()
        
        # 执行删除
        success = db.erase_all_records_except_core()
        
        if success:
            # 检查删除后的记录数
            conn = sqlite3.connect(test_db)
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM hbpr_full_records")
            after_count = cursor.fetchone()[0]
            print(f"📊 Records after erase: {after_count}")
            conn.close()
            
            if after_count == 0:
                print("✅ Test PASSED: All records were successfully erased")
            else:
                print("❌ Test FAILED: Records still exist after erase")
        else:
            print("❌ Test FAILED: Erase function returned False")
        
    except Exception as e:
        print(f"❌ Test FAILED with error: {e}")
    
    finally:
        # 清理测试文件
        if os.path.exists(test_db):
            os.remove(test_db)
            print("🧹 Cleaned up test database")


if __name__ == "__main__":
    test_erase_function() 