#!/usr/bin/env python3
from typing import Any, List, Optional, Tuple
from .db_port_client import DbPortClient


class RemoteCursor:
    """
    A minimal adapter that mimics the behavior of a standard Python DB-API cursor
    (like `sqlite3.Cursor`). It translates cursor methods into HTTP requests to
    the remote database server via a `DbPortClient` instance. This allows code
    written for the standard DB-API to work with the remote database.

    This cursor is compatible with `execute()`, `fetchall()`, and the `description` attribute.
    """
    def __init__(self, client: DbPortClient):
        self._client = client
        self.description: Optional[List[Tuple[str]]] = None
        self._last_rows: List[Tuple[Any, ...]] = []
        self._fetch_idx = 0

    def execute(self, sql: str, params: Optional[Tuple[Any, ...]] = None):
        """
        Executes a SQL statement.
        If the statement is a query (SELECT, PRAGMA), it calls the '/query' endpoint
        and stores the results.
        If it's a DDL or DML statement (CREATE, INSERT, UPDATE, DELETE), it calls
        the '/exec' endpoint.
        """
        self._fetch_idx = 0  # Reset fetch index on new execution
        sql_trim = (sql or "").strip().lower()

        # Ensure params are a list for JSON serialization, even if a tuple is passed.
        params_list = list(params) if params is not None else []

        if sql_trim.startswith("select") or sql_trim.startswith("pragma"):
            res = self._client.query(sql, params_list)
            cols = res.get("columns", [])
            self.description = [(c,) for c in cols] if cols else None
            self._last_rows = res.get("rows", [])
        else:
            # For DDL/INSERT/UPDATE/DELETE operations.
            self._client.exec(sql, params_list)
            self.description = None
            self._last_rows = []
        return self

    def fetchone(self):
        """Returns the next row from the result set, or None."""
        if self._fetch_idx < len(self._last_rows):
            row = self._last_rows[self._fetch_idx]
            self._fetch_idx += 1
            return row
        return None

    def fetchall(self):
        """
        Returns all rows from the result set, mirroring sqlite3.Cursor's behavior
        by returning all rows from the initial query regardless of prior
        fetchone() calls.
        """
        return self._last_rows


class RemoteSqliteConnection:
    """
    A minimal adapter that mimics a standard Python DB-API connection object
    (like `sqlite3.Connection`). It allows existing code that expects a standard
    database connection to use the remote database server without modification.

    It provides `cursor()`, `execute()`, `commit()`, and `close()` methods for
    compatibility.
    """
    def __init__(self, client: DbPortClient):
        self._client = client

    def cursor(self) -> RemoteCursor:
        """Returns a `RemoteCursor` instance for this connection."""
        return RemoteCursor(self._client)

    def execute(self, sql: str, params: Optional[List[Any]] = None):
        """A convenience method to create a cursor and execute a statement."""
        cur = self.cursor()
        return cur.execute(sql, params or [])

    def commit(self):
        """
        A no-op method for DB-API compatibility. The remote server commits
        automatically after each 'exec' operation, so no explicit commit is needed.
        """
        return None

    def close(self):
        """
        A no-op method for DB-API compatibility. The lifecycle of the remote
        connection is managed by the server, not the client.
        """
        return None


