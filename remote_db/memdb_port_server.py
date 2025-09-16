#!/usr/bin/env python3
"""
Per-port in-memory SQLite HTTP server

- Loads a SQLite file into an in-memory database
- Exposes minimal HTTP endpoints for query/exec/save/backup/switch
- Intended for LAN-only use; one server per user/port
"""

import argparse
import json
import os
import sqlite3
import threading
from datetime import datetime
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse


# 仅中文注释：内存数据库与源文件路径
_conn = None
_src_file_path = None
_lock = threading.Lock()


def _ensure_pragmas(conn: sqlite3.Connection) -> None:
    """Set sane PRAGMAs on the connection."""
    try:
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA busy_timeout = 30000")
    except Exception:
        pass


def _load_db_into_memory(file_path: str) -> None:
    """Load a SQLite file into a new in-memory database and swap it in atomically."""
    global _conn, _src_file_path
    new_conn = sqlite3.connect(":memory:", check_same_thread=False)
    _ensure_pragmas(new_conn)
    with sqlite3.connect(file_path) as fconn:
        fconn.backup(new_conn)
    with _lock:
        old = _conn
        _conn = new_conn
        _src_file_path = file_path
        if old:
            try:
                old.close()
            except Exception:
                pass


def _backup_memory_db() -> str:
    """Create a timestamped backup of the current in-memory DB to databases/backups."""
    if not _conn:
        return ""
    base = os.path.splitext(os.path.basename(_src_file_path or "database"))[0]
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    bdir = os.path.join("databases", "backups")
    os.makedirs(bdir, exist_ok=True)
    bpath = os.path.join(bdir, f"{base}_backup_{ts}.db")
    with _lock:
        with sqlite3.connect(bpath, check_same_thread=False) as bconn:
            _conn.backup(bconn)
    return bpath


def _save_to_source() -> None:
    """Persist the in-memory DB to its source file."""
    if not _conn or not _src_file_path:
        return
    with _lock:
        with sqlite3.connect(_src_file_path, check_same_thread=False) as fconn:
            _conn.backup(fconn)


def _list_db_files() -> list:
    files = []
    if os.path.exists("databases"):
        for name in os.listdir("databases"):
            if name.lower().endswith(".db"):
                files.append(os.path.join("databases", name))
    return sorted(files, key=lambda p: os.path.getctime(p), reverse=True)


class Handler(BaseHTTPRequestHandler):
    def _send(self, code: int, body: dict) -> None:
        data = json.dumps(body).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, format, *args):
        # Quiet server logs
        return

    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/health":
            return self._send(200, {"ok": True, "db": os.path.basename(_src_file_path) if _src_file_path else None})
        if path == "/databases/list":
            return self._send(200, {"files": _list_db_files()})
        return self._send(404, {"error": "not_found"})

    def do_POST(self):
        path = urlparse(self.path).path
        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length) if length > 0 else b"{}"
        try:
            body = json.loads(raw.decode("utf-8"))
        except Exception:
            body = {}

        try:
            if path == "/database/load":
                file_path = body.get("path")
                if not file_path or not os.path.exists(file_path):
                    return self._send(400, {"error": "invalid_path"})
                if _conn:
                    _backup_memory_db()
                _load_db_into_memory(file_path)
                return self._send(200, {"ok": True, "db_name": os.path.basename(file_path)})

            if path == "/database/backup":
                b = _backup_memory_db()
                return self._send(200, {"path": b})

            if path == "/database/save":
                _save_to_source()
                return self._send(200, {"ok": True})

            if path == "/query":
                sql = body.get("sql") or ""
                params = body.get("params") or []
                with _lock:
                    cur = _conn.cursor()
                    cur.execute(sql, params)
                    rows = cur.fetchall()
                    cols = [d[0] for d in cur.description] if cur.description else []
                return self._send(200, {"columns": cols, "rows": rows})

            if path == "/exec":
                sql = body.get("sql") or ""
                params = body.get("params") or []
                with _lock:
                    cur = _conn.cursor()
                    cur.execute(sql, params)
                    rc = cur.rowcount
                    _conn.commit()
                return self._send(200, {"rowcount": rc})

            return self._send(404, {"error": "not_found"})
        except Exception as e:
            return self._send(500, {"error": str(e)})


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, required=True)
    args = parser.parse_args()
    httpd = HTTPServer((args.host, args.port), Handler)
    print(f"memdb server listening on {args.host}:{args.port}")
    httpd.serve_forever()


if __name__ == "__main__":
    main()


