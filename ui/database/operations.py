#!/usr/bin/env python3
"""
Operations tab for Database page - HBPR operations and database management
"""

import streamlit as st
import pandas as pd
from ui.common import (
    get_hbpr_database_client,
    is_db_available,
    get_database_name,
    trigger_auto_save
)
from ui.process_records.process_all import start_processing_all_records
from ui.process_records.export_data import export_as_origin_txt, safe_export_dataframe


def execute_query_to_dataframe(db, query, params=None):
    """
    Execute a SQL query using the remote connection and return results as pandas DataFrame.
    This avoids pandas compatibility issues with RemoteSqliteConnection.
    """
    try:
        conn = db.get_connection()
        cursor = conn.cursor()
        cursor.execute(query, params or [])

        # Get column names from cursor description
        if cursor.description:
            columns = [desc[0] for desc in cursor.description]
        else:
            columns = []

        # Get all rows
        rows = cursor.fetchall()

        # Create DataFrame
        if columns and rows:
            return pd.DataFrame(rows, columns=columns)
        elif columns:
            return pd.DataFrame(columns=columns)
        else:
            return pd.DataFrame()

    except Exception as e:
        st.error(f"❌ Error executing query: {str(e)}")
        return pd.DataFrame()


def show_database_operations():
    """Show database operations with organized button layout"""
    st.subheader("Database Operations")

    if not is_db_available():
        st.warning("⚠️ No database loaded. Please select one from the sidebar.")
        return

    db_name = get_database_name()
    st.info(f"**Current Database:** `{db_name}`")

    # HBPR row
    st.markdown("**HBPR Operations:**")
    hbpr_col1, hbpr_col2, hbpr_col3, hbpr_col4 = st.columns(4)
    with hbpr_col1:
        if st.button("📥 Create from HBPR", use_container_width=True, help="Upload and process HBPR list file"):
            st.session_state.create_hbpr_triggered = True
    with hbpr_col2:
        if st.button("🔄 Process Again", use_container_width=True, help="Run processing on existing records"):
            db = get_hbpr_database_client()
            if db:
                start_processing_all_records(db, None)
    with hbpr_col3:
        if st.button("🧹 Erase Result", use_container_width=True, help="Clear all processing results"):
            db = get_hbpr_database_client()
            if db:
                from ui.process_records.process_all import erase_splited_records
                erase_splited_records(db)
    with hbpr_col4:
        if st.button("💾 Save DB", use_container_width=True, help="Save database to disk"):
            if trigger_auto_save():
                st.success(f"✅ Database `{db_name}` saved successfully.")
            else:
                st.error("❌ Failed to save database.")

    # Handle Create from HBPR
    if st.session_state.get('create_hbpr_triggered', False):
        del st.session_state.create_hbpr_triggered
        show_create_from_hbpr()

    # Commands row
    st.markdown("**Commands Operations:**")
    cmd_col1, cmd_col2 = st.columns(2)
    with cmd_col1:
        if st.button("🔄 Migrate Timeline", use_container_width=True, help="Add versioning support to database"):
            db_client = get_hbpr_database_client()
            if db_client:
                from scripts.command_processor import CommandProcessor
                processor = CommandProcessor(db_client.get_connection())
                if processor.migrate_to_timeline():
                    st.success("✅ Migration completed successfully!")
                else:
                    st.info("ℹ️ Database schema is already up to date.")
    with cmd_col2:
        if st.button("🗑️ Clear Commands", use_container_width=True, help="Clear all command data"):
            db_client = get_hbpr_database_client()
            if db_client:
                from scripts.command_processor import CommandProcessor
                processor = CommandProcessor(db_client.get_connection())
                processor.erase_commands_table()
                trigger_auto_save()
                st.success("✅ All command data cleared!")

    # Database operation row
    st.markdown("**Export Operations:**")
    export_col1, export_col2, export_col3 = st.columns(3)
    with export_col1:
        if st.button("📊 Export as Csv", use_container_width=True, help="Export processed records as CSV"):
            export_processed_data_as_csv()
    with export_col2:
        if st.button("📄 Export as Txt", use_container_width=True, help="Export processed records as text"):
            export_processed_data_as_txt()
    with export_col3:
        st.write("")  # Empty column for alignment


def show_create_from_hbpr():
    """Handle Create from HBPR functionality with auto-processing"""
    st.subheader("📥 Create from HBPR")
    uploaded_file = st.file_uploader(
        "Upload an HBPR List file (e.g., sample_hbpr_list.txt)",
        type=["txt"],
        help="This will process the file and load the data into the current in-memory database.",
        key="hbpr_upload"
    )

    if uploaded_file is not None:
        file_content = uploaded_file.getvalue().decode("utf-8")

        with st.spinner("Processing file and loading data..."):
            try:
                db_client = get_hbpr_database_client()
                if not db_client:
                    st.error("Database service is not available. Please log in again.")
                    return
                conn = db_client.get_connection()
                from scripts.hbpr_list_processor import HBPRProcessor
                processor = HBPRProcessor(conn)
                processor.process(file_content)
                st.success("✅ HBPR data processed and loaded into the current in-memory database.")

                if trigger_auto_save():
                    st.toast("Database changes have been saved to disk.")

                # Auto-run processing after successful HBPR creation
                st.info("🔄 Auto-starting record processing...")
                start_processing_all_records(db_client, None)

            except Exception as e:
                st.error(f"❌ Error processing file: {e}")


def export_processed_data_as_csv():
    """Export processed records as CSV"""
    try:
        db = get_hbpr_database_client()
        if not db:
            st.error("Database not available")
            return

        df = execute_query_to_dataframe(db, """
            SELECT hbnb_number, created_at, is_validated, is_valid, boarding_number,
                   pnr, name, seat, class, destination, bag_piece, bag_weight,
                   bag_allowance, ff, pspt_name, pspt_exp_date, ckin_msg, asvc_msg,
                   expc_piece, expc_weight, asvc_piece, fba_piece, ifba_piece,
                   has_infant, flyer_benefit, is_ca_flyer, inbound_flight,
                   outbound_flight, properties, tkne, error_count, error_baggage,
                   error_passport, error_name, error_visa, error_other, validated_at,
                   bol_duplicate
            FROM hbpr_full_records
            WHERE is_validated = 1
            ORDER BY hbnb_number
        """)

        if df.empty:
            st.info("ℹ️ No processed records to export.")
            return

        export_df = safe_export_dataframe(df)
        csv_data = export_df.to_csv(index=False)
        st.download_button(
            label="📥 Download CSV",
            data=csv_data,
            file_name=f"hbpr_results_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv",
            use_container_width=True,
            key="csv_download"
        )
    except Exception as e:
        st.error(f"❌ Error exporting CSV: {str(e)}")


def export_processed_data_as_txt():
    """Export processed records as text"""
    try:
        db = get_hbpr_database_client()
        if not db:
            st.error("Database not available")
            return

        conn = db.get_connection()
        txt_data = export_as_origin_txt(conn)
        st.download_button(
            label="📥 Download TXT",
            data=txt_data,
            file_name=f"origin_data_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.txt",
            mime="text/plain",
            use_container_width=True,
            key="txt_download"
        )
    except Exception as e:
        st.error(f"❌ Error exporting TXT: {str(e)}")
