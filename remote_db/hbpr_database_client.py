#!/usr/bin/env python3
from typing import Any, Dict, List, Optional
from .db_port_client import DbPortClient
from .remote_sqlite_adapter import RemoteSqliteConnection


class HbprDatabaseClient:
    """
    Thin client mirroring scripts.hbpr_info_processor.HbprDatabase public API,
    executing SQL via the remote DB server.
    """
    def __init__(self, client: DbPortClient):
        self._client = client
        self._conn = RemoteSqliteConnection(client)

    def get_connection(self):
        return self._conn

    # Minimal coverage for code paths relying on HbprDatabase methods
    # More methods can be added as needed; for now, generic query helpers below are sufficient

    # Convenience generic helpers
    def query_one(self, sql: str, params: Optional[List[Any]] = None) -> Optional[List[Any]]:
        res = self._client.query(sql, params or [])
        rows = res.get("rows", [])
        return rows[0] if rows else None

    def query_all(self, sql: str, params: Optional[List[Any]] = None) -> List[List[Any]]:
        res = self._client.query(sql, params or [])
        return res.get("rows", [])

    def exec(self, sql: str, params: Optional[List[Any]] = None) -> int:
        res = self._client.exec(sql, params or [])
        return int(res.get("rowcount", 0))


