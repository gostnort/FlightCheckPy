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
import time
from datetime import datetime
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse, unquote


# Global variables to hold the in-memory database connection,
# the path to the source file, and a thread lock for safe concurrent access.
_conn = None
_src_file_path = None
_lock = threading.Lock()

# 简化的用户名登录状态（无需IP绑定、无超时）
_current_username = None
_login_time = 0.0


def _ensure_pragmas(conn: sqlite3.Connection) -> None:
    """Set sane PRAGMAs on the connection."""
    try:
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA busy_timeout = 30000")
    except Exception:
        pass


def _validate_database_schema(file_path: str) -> bool:
    """
    Validates that the database has the expected schema (required tables).
    Returns True if the database has the expected structure, False otherwise.
    """
    try:
        with sqlite3.connect(file_path) as conn:
            cursor = conn.cursor()
            # Check for required tables
            required_tables = ['hbpr_full_records', 'hbpr_simple_records']
            for table in required_tables:
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,))
                if not cursor.fetchone():
                    return False
            return True
    except Exception:
        return False


def _load_db_into_memory(file_path: str) -> None:
    """
    Loads a SQLite database file from the given path into a new in-memory database.
    It then atomically swaps the new connection for the global one.
    If a database is already loaded, it's closed after the new one is ready.
    """
    global _conn, _src_file_path

    # Validate database schema before loading
    if not _validate_database_schema(file_path):
        raise ValueError(f"Database {file_path} does not have the expected schema. Required tables: hbpr_full_records, hbpr_simple_records, commands")

    # Create a new in-memory SQLite database connection.
    new_conn = sqlite3.connect(":memory:", check_same_thread=False)
    _ensure_pragmas(new_conn)
    # Connect to the source file on disk and back it up to the new in-memory database.
    with sqlite3.connect(file_path) as fconn:
        fconn.backup(new_conn)
    # Use a lock to safely swap the global connection to the new in-memory database.
    with _lock:
        old = _conn
        _conn = new_conn
        _src_file_path = file_path
        if old:
            try:
                # Close the old connection if it exists.
                old.close()
            except Exception:
                pass


def _backup_memory_db() -> str:
    """
    Creates a timestamped backup of the current in-memory database.
    The backup is saved in the 'databases/backups' directory.
    The backup filename includes the original database name and a timestamp.
    """
    if not _conn:
        return ""
    base = os.path.splitext(os.path.basename(_src_file_path or "database"))[0]
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    bdir = os.path.join("databases", "backups")
    os.makedirs(bdir, exist_ok=True)
    bpath = os.path.join(bdir, f"{base}_backup_{ts}.db")
    # Lock to prevent other operations on the DB while backing up.
    with _lock:
        with sqlite3.connect(bpath, check_same_thread=False) as bconn:
            _conn.backup(bconn)
    return bpath


def _save_to_source() -> None:
    """
    Persists the in-memory database back to its original source file on disk.
    This overwrites the source file with the current state of the in-memory database.
    """
    if not _conn or not _src_file_path:
        return
    # Lock to ensure data integrity during the save operation.
    with _lock:
        with sqlite3.connect(_src_file_path, check_same_thread=False) as fconn:
            _conn.backup(fconn)


def _list_db_files(directory: str = None) -> list:
    """
    Lists all '.db' files in the specified directory.
    If no directory is provided, defaults to 'databases' directory.
    Returns a list of file paths, sorted by creation time (most recent first).
    """
    target_dir = directory if directory else "databases"
    files = []
    if os.path.exists(target_dir):
        for name in os.listdir(target_dir):
            if name.lower().endswith(".db"):
                files.append(os.path.join(target_dir, name))
    return sorted(files, key=lambda p: os.path.getctime(p), reverse=True)


class Handler(BaseHTTPRequestHandler):
    """
    The request handler for the HTTP server.
    It defines how to handle GET and POST requests to various endpoints.
    """
    def _send(self, code: int, body: dict) -> None:
        """Helper function to send a JSON response."""
        data = json.dumps(body).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, format, *args):
        # Overridden to suppress the default server log messages for cleaner output.
        return

    def do_GET(self):
        """Handles GET requests."""
        parsed = urlparse(self.path)
        path = parsed.path
        query_params = dict(q.split('=', 1) for q in parsed.query.split('&') if q)

        if path == "/health":
            # Health check endpoint: returns server status and current database file.
            return self._send(200, {"ok": True, "db": os.path.basename(_src_file_path) if _src_file_path else None})
        if path == "/databases/list":
            # Lists available database files, optionally from a custom directory.
            directory = query_params.get("directory")
            if directory:
                directory = unquote(directory)
            return self._send(200, {"files": _list_db_files(directory)})
        if path == "/auth/status":
            # 获取当前认证状态
            global _current_username, _login_time
            return self._send(200, {
                "logged_in": _current_username is not None,
                "username": _current_username,
                "login_time": _login_time if _current_username else None
            })
        if path == "/shutdown":
            # Shutdown endpoint: saves database and stops the server.
            try:
                if _conn and _src_file_path:
                    _save_to_source()
                self._send(200, {"ok": True, "message": "Server shutting down"})
                # Shutdown the server in a separate thread to allow response to be sent
                threading.Thread(target=lambda: self.server.shutdown(), daemon=True).start()
                return
            except Exception as e:
                return self._send(500, {"error": str(e)})
        return self._send(404, {"error": "not_found"})

    def do_POST(self):
        """Handles POST requests."""
        global _current_username, _login_time
        
        path = urlparse(self.path).path
        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length) if length > 0 else b"{}"
        try:
            body = json.loads(raw.decode("utf-8"))
        except Exception:
            body = {}

        try:
            if path == "/auth/login":
                # 简单的用户名登录（幂等操作）
                username = body.get("username")
                if not username:
                    return self._send(400, {"error": "missing_username"})
                _current_username = username
                _login_time = time.time()
                return self._send(200, {"ok": True, "username": username, "login_time": _login_time})
            
            if path == "/auth/logout":
                # 登出当前用户
                _current_username = None
                return self._send(200, {"ok": True})
            
            if path == "/database/validate":
                # Validates that a database file has the expected schema.
                file_path = body.get("path")
                if not file_path or not os.path.exists(file_path):
                    return self._send(400, {"valid": False, "error": "invalid_path"})
                valid = _validate_database_schema(file_path)
                return self._send(200, {"valid": valid})

            if path == "/database/load":
                # Loads a new database file into memory.
                # If a database is already loaded, it's backed up first.
                file_path = body.get("path")
                if not file_path or not os.path.exists(file_path):
                    return self._send(400, {"error": "invalid_path"})
                if _conn:
                    _backup_memory_db()
                _load_db_into_memory(file_path)
                return self._send(200, {"ok": True, "db_name": os.path.basename(file_path)})

            if path == "/database/backup":
                # Triggers a backup of the current in-memory database.
                b = _backup_memory_db()
                return self._send(200, {"path": b})

            if path == "/database/save":
                # Saves the in-memory database to its source file.
                _save_to_source()
                return self._send(200, {"ok": True})

            if path == "/database/reload":
                # Reloads the current database from disk.
                if not _src_file_path:
                    return self._send(400, {"error": "no_database_loaded"})
                if not os.path.exists(_src_file_path):
                    return self._send(400, {"error": "source_file_not_found"})
                _load_db_into_memory(_src_file_path)
                return self._send(200, {"ok": True, "db_name": os.path.basename(_src_file_path)})

            if path == "/query":
                # Executes a read-only SQL query.
                sql = body.get("sql") or ""
                params = body.get("params") or []
                with _lock:
                    cur = _conn.cursor()
                    cur.execute(sql, params)
                    rows = cur.fetchall()
                    cols = [d[0] for d in cur.description] if cur.description else []
                return self._send(200, {"columns": cols, "rows": rows})

            if path == "/exec":
                # Executes a write (INSERT, UPDATE, DELETE) SQL statement.
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
    """
    Parses command line arguments and starts the HTTP server.
    Requires --port to be specified.
    """
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, required=True)
    args = parser.parse_args()
    httpd = HTTPServer((args.host, args.port), Handler)
    print(f"memdb server listening on {args.host}:{args.port}")
    httpd.serve_forever()


if __name__ == "__main__":
    main()


