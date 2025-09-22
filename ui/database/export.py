#!/usr/bin/env python3
"""
Export tab for Database page - Data export operations
"""

import streamlit as st
import pandas as pd
from ui.common import (
    get_hbpr_database_client,
    is_db_available,
    get_database_name
)
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


def show_export_operations():
    """Show export operations tab"""
    st.subheader("Export Operations")

    if not is_db_available():
        st.warning("⚠️ No database loaded. Please select one from the sidebar.")
        return

    db_name = get_database_name()
    st.info(f"**Current Database:** `{db_name}`")

    # Export operations buttons
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("📊 Export as Csv", use_container_width=True, help="Export processed records as CSV"):
            export_processed_data_as_csv()
    with col2:
        if st.button("📄 Export as Txt", use_container_width=True, help="Export processed records as text"):
            export_processed_data_as_txt()
    with col3:
        st.write("")  # Empty column for alignment


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

