#!/usr/bin/env python3
"""
Core Database Manager (non-UI)

Provides a port-based in-memory DB manager using the remote DB HTTP service.
This module has no Streamlit dependencies and can be used from UI wrappers.
"""

import os
from typing import Optional
from .db_port_client import DbPortClient
from .remote_sqlite_adapter import RemoteSqliteConnection
from .hbpr_database_client import HbprDatabaseClient


class DatabaseManager:
    """
    Manages the connection to the per-user remote in-memory database service.
    This class acts as a central point of control for database operations.
    It is responsible for establishing a connection to the remote server,
    loading databases, and providing access to database clients and connections.
    It is designed to be independent of any UI framework but can fall back to
    using Streamlit session state to find the database server if environment
    variables are not set.
    """
    def __init__(self):
        self._client: Optional[DbPortClient] = None
        self._db_name: Optional[str] = None
        self._file_path: Optional[str] = None

    def _ensure_client(self) -> Optional[DbPortClient]:
        """
        Ensures that a `DbPortClient` is instantiated.
        It retrieves the database host and port from environment variables.
        As a fallback for UI integration (e.g., with Streamlit), it attempts
        to get these values from the session state.
        """
        host = os.environ.get('FCP_DB_HOST')
        port = os.environ.get('FCP_DB_PORT')
        # Fallback to Streamlit session if available at runtime
        if (not host or not port):
            try:
                import streamlit as st  # type: ignore
                host = host or st.session_state.get('db_service_host')
                port = port or st.session_state.get('db_service_port')
            except Exception:
                # This will fail if not in a Streamlit environment, which is fine.
                pass
        if not host or not port:
            return None
        if not self._client:
            self._client = DbPortClient(str(host), int(port))
        return self._client

    def load_database(self, file_path: str) -> bool:
        """
        Loads a database from the given file path into the remote server's memory.
        """
        try:
            if not os.path.exists(file_path):
                return False
            client = self._ensure_client()
            if not client:
                return False
            res = client.load_database(file_path)
            if not res or not res.get('ok'):
                return False
            self._file_path = file_path
            self._db_name = os.path.basename(file_path)
            return True
        except Exception:
            return False

    def get_connection(self) -> Optional[RemoteSqliteConnection]:
        """
        Returns a DB-API 2 compatible connection object for the remote database.
        Useful for libraries that expect a standard database connection.
        """
        client = self._ensure_client()
        if not client:
            return None
        return RemoteSqliteConnection(client)

    def get_database(self) -> Optional[HbprDatabaseClient]:
        """
        Returns a high-level, application-specific database client.
        This is the preferred way for application code to interact with the database.
        """
        client = self._ensure_client()
        if not client:
            return None
        return HbprDatabaseClient(client)

    def get_database_name(self) -> Optional[str]:
        """Returns the name of the currently loaded database file."""
        return self._db_name

    def get_database_path(self) -> Optional[str]:
        """Returns the full path of the currently loaded database file."""
        return self._file_path

    def is_loaded(self) -> bool:
        """Checks if a database is currently loaded."""
        return self._db_name is not None

    def get_record_count(self) -> int:
        """
        Returns the number of records in the 'hbpr_full_records' table.
        This is a specific query for the FlightCheckPy application.
        """
        client = self._ensure_client()
        if not client:
            return 0
        try:
            res = client.query("SELECT COUNT(*) AS c FROM hbpr_full_records", [])
            rows = res.get('rows', [])
            return int(rows[0][0]) if rows else 0
        except Exception:
            return 0

    def save_to_file(self) -> bool:
        """Saves the current in-memory database back to its original file."""
        if not self._file_path:
            return False
        try:
            client = self._ensure_client()
            if not client:
                return False
            client.save()
            return True
        except Exception:
            return False

    def create_backup(self) -> Optional[str]:
        """
        Requests the remote server to create a backup of the current database.
        Returns the path to the backup file if successful.
        """
        client = self._ensure_client()
        if not client:
            return None
        try:
            res = client.backup()
            return res.get('path')
        except Exception:
            return None

    def close(self):
        """
        Resets the manager's state, effectively 'closing' the database
        from the manager's perspective. Does not close the remote connection.
        """
        self._db_name = None
        self._file_path = None


_manager_singleton: Optional[DatabaseManager] = None


def get_manager() -> DatabaseManager:
    """
    Returns a singleton instance of the DatabaseManager.
    This ensures that the entire application shares a single point of management
    for the database connection.
    """
    global _manager_singleton
    if _manager_singleton is None:
        _manager_singleton = DatabaseManager()
    return _manager_singleton


def get_database_instance() -> Optional[HbprDatabaseClient]:
    """
    A convenience function to get the application-specific database client
    from the singleton manager. This is a common entry point for application code.
    """
    return get_manager().get_database()


def get_database_path() -> Optional[str]:
    """A convenience function to get the current database path from the singleton manager."""
    return get_manager().get_database_path()


