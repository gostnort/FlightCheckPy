#!/usr/bin/env python3
"""
Home metrics helper for the FlightCheckPy UI.

Responsibilities:
- Create lightweight SQLite views for live-updating summary counts
- Parse SY command text to extract compartment configuration (CNF/JxYy)
- Provide a single function returning the values needed by the home page

All SQL is defensive and will auto-create views if missing.
"""

import re
import sqlite3
from typing import Dict, Optional, Tuple
from ui.common import get_hbpr_database_client
from ui.components.main_stats import get_missing_boarding_numbers


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


def _parse_cnf_from_text(text: str) -> Optional[Tuple[int, int, int]]:
    """Extract CNF compartment numbers from SY command text.
    Returns a tuple (f, j, y) where f=0 if not present.
    支持的格式:
    - CNF/J36Y356 → (0, 36, 356)
    - CNF/F8J42Y261 → (8, 42, 261)
    使用单一正则表达式匹配2或3个舱位数字
    """
    if not text:
        return None
    # 匹配 CNF/ 后跟 2 或 3 个 字母+数字 组合
    # 捕获3个数字组，第3个可选
    match = re.search(r'CNF\s*/?\s*[A-Z]\s*(\d+)\s*[A-Z]\s*(\d+)\s*(?:[A-Z]\s*(\d+))?', text)
    if match:
        groups = match.groups()
        if groups[2] is None:
            # 只有2个舱位 (J, Y)，F设为0
            return (0, int(groups[0]), int(groups[1]))
        else:
            # 有3个舱位 (F, J, Y)
            return (int(groups[0]), int(groups[1]), int(groups[2]))
    return None


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
    for text in (content or "", command_full or ""):
        result = _parse_cnf_from_text(text)
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


def get_debug_data() -> Dict[str, object]:
    """返回用于手动验证统计数据的调试数据
    注意：ID员工仅存在于C和Y舱，不存在于F舱
    """
    conn = _get_conn()
    cur = conn.cursor()
    debug_data = {}
    # 按舱位获取总数 - 使用COUNT(DISTINCT)保持一致性
    cur.execute("""
        SELECT class, COUNT(DISTINCT hbnb_number) as total_count,
               SUM(CASE WHEN boarding_number IS NOT NULL AND boarding_number > 0 THEN 1 ELSE 0 END) as with_bn,
               SUM(CASE WHEN boarding_number IS NULL OR boarding_number = 0 THEN 1 ELSE 0 END) as without_bn
        FROM hbpr_full_records 
        GROUP BY class
    """)
    debug_data['class_breakdown'] = cur.fetchall()
    # 获取XRES计数
    cur.execute("""
        SELECT class, COUNT(DISTINCT hbnb_number) as xres_count
        FROM hbpr_full_records 
        WHERE INSTR(','||IFNULL(properties,'')||',', ',XRES') > 0
        GROUP BY class
    """)
    debug_data['xres_counts'] = cur.fetchall()
    # 获取ID员工计数 (SA, PAD-2, PAD-SA) - 仅C和Y舱，不含F舱
    cur.execute("""
        SELECT class, COUNT(DISTINCT hbnb_number) as id_staff_count
        FROM hbpr_full_records 
        WHERE class IN ('C', 'Y')
          AND (INSTR(','||IFNULL(properties,'')||',', ',SA') > 0
           OR INSTR(','||IFNULL(properties,'')||',', ',PAD-2') > 0
           OR INSTR(','||IFNULL(properties,'')||',', ',PAD-SA') > 0)
        GROUP BY class
    """)
    debug_data['id_staff_counts'] = cur.fetchall()
    # 获取空属性计数
    cur.execute("""
        SELECT class, COUNT(DISTINCT hbnb_number) as empty_props_count
        FROM hbpr_full_records 
        WHERE LENGTH(TRIM(IFNULL(properties,''))) = 0
        GROUP BY class
    """)
    debug_data['empty_properties'] = cur.fetchall()
    # 获取每个类别的样本记录
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
        WHERE class IN ('C', 'Y')
          AND (INSTR(','||IFNULL(properties,'')||',', ',SA') > 0
           OR INSTR(','||IFNULL(properties,'')||',', ',PAD-2') > 0
           OR INSTR(','||IFNULL(properties,'')||',', ',PAD-SA') > 0)
        LIMIT 5
    """)
    debug_data['id_staff_samples'] = cur.fetchall()
    cur.execute("""
        SELECT hbnb_number, class, boarding_number, properties
        FROM hbpr_full_records 
        WHERE (boarding_number IS NULL OR boarding_number = 0)
          AND INSTR(','||IFNULL(properties,'')||',', ',XRES') = 0
          AND INSTR(','||IFNULL(properties,'')||',', ',SA') = 0
          AND INSTR(','||IFNULL(properties,'')||',', ',PAD-2') = 0
          AND INSTR(','||IFNULL(properties,'')||',', ',PAD-SA') = 0
          AND LENGTH(TRIM(IFNULL(properties,''))) > 0
        LIMIT 5
    """)
    debug_data['noshow_samples'] = cur.fetchall()
    conn.close()
    return debug_data


def get_debug_summary() -> str:
    """Return a formatted debug summary string for manual verification"""
    try:
        debug_data = get_debug_data()
        summary = []
        summary.append("🔍 Debug Data for Manual Verification")
        summary.append("")
        # 添加deleted passengers和missing boarding numbers的完整信息
        try:
            # 获取deleted passengers完整信息
            db = get_hbpr_database_client()
            all_stats = db.get_all_statistics()
            deleted_stats = all_stats.get('deleted_passengers_stats', {})
            if deleted_stats and deleted_stats.get('total_deleted', 0) > 0:
                summary.append("**🗑️ Deleted Passengers (Complete List):**")
                summary.append(f"- Total Deleted: {deleted_stats.get('total_deleted', 0)}")
                xres_nums = deleted_stats.get('xres_boarding_numbers', [])
                non_xres_nums = deleted_stats.get('original_boarding_numbers', [])
                if xres_nums:
                    summary.append(f"- XRES Deleted BN: {', '.join(map(str, sorted(xres_nums)))}")
                if non_xres_nums:
                    summary.append(f"- Non-XRES Deleted BN: {', '.join(map(str, sorted(non_xres_nums)))}")
                all_deleted = sorted(xres_nums + non_xres_nums)
                if all_deleted:
                    summary.append(f"- All Deleted BN: {', '.join(map(str, all_deleted))}")
                summary.append("")
            # 获取missing boarding numbers完整信息
            # An internal class to wrap the database object
            class DBWrapper:
                def __init__(self, real_db):
                    self.db_file = real_db.db_file
                    self._real_db = real_db
                def find_database(self):
                    pass
                def get_all_statistics(self):
                    return self._real_db.get_all_statistics()
            # Back to try block
            wrapped_db = DBWrapper(db)
            missing_numbers = get_missing_boarding_numbers(wrapped_db)
            if missing_numbers:
                summary.append("**🔢 Missing Boarding Numbers (Complete List):**")
                summary.append(f"- Total Missing: {len(missing_numbers)}")
                summary.append(f"- Missing BN: {', '.join(map(str, missing_numbers))}")
                summary.append("")
        except Exception as e:
            summary.append(f"**Error getting deleted/missing data: {str(e)}**")
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
        # ID staff counts  
        summary.append("")
        summary.append("**ID Staff Counts (SA, PAD-2, PAD-SA):**")
        for row in debug_data['id_staff_counts']:
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
        summary.append("**ID Staff Sample Records:**")
        for row in debug_data['id_staff_samples']:
            summary.append(f"- HBNB {row[0]}, Class {row[1]}, BN {row[2]}, Props: {row[3]}")
        summary.append("")
        summary.append("**NOSHOW Sample Records:**")
        for row in debug_data['noshow_samples']:
            summary.append(f"- HBNB {row[0]}, Class {row[1]}, BN {row[2]}, Props: {row[3]}")
        return "\n".join(summary)
    except Exception as e:
        return f"Error getting debug data: {str(e)}"


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