#!/usr/bin/env python3
"""
Home metrics helper for the FlightCheckPy UI.

Responsibilities:
- Create lightweight SQLite views for live-updating summary counts
- Parse SY command text to extract compartment configuration (CNF/JxYy)
- Provide a single function returning the values needed by the home page

All SQL is defensive and will auto-create views if missing.
"""

import os
import re
import sqlite3
from typing import Dict, Optional, Tuple


def _connect(db_file: str) -> sqlite3.Connection:
    if not db_file or not os.path.exists(db_file):
        raise FileNotFoundError(f"Database file not found: {db_file}")
    conn = sqlite3.connect(db_file)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA busy_timeout = 30000")
    return conn


def create_or_refresh_views(db_file: str) -> None:
    """Create views used by the home page. Idempotent.

    Views:
    - vw_home_accepted_counts: totals for accepted pax (adults), infants, J/Y adult split
    - vw_home_flags: ID (SA) counts by class, NOSHOW by class, INAD total
    """
    conn = _connect(db_file)
    cur = conn.cursor()

    # Drop and recreate to keep logic simple and always up-to-date
    cur.execute("DROP VIEW IF EXISTS vw_home_accepted_counts")
    cur.execute(
        """
        CREATE VIEW vw_home_accepted_counts AS
        SELECT
            -- Total accepted passengers (boarding number present)
            SUM(CASE WHEN boarding_number IS NOT NULL AND boarding_number > 0 THEN 1 ELSE 0 END) AS total_accepted,
            -- Adults with infant flag on the record
            SUM(CASE WHEN boarding_number IS NOT NULL AND boarding_number > 0 AND IFNULL(has_infant, 0) = 1 THEN 1 ELSE 0 END) AS infant_count,
            -- Business cabin accepted (F/C)
            SUM(CASE WHEN boarding_number IS NOT NULL AND boarding_number > 0 AND class IN ('F','C') THEN 1 ELSE 0 END) AS accepted_business,
            -- Economy cabin accepted (Y)
            SUM(CASE WHEN boarding_number IS NOT NULL AND boarding_number > 0 AND class = 'Y' THEN 1 ELSE 0 END) AS accepted_economy
        FROM hbpr_full_records
        """
    )

    cur.execute("DROP VIEW IF EXISTS vw_home_flags")
    cur.execute(
        """
        CREATE VIEW vw_home_flags AS
        SELECT
            -- SA indicates ID staff tickets (match as token, not substring like in USA)
            SUM(CASE WHEN boarding_number IS NOT NULL AND boarding_number > 0 AND class IN ('F','C') AND (
                      INSTR(','||IFNULL(properties,'')||',', ',SA') > 0
                    ) THEN 1 ELSE 0 END) AS id_j,
            SUM(CASE WHEN boarding_number IS NOT NULL AND boarding_number > 0 AND class = 'Y' AND (
                      INSTR(','||IFNULL(properties,'')||',', ',SA') > 0
                    ) THEN 1 ELSE 0 END) AS id_y,
            -- NOSHOW: total - XRES - SA - BN - empty_properties
            SUM(CASE WHEN class IN ('F','C')
                      AND (boarding_number IS NULL OR boarding_number = 0)
                      AND INSTR(','||IFNULL(properties,'')||',', ',XRES') = 0
                      AND INSTR(','||IFNULL(properties,'')||',', ',SA') = 0
                      AND LENGTH(TRIM(IFNULL(properties,''))) > 0
                THEN 1 ELSE 0 END) AS noshow_j,
            SUM(CASE WHEN class = 'Y'
                      AND (boarding_number IS NULL OR boarding_number = 0)
                      AND INSTR(','||IFNULL(properties,'')||',', ',XRES') = 0
                      AND INSTR(','||IFNULL(properties,'')||',', ',SA') = 0
                      AND LENGTH(TRIM(IFNULL(properties,''))) > 0
                THEN 1 ELSE 0 END) AS noshow_y,
            -- INAD: any record with INAD property
            SUM(CASE WHEN IFNULL(properties,'') LIKE '%INAD%' THEN 1 ELSE 0 END) AS inad_total
        FROM hbpr_full_records
        """
    )

    conn.commit()
    conn.close()


def _parse_cnf_from_text(text: str) -> Optional[Tuple[int, int]]:
    """Extract CNF/JxYy from a block of SY command text.

    Returns a tuple (j_compartment, y_compartment) if found.
    """
    if not text:
        return None
    # Common patterns seen: CNF/J36Y356 (no space) or CNF/J36 Y356 (with space)
    m = re.search(r"CNF\s*/?\s*J\s*(\d+)\s*Y\s*(\d+)", text)
    if m:
        return int(m.group(1)), int(m.group(2))
    return None


def get_sy_compartments(db_file: str) -> Optional[Tuple[int, int]]:
    """Find the latest SY command matching current flight in DB and parse CNF.

    Looks up the flight in table flight_info, then finds the newest matching
    command in table commands where command_type = 'SY' and is_latest = 1.
    """
    conn = _connect(db_file)
    cur = conn.cursor()
    # Read flight number/date
    cur.execute("SELECT flight_number, flight_date FROM flight_info LIMIT 1")
    row = cur.fetchone()
    if not row:
        conn.close()
        return None
    flt_no, flt_date = row[0], row[1]
    # Try to find an SY command for this flight/date
    cur.execute(
        """
        SELECT command_full, content
        FROM commands
        WHERE command_type = 'SY'
          AND is_latest = 1
          AND flight_number = ?
          AND flight_date = ?
        ORDER BY updated_at DESC, id DESC
        LIMIT 1
        """,
        (flt_no, flt_date)
    )
    cmd = cur.fetchone()
    conn.close()
    if not cmd:
        return None
    command_full, content = cmd
    for text in (content or "", command_full or ""):
        result = _parse_cnf_from_text(text)
        if result:
            return result
    return None


def get_home_summary(db_file: str) -> Dict[str, object]:
    """Return a dict with all values needed by the home page expander.

    Keys: flight_number, flight_date, total_accepted, infant_count,
          accepted_business, accepted_economy, id_j, id_y,
          noshow_j, noshow_y, inad_total, j_cnf, y_cnf, ratio
    """
    # Ensure views exist
    create_or_refresh_views(db_file)

    conn = _connect(db_file)
    cur = conn.cursor()

    # Flight info
    cur.execute("SELECT flight_number, flight_date FROM flight_info LIMIT 1")
    flight_row = cur.fetchone()
    flight_number, flight_date = (flight_row[0], flight_row[1]) if flight_row else ("", "")

    # Accepted counts
    cur.execute("SELECT total_accepted, infant_count, accepted_business, accepted_economy FROM vw_home_accepted_counts")
    a = cur.fetchone() or (0, 0, 0, 0)
    total_accepted, infant_count, accepted_business, accepted_economy = a

    # Flags
    cur.execute("SELECT id_j, id_y, noshow_j, noshow_y, inad_total FROM vw_home_flags")
    f = cur.fetchone() or (0, 0, 0, 0, 0)
    id_j, id_y, noshow_j, noshow_y, inad_total = f

    conn.close()

    # CNF from SY
    cnf = get_sy_compartments(db_file)
    j_cnf, y_cnf = (cnf if cnf else (0, 0))

    compartment_total = (j_cnf or 0) + (y_cnf or 0)
    ratio = None
    if compartment_total > 0:
        ratio = round((total_accepted / compartment_total) * 100)

    return {
        'flight_number': flight_number,
        'flight_date': flight_date,
        'total_accepted': int(total_accepted or 0),
        'infant_count': int(infant_count or 0),
        'accepted_business': int(accepted_business or 0),
        'accepted_economy': int(accepted_economy or 0),
        'id_j': int(id_j or 0),
        'id_y': int(id_y or 0),
        'noshow_j': int(noshow_j or 0),
        'noshow_y': int(noshow_y or 0),
        'inad_total': int(inad_total or 0),
        'j_cnf': int(j_cnf or 0),
        'y_cnf': int(y_cnf or 0),
        'ratio': ratio,
    }


def get_debug_data(db_file: str) -> Dict[str, object]:
    """Return debug data for manual verification of statistics"""
    conn = _connect(db_file)
    cur = conn.cursor()
    
    debug_data = {}
    
    # Get total counts by class
    cur.execute("""
        SELECT class, COUNT(*) as total_count,
               SUM(CASE WHEN boarding_number IS NOT NULL AND boarding_number > 0 THEN 1 ELSE 0 END) as with_bn,
               SUM(CASE WHEN boarding_number IS NULL OR boarding_number = 0 THEN 1 ELSE 0 END) as without_bn
        FROM hbpr_full_records 
        GROUP BY class
    """)
    debug_data['class_breakdown'] = cur.fetchall()
    
    # Get XRES counts
    cur.execute("""
        SELECT class, COUNT(*) as xres_count
        FROM hbpr_full_records 
        WHERE INSTR(','||IFNULL(properties,'')||',', ',XRES') > 0
        GROUP BY class
    """)
    debug_data['xres_counts'] = cur.fetchall()
    
    # Get SA counts
    cur.execute("""
        SELECT class, COUNT(*) as sa_count
        FROM hbpr_full_records 
        WHERE INSTR(','||IFNULL(properties,'')||',', ',SA') > 0
        GROUP BY class
    """)
    debug_data['sa_counts'] = cur.fetchall()
    
    # Get empty properties counts
    cur.execute("""
        SELECT class, COUNT(*) as empty_props_count
        FROM hbpr_full_records 
        WHERE LENGTH(TRIM(IFNULL(properties,''))) = 0
        GROUP BY class
    """)
    debug_data['empty_properties'] = cur.fetchall()
    
    # Get sample records for each category
    cur.execute("""
        SELECT hbnb_number, class, boarding_number, properties
        FROM hbpr_full_records 
        WHERE INSTR(','||IFNULL(properties,'')||',', ',XRES') > 0
        LIMIT 5
    """)
    debug_data['xres_samples'] = cur.fetchall()
    
    cur.execute("""
        SELECT hbnb_number, class, boarding_number, properties
        FROM hbpr_full_records 
        WHERE INSTR(','||IFNULL(properties,'')||',', ',SA') > 0
        LIMIT 5
    """)
    debug_data['sa_samples'] = cur.fetchall()
    
    cur.execute("""
        SELECT hbnb_number, class, boarding_number, properties
        FROM hbpr_full_records 
        WHERE (boarding_number IS NULL OR boarding_number = 0)
          AND INSTR(','||IFNULL(properties,'')||',', ',XRES') = 0
          AND INSTR(','||IFNULL(properties,'')||',', ',SA') = 0
          AND LENGTH(TRIM(IFNULL(properties,''))) > 0
        LIMIT 5
    """)
    debug_data['noshow_samples'] = cur.fetchall()
    
    conn.close()
    return debug_data


def get_debug_summary(db_file: str) -> str:
    """Return a formatted debug summary string for manual verification"""
    try:
        debug_data = get_debug_data(db_file)
        
        summary = []
        summary.append("🔍 Debug Data for Manual Verification")
        summary.append("")
        
        # Class breakdown
        summary.append("**Class Breakdown:**")
        for row in debug_data['class_breakdown']:
            summary.append(f"- Class {row[0]}: Total={row[1]}, With BN={row[2]}, Without BN={row[3]}")
        
        # XRES counts
        summary.append("")
        summary.append("**XRES Counts:**")
        for row in debug_data['xres_counts']:
            summary.append(f"- Class {row[0]}: {row[1]} records")
        
        # SA counts  
        summary.append("")
        summary.append("**SA Counts:**")
        for row in debug_data['sa_counts']:
            summary.append(f"- Class {row[0]}: {row[1]} records")
        
        # Empty properties
        summary.append("")
        summary.append("**Empty Properties Counts:**")
        for row in debug_data['empty_properties']:
            summary.append(f"- Class {row[0]}: {row[1]} records")
        
        # Sample records
        summary.append("")
        summary.append("**XRES Sample Records:**")
        for row in debug_data['xres_samples']:
            summary.append(f"- HBNB {row[0]}, Class {row[1]}, BN {row[2]}, Props: {row[3]}")
        
        summary.append("")
        summary.append("**SA Sample Records:**")
        for row in debug_data['sa_samples']:
            summary.append(f"- HBNB {row[0]}, Class {row[1]}, BN {row[2]}, Props: {row[3]}")
        
        summary.append("")
        summary.append("**NOSHOW Sample Records:**")
        for row in debug_data['noshow_samples']:
            summary.append(f"- HBNB {row[0]}, Class {row[1]}, BN {row[2]}, Props: {row[3]}")
            
        return "\n".join(summary)
        
    except Exception as e:
        return f"Error getting debug data: {str(e)}"


