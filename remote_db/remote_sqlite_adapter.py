#!/usr/bin/env python3
from typing import Any, List, Optional, Tuple
from .db_port_client import DbPortClient


class RemoteCursor:
    """
    Minimal DB-API–like cursor adapter that proxies to the HTTP DB server.
    仅中文注释：兼容execute/fetchall/description接口
    """
    def __init__(self, client: DbPortClient):
        self._client = client
        self.description: Optional[List[Tuple[str]]] = None
        self._last_rows: List[Tuple[Any, ...]] = []

    def execute(self, sql: str, params: Optional[List[Any]] = None):
        sql_trim = (sql or "").strip().lower()
        if sql_trim.startswith("select") or sql_trim.startswith("pragma"):
            res = self._client.query(sql, params or [])
            cols = res.get("columns", [])
            self.description = [(c,) for c in cols] if cols else None
            self._last_rows = res.get("rows", [])
        else:
            # DDL/INSERT/UPDATE/DELETE
            self._client.exec(sql, params or [])
            self.description = None
            self._last_rows = []
        return self

    def fetchall(self):
        return self._last_rows


class RemoteSqliteConnection:
    """
    Minimal connection adapter used by code that expects sqlite3.Connection.
    Methods: cursor(), execute(), commit(), close() (no-op)
    """
    def __init__(self, client: DbPortClient):
        self._client = client

    def cursor(self) -> RemoteCursor:
        return RemoteCursor(self._client)

    def execute(self, sql: str, params: Optional[List[Any]] = None):
        cur = self.cursor()
        return cur.execute(sql, params or [])

    def commit(self):
        # No explicit commit endpoint needed; server commits on exec
        return None

    def close(self):
        # Shared remote connection; no-op for compatibility
        return None


