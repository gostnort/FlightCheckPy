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
    Manage connection to the per-user remote in-memory DB service.
    """
    def __init__(self):
        self._client: Optional[DbPortClient] = None
        self._db_name: Optional[str] = None
        self._file_path: Optional[str] = None

    def _ensure_client(self) -> Optional[DbPortClient]:
        host = os.environ.get('FCP_DB_HOST')
        port = os.environ.get('FCP_DB_PORT')
        # Fallback to Streamlit session if available at runtime
        if (not host or not port):
            try:
                import streamlit as st  # type: ignore
                host = host or st.session_state.get('db_service_host')
                port = port or st.session_state.get('db_service_port')
            except Exception:
                pass
        if not host or not port:
            return None
        if not self._client:
            self._client = DbPortClient(str(host), int(port))
        return self._client

    def load_database(self, file_path: str) -> bool:
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
        client = self._ensure_client()
        if not client:
            return None
        return RemoteSqliteConnection(client)

    def get_database(self) -> Optional[HbprDatabaseClient]:
        client = self._ensure_client()
        if not client:
            return None
        return HbprDatabaseClient(client)

    def get_database_name(self) -> Optional[str]:
        return self._db_name

    def get_database_path(self) -> Optional[str]:
        return self._file_path

    def is_loaded(self) -> bool:
        return self._db_name is not None

    def get_record_count(self) -> int:
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
        client = self._ensure_client()
        if not client:
            return None
        try:
            res = client.backup()
            return res.get('path')
        except Exception:
            return None

    def close(self):
        self._db_name = None
        self._file_path = None


_manager_singleton: Optional[DatabaseManager] = None


def get_manager() -> DatabaseManager:
    global _manager_singleton
    if _manager_singleton is None:
        _manager_singleton = DatabaseManager()
    return _manager_singleton


def get_database_instance() -> Optional[HbprDatabaseClient]:
    return get_manager().get_database()


def get_database_path() -> Optional[str]:
    return get_manager().get_database_path()


