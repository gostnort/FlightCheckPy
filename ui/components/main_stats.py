#!/usr/bin/env python3
"""
Reusable component for displaying main HBPR statistics
"""

import streamlit as st
from ui.components.deleted_stats import display_deleted_stats


def display_main_statistics(all_stats):
    """
    Display main HBPR statistics in a reusable format
    
    Args:
        all_stats: Dictionary containing all statistics from get_all_statistics()
    """
    if not all_stats:
        st.error("❌ No statistics available")
        return
    
    # Extract individual stats
    range_info = all_stats.get('hbnb_range_info', {})
    missing_numbers = all_stats.get('missing_numbers', [])
    accepted_stats = all_stats.get('accepted_passengers_stats', {})
    deleted_stats = all_stats.get('deleted_passengers_stats', {})
    
    # First row: Main metrics
    st.subheader("📊 Main Statistics")
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
        b = accepted_stats.get('accepted_business', 0)
        y = accepted_stats.get('accepted_economy', 0)
        value = f"{adult}+{infant}Inf"
        delta = f"{b}/{y}"
        st.metric("Accepted Passengers", value, delta)
    
    # Second row: Deleted passenger statistics
    if deleted_stats and deleted_stats.get('total_deleted', 0) > 0:
        st.subheader("🗑️ Deleted Passengers")
        display_deleted_stats(deleted_stats)
    else:
        st.info("✅ No deleted passengers found")


def get_and_display_main_statistics(db):
    """
    Get all statistics from database and display them
    
    Args:
        db: HbprDatabase instance
    """
    try:
        all_stats = db.get_all_statistics()
        display_main_statistics(all_stats)
        return all_stats  # Return for additional processing if needed
    except Exception as e:
        st.error(f"❌ Error loading statistics: {e}")
        return None


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
