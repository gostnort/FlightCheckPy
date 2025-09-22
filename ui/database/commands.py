#!/usr/bin/env python3
"""
Commands tab for Database page - Command processing and maintenance
"""

import streamlit as st
from ui.common import (
    get_hbpr_database_client,
    is_db_available,
    get_database_name,
    trigger_auto_save
)


def show_commands_operations():
    """Show commands operations tab"""
    st.subheader("Commands Operations")

    if not is_db_available():
        st.warning("⚠️ No database loaded. Please select one from the sidebar.")
        return

    db_name = get_database_name()
    st.info(f"**Current Database:** `{db_name}`")

    # Commands operations buttons
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🔄 Migrate Timeline", use_container_width=True, help="Add versioning support to database"):
            db_client = get_hbpr_database_client()
            if db_client:
                from scripts.command_processor import CommandProcessor
                processor = CommandProcessor(db_client.get_connection())
                if processor.migrate_to_timeline():
                    st.success("✅ Migration completed successfully!")
                else:
                    st.info("ℹ️ Database schema is already up to date.")
    with col2:
        if st.button("🗑️ Clear Commands", use_container_width=True, help="Clear all command data"):
            db_client = get_hbpr_database_client()
            if db_client:
                from scripts.command_processor import CommandProcessor
                processor = CommandProcessor(db_client.get_connection())
                processor.erase_commands_table()
                trigger_auto_save()
                st.success("✅ All command data cleared!")

