#!/usr/bin/env python3
"""
Reusable component for displaying main HBPR statistics
"""

import streamlit as st


def display_main_statistics(all_stats, db=None):
    """
    Display main HBPR statistics in a reusable format
    Args:
        all_stats: Dictionary containing all statistics from get_all_statistics()
        db: HbprDatabase instance (optional, deprecated - no longer needed)
    """
    if not all_stats:
        st.error("❌ No statistics available")
        return
    # Extract individual stats
    range_info = all_stats.get('hbnb_range_info', {})
    missing_numbers = all_stats.get('missing_numbers', [])
    accepted_stats = all_stats.get('accepted_passengers_stats', {})
    deleted_stats = all_stats.get('deleted_passengers_stats', {})
    missing_boarding_numbers = all_stats.get('missing_boarding_numbers', [])
    # First row: Main metrics
    m1, m2, m3 = st.columns(3)
    with m1:
        max_hbnb = range_info.get('max', 0)
        st.metric("Max HBNB", max_hbnb)
    with m2:
        missing_count = len(missing_numbers)
        st.metric("Missing Count", missing_count)
    with m3:
        adult = accepted_stats.get('total_accepted', 0)
        infant = accepted_stats.get('infant_count', 0)
        f = accepted_stats.get('accepted_first', 0)
        c = accepted_stats.get('accepted_business', 0)
        y = accepted_stats.get('accepted_economy', 0)
        value = f"{adult} + {infant}Inf"
        # 只显示非零的舱位
        delta = f"{f}/{c}/{y}" if f > 0 else f"{c}/{y}"
        st.metric("Accepted Passengers", value, delta)
    # Second row: Deleted passenger statistics and Missing BN
    st.subheader("🗑️ Deleted Passengers")
    # 检查是否有任何数据需要显示
    has_deleted = deleted_stats and deleted_stats.get('total_deleted', 0) > 0
    has_missing = missing_boarding_numbers and len(missing_boarding_numbers) > 0
    if not has_deleted and not has_missing:
        st.info("✅ No deleted passengers or missing boarding numbers found")
    else:
        d1, d2 = st.columns(2)
        with d1:
            display_deleted_stats(deleted_stats)   
        with d2:
            # 显示缺失的boarding_number统计（在同一个section下）
            display_missing_boarding_numbers(missing_boarding_numbers)  


def display_detailed_range_info(all_stats):
    """
    Display detailed HBNB range information (for database page)
    Args:
        all_stats: Dictionary containing all statistics
    """
    if not all_stats:
        return
    range_info = all_stats.get('hbnb_range_info', {})
    missing_numbers = all_stats.get('missing_numbers', [])
    st.subheader("📈 HBNB Range Details")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        hbnb_range = f"{range_info.get('min', 0)} - {range_info.get('max', 0)}"
        st.metric("HBNB Range", hbnb_range)
    with col2:
        total_expected = range_info.get('total_expected', 0)
        st.metric("Total Expected", total_expected)
    with col3:
        total_found = range_info.get('total_found', 0)
        st.metric("Total Found", total_found)
    with col4:
        missing_count = len(missing_numbers)
        st.metric("Missing Numbers", missing_count)


def display_deleted_stats(deleted_stats):
    """
    Display deleted passenger statistics in a reusable format
    Args:
        deleted_stats: Dictionary containing deleted passenger statistics
    """
    if not deleted_stats:
        st.info("No deleted passenger statistics available")
        return
    # 合并所有删除乘客的登机号
    xres_nums = deleted_stats.get('xres_boarding_numbers', [])
    non_xres_nums = deleted_stats.get('original_boarding_numbers', [])
    all_deleted_nums = sorted(xres_nums + non_xres_nums)
    # 合并为一个统计项，但保持原有显示格式
    total_deleted = deleted_stats.get('total_deleted', 0)
    # 显示合并的删除乘客统计
    if all_deleted_nums:
        if len(all_deleted_nums) <= 40:
            delta = f"BN: {', '.join(map(str, all_deleted_nums))}"
        else:
            delta = f"BN: {', '.join(map(str, all_deleted_nums[:40]))}..."
    else:
        delta = "No Del BN"
    st.metric("Del in Records", total_deleted, delta)


def display_missing_boarding_numbers(missing_numbers):
    """
    显示缺失的boarding_number统计
    Args:
        missing_numbers: 缺失的boarding_number列表
    """
    if not missing_numbers:
        st.info("✅ No missing boarding numbers found")
        return
    missing_count = len(missing_numbers)
    # 显示缺失的登机号数量和号码列表
    if missing_count <= 40:
        delta = f"BN: {', '.join(map(str, missing_numbers))}"
    else:
        delta = f"BN: {', '.join(map(str, missing_numbers[:40]))}..."
    st.metric("Missing BN", missing_count, delta)

