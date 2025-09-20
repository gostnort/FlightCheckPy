#!/usr/bin/env python3
from typing import Any, Dict, List, Optional
from .db_port_client import DbPortClient
from .remote_sqlite_adapter import RemoteSqliteConnection


class HbprDatabaseClient:
    """
    A high-level client for interacting with the HBPR (Flight Check) database
    via the remote database server. This class provides a simplified interface for
    common database operations, mirroring the API of a local database processor
    (likely `scripts.hbpr_info_processor.HbprDatabase`). It uses an instance of
    `DbPortClient` to send commands to the `MemDbPortServer`.

    This class also provides a connection object that adapts the remote HTTP-based
    database for use with standard Python DB-API clients.
    """
    def __init__(self, client: DbPortClient):
        self._client = client
        self._conn = RemoteSqliteConnection(client)

    def get_connection(self):
        """Returns a DB-API 2 compatible connection object for the remote database."""
        return self._conn

    # This class is a minimal implementation, primarily providing generic helpers.
    # More specific methods mirroring `HbprDatabase` can be added here if needed.

    # Convenience generic helpers
    def query_one(self, sql: str, params: Optional[List[Any]] = None) -> Optional[List[Any]]:
        """
        Executes a query and returns the first row of the result, or None if no rows are found.
        """
        res = self._client.query(sql, params or [])
        rows = res.get("rows", [])
        return rows[0] if rows else None

    def query_all(self, sql: str, params: Optional[List[Any]] = None) -> List[List[Any]]:
        """Executes a query and returns all rows of the result."""
        res = self._client.query(sql, params or [])
        return res.get("rows", [])

    def exec(self, sql: str, params: Optional[List[Any]] = None) -> int:
        """
        Executes a SQL statement (INSERT, UPDATE, DELETE) and returns the number of
        affected rows.
        """
        res = self._client.exec(sql, params or [])
        return int(res.get("rowcount", 0))


