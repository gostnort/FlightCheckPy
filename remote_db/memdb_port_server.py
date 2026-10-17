#!/usr/bin/env python3
"""
Per-port in-memory SQLite HTTP server.

Disk reads and writes run outside the SQLite lock. Encrypted files use the
AES-256-GCM container in scripts/crypto_engine.py. Query and exec still use
the single active connection.
"""

import argparse
import json
import queue
import sqlite3
import sys
import threading
import time
from datetime import datetime
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import unquote, urlparse

from cryptography.exceptions import InvalidTag

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.crypto_engine import (
    CryptoFormatError,
    decrypt_sqlite_payload,
    encrypt_sqlite_payload,
    encrypted_header_ok,
    resolve_master_key,
)

_conn = None
_src_file_path = None
_lock = threading.Lock()
_current_username = None
_login_time = 0.0
_master_key = None

_write_queue: queue.Queue = queue.Queue()
_pending_condition = threading.Condition()
_pending_writes = 0
_pending_by_path: dict[str, int] = {}
_last_disk_error = None
_writer_thread = None
_writer_guard = threading.Lock()

REQUIRED_TABLES = ("hbpr_full_records", "hbpr_simple_records")


def _ensure_pragmas(conn: sqlite3.Connection) -> None:
    """Set sane PRAGMAs on the connection."""
    try:
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA busy_timeout = 30000")
    except Exception:
        pass


def _is_encrypted_path(path: Path) -> bool:
    return path.name.lower().endswith(".db.enc")


def _normalized_path(file_path: str) -> str:
    return str(Path(file_path).resolve())


def _require_master_key() -> str:
    global _master_key
    if _master_key:
        return _master_key
    key = resolve_master_key()
    if not key:
        raise PermissionError("KEY_UNAVAILABLE")
    _master_key = key
    return key


def _connection_has_required_tables(conn: sqlite3.Connection) -> bool:
    for table in REQUIRED_TABLES:
        row = conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
            (table,),
        ).fetchone()
        if row is None:
            return False
    return True


def _validate_database_schema(file_path: str) -> bool:
    """Accept an encrypted file from its header, or a plain file from its tables.

    Listing calls this for every database on each sidebar refresh. Encrypted
    files are not decrypted here.
    """
    path = Path(file_path)
    try:
        if _is_encrypted_path(path):
            return encrypted_header_ok(path)
        with sqlite3.connect(path) as conn:
            return _connection_has_required_tables(conn)
    except Exception:
        return False


def _ensure_writer() -> None:
    global _writer_thread
    with _writer_guard:
        if _writer_thread and _writer_thread.is_alive():
            return
        _writer_thread = threading.Thread(
            target=_disk_writer_loop,
            name="db-disk-writer",
            daemon=True,
        )
        _writer_thread.start()


def _enqueue_disk_write(path_key: str, sqlite_bytes: bytes) -> int:
    global _pending_writes
    _ensure_writer()
    with _pending_condition:
        _pending_writes += 1
        _pending_by_path[path_key] = _pending_by_path.get(path_key, 0) + 1
        pending = _pending_writes
    _write_queue.put((path_key, sqlite_bytes))
    return pending


def _disk_writer_loop() -> None:
    global _pending_writes, _last_disk_error
    while True:
        path_key, sqlite_bytes = _write_queue.get()
        try:
            _write_sqlite_bytes(Path(path_key), sqlite_bytes)
            with _pending_condition:
                _last_disk_error = None
        except Exception as exc:
            with _pending_condition:
                _last_disk_error = str(exc)
        finally:
            with _pending_condition:
                _pending_writes = max(0, _pending_writes - 1)
                remaining = _pending_by_path.get(path_key, 0) - 1
                if remaining <= 0:
                    _pending_by_path.pop(path_key, None)
                else:
                    _pending_by_path[path_key] = remaining
                _pending_condition.notify_all()
            _write_queue.task_done()


def _wait_for_path(path_key: str) -> None:
    with _pending_condition:
        while _pending_by_path.get(path_key, 0) > 0:
            _pending_condition.wait()


def _wait_all_disk_writes() -> None:
    _write_queue.join()


def _write_sqlite_bytes(path: Path, sqlite_bytes: bytes) -> None:
    if _is_encrypted_path(path):
        payload = encrypt_sqlite_payload(sqlite_bytes, _require_master_key())
    else:
        payload = sqlite_bytes
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = Path(str(path) + ".tmp")
    temporary.write_bytes(payload)
    temporary.replace(path)


def _read_sqlite_bytes(path: Path) -> bytes:
    raw = path.read_bytes()
    if not _is_encrypted_path(path):
        return raw
    return decrypt_sqlite_payload(raw, _require_master_key())


def _snapshot_active_db() -> int:
    """Copy the active memory database and queue the disk write.

    Serialization holds the SQLite lock. Encryption and file replacement do not.
    """
    with _lock:
        if _conn is None or not _src_file_path:
            return _pending_writes
        sqlite_bytes = _conn.serialize()
        path_key = _src_file_path
    return _enqueue_disk_write(path_key, sqlite_bytes)


def _load_db_into_memory(file_path: str, preserve_current: bool = True) -> None:
    """Read one database outside the lock, then swap the active connection.

    Switching to a different file queues the current memory image first.
    Reloading the same file reads the disk image after queued writes finish.
    """
    global _conn, _src_file_path

    path = Path(file_path).resolve()
    if preserve_current and _src_file_path:
        _snapshot_active_db()
    _wait_for_path(str(path))
    if not path.is_file():
        raise ValueError("source file not found")

    sqlite_bytes = _read_sqlite_bytes(path)
    new_conn = sqlite3.connect(":memory:", check_same_thread=False)
    try:
        _ensure_pragmas(new_conn)
        new_conn.deserialize(sqlite_bytes)
        if not _connection_has_required_tables(new_conn):
            raise ValueError(
                "Database does not have the expected schema. "
                "Required tables: hbpr_full_records, hbpr_simple_records"
            )
    except Exception:
        new_conn.close()
        raise

    with _lock:
        old = _conn
        _conn = new_conn
        _src_file_path = str(path)
    if old is not None:
        try:
            old.close()
        except Exception:
            pass


def _backup_stem(path: Path) -> str:
    name = path.name
    lower = name.lower()
    if lower.endswith(".db.enc"):
        return name[: -len(".db.enc")]
    if lower.endswith(".db"):
        return name[: -len(".db")]
    return path.stem


def _backup_memory_db() -> str:
    """Write a timestamped backup. Encrypted sources stay encrypted."""
    with _lock:
        if _conn is None or not _src_file_path:
            return ""
        sqlite_bytes = _conn.serialize()
        source = Path(_src_file_path)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    extension = ".db.enc" if _is_encrypted_path(source) else ".db"
    backup_dir = Path("databases") / "backups"
    backup_dir.mkdir(parents=True, exist_ok=True)
    backup_path = backup_dir / f"{_backup_stem(source)}_backup_{stamp}{extension}"
    _write_sqlite_bytes(backup_path, sqlite_bytes)
    return str(backup_path)


def _save_to_source() -> int:
    """Queue the active database for disk write and return the pending count."""
    return _snapshot_active_db()


def _list_db_files(directory: str = None) -> list:
    """List plain and encrypted databases, newest creation or modification first."""
    target = Path(directory) if directory else Path("databases")
    if not target.is_dir():
        return []
    files = []
    for entry in target.iterdir():
        if not entry.is_file():
            continue
        lower = entry.name.lower()
        if lower.endswith(".db.enc") or lower.endswith(".db"):
            files.append(entry)
    files.sort(key=lambda entry: max(entry.stat().st_mtime, entry.stat().st_ctime), reverse=True)
    return [str(entry) for entry in files]


def _health_body() -> dict:
    with _pending_condition:
        pending = _pending_writes
        disk_error = _last_disk_error
    return {
        "ok": True,
        "db": Path(_src_file_path).name if _src_file_path else None,
        "disk_write_pending": pending,
        "last_disk_error": disk_error,
    }


class Handler(BaseHTTPRequestHandler):
    """HTTP handlers for the in-memory database server."""

    def _send(self, code: int, body: dict) -> None:
        data = json.dumps(body).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, format, *args):
        return

    def _send_known_error(self, exc: Exception):
        if isinstance(exc, CryptoFormatError):
            return self._send(400, {"ok": False, "error": exc.code})
        if isinstance(exc, InvalidTag):
            return self._send(403, {"ok": False, "error": "AUTHENTICATION_FAILED"})
        if isinstance(exc, PermissionError):
            return self._send(500, {"ok": False, "error": "KEY_UNAVAILABLE"})
        if isinstance(exc, ValueError):
            return self._send(400, {"ok": False, "error": str(exc)})
        return self._send(500, {"ok": False, "error": str(exc)})

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        query_params = dict(part.split("=", 1) for part in parsed.query.split("&") if part)

        if path == "/health":
            return self._send(200, _health_body())
        if path == "/databases/list":
            directory = query_params.get("directory")
            if directory:
                directory = unquote(directory)
            return self._send(200, {"files": _list_db_files(directory)})
        if path == "/auth/status":
            return self._send(200, {
                "logged_in": _current_username is not None,
                "username": _current_username,
                "login_time": _login_time if _current_username else None,
            })
        if path == "/shutdown":
            try:
                _snapshot_active_db()
                _wait_all_disk_writes()
                body = {"ok": True, "message": "Server shutting down"}
                if _last_disk_error:
                    body["last_disk_error"] = _last_disk_error
                self._send(200, body)
                threading.Thread(target=self.server.shutdown, daemon=True).start()
                return
            except Exception as exc:
                return self._send_known_error(exc)
        return self._send(404, {"error": "not_found"})

    def do_POST(self):
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
                username = body.get("username")
                if not username:
                    return self._send(400, {"error": "missing_username"})
                _current_username = username
                _login_time = time.time()
                return self._send(200, {"ok": True, "username": username, "login_time": _login_time})

            if path == "/auth/logout":
                _current_username = None
                return self._send(200, {"ok": True})

            if path == "/database/validate":
                file_path = body.get("path")
                if not file_path or not Path(file_path).exists():
                    return self._send(400, {"valid": False, "error": "invalid_path"})
                return self._send(200, {"valid": _validate_database_schema(file_path)})

            if path == "/database/load":
                file_path = body.get("path")
                if not file_path or not Path(file_path).exists():
                    return self._send(400, {"error": "invalid_path"})
                _load_db_into_memory(file_path)
                return self._send(200, {"ok": True, "db_name": Path(file_path).name})

            if path == "/database/backup":
                backup_path = _backup_memory_db()
                return self._send(200, {"path": backup_path})

            if path == "/database/save":
                pending = _save_to_source()
                return self._send(200, {"ok": True, "pending": pending})

            if path == "/database/reload":
                if not _src_file_path:
                    return self._send(400, {"error": "no_database_loaded"})
                if not Path(_src_file_path).exists():
                    return self._send(400, {"error": "source_file_not_found"})
                _load_db_into_memory(_src_file_path, preserve_current=False)
                return self._send(200, {"ok": True, "db_name": Path(_src_file_path).name})

            if path == "/query":
                sql = body.get("sql") or ""
                params = body.get("params") or []
                with _lock:
                    cur = _conn.cursor()
                    cur.execute(sql, params)
                    rows = cur.fetchall()
                    cols = [item[0] for item in cur.description] if cur.description else []
                return self._send(200, {"columns": cols, "rows": rows})

            if path == "/exec":
                sql = body.get("sql") or ""
                params = body.get("params") or []
                with _lock:
                    cur = _conn.cursor()
                    cur.execute(sql, params)
                    rowcount = cur.rowcount
                    _conn.commit()
                return self._send(200, {"rowcount": rowcount})

            return self._send(404, {"error": "not_found"})
        except Exception as exc:
            return self._send_known_error(exc)


def main():
    """Start the HTTP server. The default bind address is loopback only."""
    _ensure_writer()
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, required=True)
    args = parser.parse_args()
    httpd = HTTPServer((args.host, args.port), Handler)
    print(f"memdb server listening on {args.host}:{args.port}")
    httpd.serve_forever()


if __name__ == "__main__":
    main()
