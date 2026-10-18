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

_cache_lock = threading.Lock()
_db_cache: dict[str, sqlite3.Connection] = {}
_dirty_paths: set[str] = set()
_schema_cache_lock = threading.Lock()
_schema_cache: dict[str, tuple] = {}
_state_lock = threading.Lock()
_loading_paths: set[str] = set()
_load_errors: dict[str, str] = {}
_desired_active = None
_prewarm_thread = None
_prewarm_guard = threading.Lock()

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


def _resident_paths() -> set:
    """Live in-memory connections. These files are not opened again."""
    with _cache_lock:
        return set(_db_cache)


def _probe_schema(path: Path) -> bool:
    """Check a file once, then close it. A resident database is not probed."""
    if _is_encrypted_path(path):
        return encrypted_header_ok(path)
    uri = path.resolve().as_uri() + "?mode=ro&immutable=1"
    conn = sqlite3.connect(uri, uri=True)
    try:
        return _connection_has_required_tables(conn)
    finally:
        conn.close()


def _validate_database_schema(file_path: str) -> bool:
    """Return whether a database file has the expected tables.

    Results are cached by path, size, and modification time. Files already
    in memory are accepted without opening them.
    """
    path = Path(file_path)
    try:
        key = _normalized_path(file_path)
    except OSError:
        return False
    if key in _resident_paths():
        return True
    try:
        stat = path.stat()
        signature = (stat.st_mtime_ns, stat.st_size)
    except OSError:
        return False
    with _schema_cache_lock:
        cached = _schema_cache.get(key)
        if cached and cached[0] == signature:
            return cached[1]
    try:
        valid = _probe_schema(path)
    except Exception:
        valid = False
    with _schema_cache_lock:
        _schema_cache[key] = (signature, valid)
    return valid


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
    _replace_temp_file(temporary, path)


def _replace_temp_file(temporary: Path, path: Path) -> None:
    """Replace the database file. Retry if Windows still has the old handle."""
    delay = 0.05
    last_error = None
    for _attempt in range(6):
        try:
            temporary.replace(path)
            return
        except PermissionError as exc:
            last_error = exc
            time.sleep(delay)
            delay = min(delay * 2, 0.4)
    if last_error is not None:
        raise last_error


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
    """Point the active database at a resident connection.

    The first read builds a live memory connection and keeps it. Later switches
    only replace the active pointer. A disk reload replaces that one entry.
    """
    global _desired_active

    path_key = _normalized_path(file_path)
    if preserve_current and _src_file_path and _src_file_path != path_key:
        _snapshot_active_db()
    if (not preserve_current) or path_key not in _resident_paths():
        _read_connection_into_cache(path_key, replace=not preserve_current)
    _point_at(path_key)
    with _state_lock:
        _desired_active = path_key


def _point_at(path_key: str, only_if_unset: bool = False) -> None:
    """Switch the active database by pointer. Other connections stay resident."""
    global _conn, _src_file_path
    with _cache_lock:
        cached = _db_cache.get(path_key)
    if cached is None:
        raise ValueError("source file not found")
    with _lock:
        if only_if_unset and _src_file_path is not None:
            return
        _conn = cached
        _src_file_path = path_key


def _read_connection_into_cache(path_key: str, replace: bool = False) -> None:
    """Read a file outside the query lock, then keep the live connection."""
    with _state_lock:
        already = path_key in _loading_paths
        if not already:
            _loading_paths.add(path_key)
    if already:
        deadline = time.time() + 30
        while time.time() < deadline:
            if path_key in _resident_paths():
                return
            with _state_lock:
                if path_key not in _loading_paths:
                    break
            time.sleep(0.05)
        if path_key not in _resident_paths():
            raise ValueError(_load_errors.get(path_key, "load failed"))
        return
    try:
        path = Path(path_key)
        if not path.is_file():
            raise ValueError("source file not found")
        if not replace and path_key in _resident_paths():
            return
        _wait_for_path(path_key)
        sqlite_bytes = _read_sqlite_bytes(path)
        new_conn = _open_memory_connection(sqlite_bytes)
        with _cache_lock:
            old = _db_cache.get(path_key)
            if old is not None and not replace:
                new_conn.close()
                return
            _db_cache[path_key] = new_conn
        if old is not None and replace:
            with _lock:
                if _conn is old:
                    _conn = new_conn
            try:
                old.close()
            except Exception:
                pass
            with _state_lock:
                _dirty_paths.discard(path_key)
    finally:
        with _state_lock:
            _loading_paths.discard(path_key)


def _prewarm_targets() -> list:
    """Keep the globally newest databases in memory.

    Valid files are ordered by max(mtime, ctime), newest first. The first
    preload_count files form the base set. When last_selected_db is valid and
    outside that set, it is inserted at the front so the previous choice is
    activated without dropping a newer database.
    """
    from scripts.config_manager import get_config_value

    try:
        count = int(get_config_value("db_preferences", "preload_count", 5) or 5)
    except (TypeError, ValueError):
        count = 5
    count = max(1, count)
    last_name = Path(get_config_value("db_preferences", "last_selected_db", "") or "").name
    files = [
        _normalized_path(file_path)
        for file_path in _list_db_files()
        if _validate_database_schema(file_path)
    ]
    files.sort(
        key=lambda path_key: max(Path(path_key).stat().st_mtime, Path(path_key).stat().st_ctime),
        reverse=True,
    )
    selected = files[:count]
    if not last_name:
        return selected
    last_path = next((path_key for path_key in files if Path(path_key).name == last_name), None)
    if last_path and last_path not in selected:
        selected.insert(0, last_path)
    return selected


def _prewarm_loop() -> None:
    global _desired_active
    try:
        targets = _prewarm_targets()
    except Exception as exc:
        with _state_lock:
            _load_errors["prewarm"] = str(exc)
        return
    for index, path_key in enumerate(targets):
        try:
            if path_key not in _resident_paths():
                _read_connection_into_cache(path_key)
            if index == 0 and path_key in _resident_paths():
                _point_at(path_key, only_if_unset=True)
                with _state_lock:
                    _desired_active = path_key
        except Exception as exc:
            with _state_lock:
                _load_errors[path_key] = str(exc)


def _start_prewarm() -> None:
    global _prewarm_thread
    with _prewarm_guard:
        if _prewarm_thread and _prewarm_thread.is_alive():
            return
        _prewarm_thread = threading.Thread(
            target=_prewarm_loop,
            name="db-prewarm",
            daemon=True,
        )
        _prewarm_thread.start()


def _request_preload(paths: list, activate: str) -> list:
    """Append the requested databases to the resident set. Nothing is evicted."""
    normalized = []
    for raw_path in paths:
        if not raw_path:
            continue
        path_key = _normalized_path(raw_path)
        if path_key not in normalized:
            normalized.append(path_key)
    activate_key = _normalized_path(activate) if activate else None

    def _work() -> None:
        global _desired_active
        for path_key in normalized:
            try:
                if path_key not in _resident_paths():
                    _read_connection_into_cache(path_key)
            except Exception as exc:
                with _state_lock:
                    _load_errors[path_key] = str(exc)
        if activate_key and activate_key in _resident_paths():
            _point_at(activate_key, only_if_unset=True)
            with _state_lock:
                _desired_active = activate_key

    threading.Thread(target=_work, name="db-preload", daemon=True).start()
    return normalized


def _flush_resident_databases() -> None:
    """Serialize every resident connection before the process exits."""
    _wait_all_disk_writes()
    with _cache_lock:
        connections = list(_db_cache.items())
    with _lock:
        snapshots = [(path_key, conn.serialize()) for path_key, conn in connections]
    for path_key, sqlite_bytes in snapshots:
        _write_sqlite_bytes(Path(path_key), sqlite_bytes)


def _open_memory_connection(sqlite_bytes: bytes) -> sqlite3.Connection:
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
    return new_conn


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


def _describe_databases(directory: str = None) -> list:
    """List databases with validity and whether a memory copy already exists."""
    resident = _resident_paths()
    active = _src_file_path
    described = []
    for file_path in _list_db_files(directory):
        key = _normalized_path(file_path)
        described.append({
            "path": file_path,
            "valid": _validate_database_schema(file_path),
            "resident": key in resident,
            "active": bool(active) and key == active,
        })
    return described


def _health_body() -> dict:
    with _pending_condition:
        pending = _pending_writes
        disk_error = _last_disk_error
    with _state_lock:
        loading = sorted(_loading_paths)
        failed = sorted(_load_errors)
        load_error = _load_errors.get(_desired_active) if _desired_active else None
        if load_error is None and _load_errors:
            load_error = next(iter(_load_errors.values()))
    with _cache_lock:
        resident = sorted(_db_cache)
    return {
        "ok": True,
        "db": Path(_src_file_path).name if _src_file_path else None,
        "db_path": _src_file_path,
        "disk_write_pending": pending,
        "last_disk_error": disk_error,
        "loading": loading,
        "ready": resident,
        "resident": resident,
        "failed": failed,
        "load_error": load_error,
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
            described = _describe_databases(directory)
            return self._send(200, {
                "files": [item["path"] for item in described],
                "databases": described,
            })
        if path == "/auth/status":
            return self._send(200, {
                "logged_in": _current_username is not None,
                "username": _current_username,
                "login_time": _login_time if _current_username else None,
            })
        if path == "/shutdown":
            try:
                _flush_resident_databases()
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

            if path == "/database/preload":
                paths = body.get("paths") or []
                activate = body.get("activate") or (paths[0] if paths else None)
                if not activate:
                    return self._send(400, {"error": "invalid_path"})
                queued = _request_preload(paths, activate)
                return self._send(200, {"ok": True, "queued": queued})

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
                    if _src_file_path:
                        _dirty_paths.add(_src_file_path)
                return self._send(200, {"rowcount": rowcount})

            return self._send(404, {"error": "not_found"})
        except Exception as exc:
            return self._send_known_error(exc)


def main():
    """Start the HTTP server.

    The default bind address is 0.0.0.0, so several users on the LAN can
    connect. The master secret is only the passphrase a user saved. This
    process does not create one.
    """
    _ensure_writer()
    _start_prewarm()
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="0.0.0.0", help="Bind address. Defaults to all interfaces for LAN access.")
    parser.add_argument("--port", type=int, required=True)
    args = parser.parse_args()
    httpd = HTTPServer((args.host, args.port), Handler)
    print(f"memdb server listening on {args.host}:{args.port}")
    httpd.serve_forever()


if __name__ == "__main__":
    main()
