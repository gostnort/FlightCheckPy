#!/usr/bin/env python3
"""
Flight summary and metrics helper for the FlightCheckPy UI.

Responsibilities:
- Create lightweight SQLite views for live-updating summary counts
- Extract compartment configuration from SY commands (using Scripts layer)
- Build flight summary messages for home page display

All SQL is defensive and will auto-create views if missing.
"""

import sqlite3
from typing import Dict, Optional, Tuple
from ui.common import get_hbpr_database_client
from scripts.commands_parsing.sy import extract_cnf_from_text


def _get_conn() -> sqlite3.Connection:
    """Get shared in-memory DB connection from global manager."""
    db = get_hbpr_database_client()
    if not db:
        raise ConnectionError("Database client not available.")
    conn = db.get_connection()
    # Ensure sane pragmas (no-ops if already set)
    try:
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA busy_timeout = 30000")
    except Exception:
        pass
    return conn


def create_or_refresh_views() -> None:
    """Create views used by the home page. Idempotent.
    Views:
    - vw_home_accepted_counts: totals for accepted pax (adults), infants, F/C/Y split
    - vw_home_flags: ID staff (SA, PAD-2, PAD-SA) counts by class, NOSHOW by class, INAD total
    数据库有三个主舱位:
    - 'F' = First Class (头等舱) - 最高级，无ID员工
    - 'C' = Business Class (公务舱) - 商务舱，有ID员工
    - 'Y' = Economy Class (经济舱) - 经济舱，有ID员工
    """
    conn = _get_conn()
    cur = conn.cursor()
    # Drop and recreate to keep logic simple and always up-to-date
    cur.execute("DROP VIEW IF EXISTS vw_home_accepted_counts")
    cur.execute(
        """
        CREATE VIEW vw_home_accepted_counts AS
        SELECT
            -- 已接受乘客总数 (boarding number present)
            SUM(CASE WHEN boarding_number IS NOT NULL AND boarding_number > 0 THEN 1 ELSE 0 END) AS total_accepted,
            -- 带婴儿的成人
            SUM(CASE WHEN boarding_number IS NOT NULL AND boarding_number > 0 AND IFNULL(has_infant, 0) = 1 THEN 1 ELSE 0 END) AS infant_count,
            -- 头等舱已接受 (F)
            SUM(CASE WHEN boarding_number IS NOT NULL AND boarding_number > 0 AND class = 'F' THEN 1 ELSE 0 END) AS accepted_first,
            -- 商务舱已接受 (C)
            SUM(CASE WHEN boarding_number IS NOT NULL AND boarding_number > 0 AND class = 'C' THEN 1 ELSE 0 END) AS accepted_business,
            -- 经济舱已接受 (Y)
            SUM(CASE WHEN boarding_number IS NOT NULL AND boarding_number > 0 AND class = 'Y' THEN 1 ELSE 0 END) AS accepted_economy
        FROM hbpr_full_records
        """
    )
    cur.execute("DROP VIEW IF EXISTS vw_home_flags")
    cur.execute(
        """
        CREATE VIEW vw_home_flags AS
        SELECT
            -- ID员工票: SA, PAD-2, PAD-SA (仅C和Y舱有，F舱无)
            (SELECT COUNT(DISTINCT hbnb_number) 
             FROM hbpr_full_records 
             WHERE boarding_number IS NOT NULL AND boarding_number > 0 AND class = 'C' AND (
                      INSTR(','||IFNULL(properties,'')||',', ',SA') > 0 OR
                      INSTR(','||IFNULL(properties,'')||',', ',PAD-2') > 0 OR
                      INSTR(','||IFNULL(properties,'')||',', ',PAD-SA') > 0
                    )) AS id_c,
            (SELECT COUNT(DISTINCT hbnb_number) 
             FROM hbpr_full_records 
             WHERE boarding_number IS NOT NULL AND boarding_number > 0 AND class = 'Y' AND (
                      INSTR(','||IFNULL(properties,'')||',', ',SA') > 0 OR
                      INSTR(','||IFNULL(properties,'')||',', ',PAD-2') > 0 OR
                      INSTR(','||IFNULL(properties,'')||',', ',PAD-SA') > 0
                    )) AS id_y,
            -- NOSHOW: 总数 - XRES - ID员工 (SA, PAD-2, PAD-SA) - BN - empty_properties
            (SELECT COUNT(DISTINCT hbnb_number) 
             FROM hbpr_full_records 
             WHERE class = 'F'
                      AND (boarding_number IS NULL OR boarding_number = 0)
                      AND INSTR(','||IFNULL(properties,'')||',', ',XRES') = 0
                      AND LENGTH(TRIM(IFNULL(properties,''))) > 0) AS noshow_f,
            (SELECT COUNT(DISTINCT hbnb_number) 
             FROM hbpr_full_records 
             WHERE class = 'C'
                      AND (boarding_number IS NULL OR boarding_number = 0)
                      AND INSTR(','||IFNULL(properties,'')||',', ',XRES') = 0
                      AND INSTR(','||IFNULL(properties,'')||',', ',SA') = 0
                      AND INSTR(','||IFNULL(properties,'')||',', ',PAD-2') = 0
                      AND INSTR(','||IFNULL(properties,'')||',', ',PAD-SA') = 0
                      AND LENGTH(TRIM(IFNULL(properties,''))) > 0) AS noshow_c,
            (SELECT COUNT(DISTINCT hbnb_number) 
             FROM hbpr_full_records 
             WHERE class = 'Y'
                      AND (boarding_number IS NULL OR boarding_number = 0)
                      AND INSTR(','||IFNULL(properties,'')||',', ',XRES') = 0
                      AND INSTR(','||IFNULL(properties,'')||',', ',SA') = 0
                      AND INSTR(','||IFNULL(properties,'')||',', ',PAD-2') = 0
                      AND INSTR(','||IFNULL(properties,'')||',', ',PAD-SA') = 0
                      AND LENGTH(TRIM(IFNULL(properties,''))) > 0) AS noshow_y,
            -- INAD: 任何带有INAD属性的记录
            (SELECT COUNT(DISTINCT hbnb_number) 
             FROM hbpr_full_records 
             WHERE IFNULL(properties,'') LIKE '%INAD%') AS inad_total
        """
    )
    conn.commit()


def get_sy_compartments() -> Optional[Tuple[int, int, int]]:
    """Find the latest SY command and parse CNF.
    Both departure and arrival SY have identical compartment configurations.
    Returns (f_cnf, j_cnf, y_cnf) or None.
    """
    conn = _get_conn()
    cur = conn.cursor()
    # Read flight number/date
    cur.execute("SELECT flight_number, flight_date FROM flight_info LIMIT 1")
    row = cur.fetchone()
    if not row:
        return None
    flt_no, flt_date = row[0], row[1]
    # Get any SY command - both have same compartments
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
    # Do not close shared connection
    if not cmd:
        return None
    command_full, content = cmd
    # 使用 Scripts 层的解析函数（遵循三层架构）
    for text in (content or "", command_full or ""):
        result = extract_cnf_from_text(text)
        if result:
            return result
    return None


def get_home_summary() -> Dict[str, object]:
    """Return a dict with all values needed by the home page expander.
    Keys: flight_number, flight_date, total_accepted, infant_count,
          accepted_first, accepted_business, accepted_economy,
          id_c, id_y, noshow_f, noshow_c, noshow_y, inad_total,
          f_cnf, j_cnf, y_cnf, ratio
    """
    # Ensure views exist
    create_or_refresh_views()
    conn = _get_conn()
    cur = conn.cursor()
    # Flight info
    cur.execute("SELECT flight_number, flight_date FROM flight_info LIMIT 1")
    flight_row = cur.fetchone()
    flight_number, flight_date = (flight_row[0], flight_row[1]) if flight_row else ("", "")
    # Accepted counts - 现在包含三个舱位: F, C, Y
    cur.execute("SELECT total_accepted, infant_count, accepted_first, accepted_business, accepted_economy FROM vw_home_accepted_counts")
    a = cur.fetchone() or (0, 0, 0, 0, 0)
    total_accepted, infant_count, accepted_first, accepted_business, accepted_economy = a
    # Flags - id_c (C舱ID员工), id_y (Y舱ID员工), noshow_f/c/y (三个舱位的noshow)
    cur.execute("SELECT id_c, id_y, noshow_f, noshow_c, noshow_y, inad_total FROM vw_home_flags")
    f = cur.fetchone() or (0, 0, 0, 0, 0, 0)
    id_c, id_y, noshow_f, noshow_c, noshow_y, inad_total = f
    # Do not close shared connection
    # CNF from SY - 返回三个值: F, J, Y
    cnf = get_sy_compartments()
    f_cnf, j_cnf, y_cnf = (cnf if cnf else (0, 0, 0))
    compartment_total = (f_cnf or 0) + (j_cnf or 0) + (y_cnf or 0)
    ratio = None
    if compartment_total > 0:
        ratio = round((total_accepted / compartment_total) * 100)
    return {
        'flight_number': flight_number,
        'flight_date': flight_date,
        'total_accepted': int(total_accepted or 0),
        'infant_count': int(infant_count or 0),
        'accepted_first': int(accepted_first or 0),
        'accepted_business': int(accepted_business or 0),
        'accepted_economy': int(accepted_economy or 0),
        'id_c': int(id_c or 0),
        'id_y': int(id_y or 0),
        'noshow_f': int(noshow_f or 0),
        'noshow_c': int(noshow_c or 0),
        'noshow_y': int(noshow_y or 0),
        'inad_total': int(inad_total or 0),
        'f_cnf': int(f_cnf or 0),
        'j_cnf': int(j_cnf or 0),
        'y_cnf': int(y_cnf or 0),
        'ratio': ratio,
    }


def build_summary_message():
    """构建摘要信息，只显示非零的部分
    Args:
        summary: 包含统计数据的字典
    Returns:
        str: 格式化的摘要信息
    """
    summary = get_home_summary()
    lines = []
    # 标题行 - 始终显示
    title = f"{summary['flight_number']} / {summary['flight_date']}"
    lines.append(title)
    # 总数行 - 始终显示
    total_line = f"TOTAL {summary['total_accepted']} + {summary['infant_count']} INF"
    lines.append(total_line)
    # 舱位分布 - 只显示非零的舱位
    class_parts = []
    if summary.get('accepted_first', 0) > 0:
        class_parts.append(f"F_{summary['accepted_first']}")
    if summary.get('accepted_business', 0) > 0:
        class_parts.append(f"J_{summary['accepted_business']}")
    if summary.get('accepted_economy', 0) > 0:
        class_parts.append(f"Y_{summary['accepted_economy']}")
    if class_parts:
        lines.append(f"ACCEPTED PAX: {" / ".join(class_parts)}")
    # 比率 - 始终显示
    ratio_display = f"{summary['ratio']}%" if summary['ratio'] is not None else "N/A"
    lines.append(f"RATIO: {ratio_display}")
    # ID员工 - 只显示非零的
    id_parts = []
    if summary.get('id_c', 0) > 0:
        id_parts.append(f"ID_J: {summary['id_c']}")
    if summary.get('id_y', 0) > 0:
        id_parts.append(f"ID_Y: {summary['id_y']}")
    if id_parts:
        lines.append("  ".join(id_parts))
    else:
        lines.append("ID: N/A")
    # NOSHOW - 只显示非零的
    noshow_parts = []
    if summary.get('noshow_f', 0) > 0:
        noshow_parts.append(f"F_{summary['noshow_f']}")
    if summary.get('noshow_c', 0) > 0:
        noshow_parts.append(f"J_{summary['noshow_c']}")
    if summary.get('noshow_y', 0) > 0:
        noshow_parts.append(f"Y_{summary['noshow_y']}")
    if noshow_parts:
        lines.append(f"NO_SHOW: {' / '.join(noshow_parts)}")
    else:
        lines.append("NO_SHOW: N/A")
    # INAD
    lines.append(f"INAD: {summary['inad_total']}")
    return "\n".join(lines)