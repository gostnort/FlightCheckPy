#!/usr/bin/env python3
"""
Reusable component for displaying deleted passenger statistics
"""

import streamlit as st


def display_deleted_stats(deleted_stats):
    """
    Display deleted passenger statistics in a reusable format
    
    Args:
        deleted_stats: Dictionary containing deleted passenger statistics
    """
    if not deleted_stats:
        st.info("No deleted passenger statistics available")
        return
    
    col1, col2 = st.columns([1, 3])
    
    with col1:
        del_xres = deleted_stats.get('deleted_with_xres', 0)
        xres_nums = deleted_stats.get('xres_boarding_numbers', [])
        # 显示带XRES的删除乘客的原始登机号
        if xres_nums:
            if len(xres_nums) <= 8:
                delta = f"BN: {', '.join(map(str, xres_nums))}"
            else:
                delta = f"BN: {', '.join(map(str, xres_nums[:10]))}..."
        else:
            delta = "No XRES BN"
        st.metric("Del w XRES", del_xres, delta)
    
    with col2:
        del_nums = deleted_stats.get('original_boarding_numbers', [])
        # 显示删除乘客的原始登机号数量和号码列表
        if del_nums:
            value = str(len(del_nums))
            # 将前几个号码作为delta显示 - 显示更多数字
            if len(del_nums) <= 10:
                delta = f"BN: {', '.join(map(str, del_nums))}"
            else:
                delta = f"BN: {', '.join(map(str, del_nums[:30]))}..."
        else:
            value = "0"
            delta = "No Del BN"
        st.metric("Del w/o XRES", value, delta)


def get_and_display_deleted_stats(db):
    """
    Get deleted passenger statistics from database and display them
    
    Args:
        db: HbprDatabase instance
    """
    try:
        all_stats = db.get_all_statistics()
        deleted_stats = all_stats.get('deleted_passengers_stats', {})
        
        if deleted_stats and deleted_stats.get('total_deleted', 0) > 0:
            st.subheader("🗑️ Deleted Passengers")
            display_deleted_stats(deleted_stats)
        else:
            st.info("✅ No deleted passengers found")
    except Exception as e:
        st.error(f"❌ Error loading deleted passenger statistics: {e}")
