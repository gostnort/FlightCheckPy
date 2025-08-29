#!/usr/bin/env python3
"""
Calculation functions for deleted passenger and missing boarding number statistics
"""

from ui.db_management import db_manager



def get_missing_boarding_numbers(db):
    """
    从数据库中获取缺失的boarding_number（排除已删除乘客的号码）
    
    Args:
        db: HbprDatabase instance
        
    Returns:
        list: 真正缺失的boarding_number列表（不包括删除乘客的号码）
    """
    try:
        # 使用全局内存数据库连接
        conn = db_manager.get_database().get_connection()
        cursor = conn.cursor()
        
        # 获取所有有效的boarding_number（非空且非0）
        cursor.execute("""
            SELECT DISTINCT boarding_number 
            FROM hbpr_full_records 
            WHERE boarding_number IS NOT NULL 
            AND boarding_number > 0
            ORDER BY boarding_number
        """)
        
        boarding_numbers = [row[0] for row in cursor.fetchall()]
        
        # 获取已删除乘客的统计数据
        all_stats = db.get_all_statistics()
        deleted_stats = all_stats.get('deleted_passengers_stats', {})
        
        # 收集所有已删除乘客的boarding_number
        deleted_boarding_numbers = set()
        if deleted_stats:
            xres_nums = deleted_stats.get('xres_boarding_numbers', [])
            non_xres_nums = deleted_stats.get('original_boarding_numbers', [])
            deleted_boarding_numbers = set(xres_nums + non_xres_nums)
        
        # 不要关闭共享内存连接
        
        if not boarding_numbers:
            return []
            
        # 找出缺失的连续号码
        min_bn = min(boarding_numbers)
        max_bn = max(boarding_numbers)
        expected_numbers = set(range(min_bn, max_bn + 1))
        existing_numbers = set(boarding_numbers)
        missing_numbers = expected_numbers - existing_numbers
        
        # 从缺失号码中排除已删除乘客的号码
        truly_missing_numbers = sorted(missing_numbers - deleted_boarding_numbers)
        
        return truly_missing_numbers
        
    except Exception as e:
        print(f"Error getting missing boarding numbers: {e}")
        return []

