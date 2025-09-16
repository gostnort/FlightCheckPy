#!/usr/bin/env python3
"""
UI Database Manager Wrapper

Thin wrapper around remote_db.database_manager to integrate with Streamlit UI.
"""

import streamlit as st
import os
from typing import Optional, Callable
from remote_db.database_manager import get_manager, get_database_instance as _core_get_db, get_database_path as _core_get_path
from remote_db.remote_sqlite_adapter import RemoteSqliteConnection
from remote_db.hbpr_database_client import HbprDatabaseClient


class DatabaseManager:
    """
    Centralized database manager for in-memory operations with async file persistence.

    This class provides:
    - In-memory database connection management
    - Synchronous memory updates
    - Asynchronous file persistence
    - Thread-safe operations
    """

    def __init__(self):
        self._core = get_manager()

    def _ensure_client(self):
        # delegated inside core manager
        return self._core._ensure_client()  # type: ignore

    def load_database(self, file_path: str) -> bool:
        """
        Load database file into memory.

        Args:
            file_path (str): Path to the database file

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            if not os.path.exists(file_path):
                st.error(f"Database file not found: {file_path}")
                return False
            if not self._ensure_client():
                st.error("❌ DB service is not ready. Please login again.")
                return False
            if not self._core.load_database(file_path):
                st.error("❌ Failed to load database in remote memory")
                return False
            st.success(f"✅ Database loaded: {self._db_name}")
            return True

        except Exception as e:
            st.error(f"❌ Failed to load database: {e}")
            return False

    def get_connection(self) -> Optional[RemoteSqliteConnection]:
        """
        Get the in-memory database connection.

        Returns:
            sqlite3.Connection or None: The database connection
        """
        client = self._ensure_client()
        if not client:
            return None
        return RemoteSqliteConnection(client)

    def get_database(self) -> Optional[HbprDatabaseClient]:
        """
        Return a lightweight HbprDatabase wrapper over the in-memory connection.

        Returns:
            HbprDatabase or None: Wrapper instance if a connection is loaded.
        """
        return self._core.get_database()

    def get_database_name(self) -> Optional[str]:
        """
        Get the current database name.

        Returns:
            str or None: Database name
        """
        return self._core.get_database_name()

    def get_database_path(self) -> Optional[str]:
        """
        Get the current database file path.

        Returns:
            str or None: Database file path
        """
        return self._core.get_database_path()

    def is_loaded(self) -> bool:
        """
        Check if database is loaded.

        Returns:
            bool: True if database is loaded
        """
        return self._core.is_loaded()

    def get_record_count(self) -> int:
        return self._core.get_record_count()

    def save_to_file(self, show_progress: bool = True) -> bool:
        """
        Save in-memory database to file synchronously.

        Args:
            show_progress (bool): Whether to show progress messages

        Returns:
            bool: True if successful
        """
        if not self._core.get_database_path():
            if show_progress:
                st.error("❌ No database loaded")
            return False

        try:
            if show_progress:
                with st.spinner("💾 Saving database..."):
                    ok = self._core.save_to_file()
            else:
                ok = self._core.save_to_file()
            if not ok:
                if show_progress:
                    st.error("❌ Failed to save database")
                return False
            if show_progress:
                st.success("✅ Database saved successfully")
            return True

        except Exception as e:
            if show_progress:
                st.error(f"❌ Failed to save database: {e}")
            return False

    def create_backup(self, backup_name: Optional[str] = None) -> Optional[str]:
        path = self._core.create_backup()
        if not path:
            st.error("❌ Failed to create backup")
            return None
        st.success(f"✅ Backup created: {path}")
        return path

    def close(self):
        self._core.close()


# Global instance
_db_manager_instance = DatabaseManager()


def get_database_instance() -> Optional[HbprDatabaseClient]:
    """
    Get a database instance for operations.

    Returns:
        HbprDatabaseClient or None: Database instance if available
    """
    return _core_get_db()


def get_database_path() -> Optional[str]:
    """
    Get the current database file path from the manager.

    Returns:
        str or None: Database file path
    """
    return _core_get_path()


def require_database(func: Callable) -> Callable:
    """
    Decorator to ensure database is loaded before executing function.

    Args:
        func: Function to decorate

    Returns:
        Decorated function
    """
    def wrapper(*args, **kwargs):
        if not _db_manager_instance.is_loaded():
            st.error("❌ Please load a database first")
            st.stop()
        return func(*args, **kwargs)
    return wrapper


def create_database_selectbox(label="Select database:", key=None, default_index=0, custom_folder=None):
    """
    创建数据库选择下拉框并自动加载到内存数据库
    Args:
        label (str): 下拉框标签
        key (str): Streamlit组件key
        default_index (int): 默认选中的索引（0为最新的数据库）
        custom_folder (str): 自定义数据库文件夹路径
    Returns:
        tuple: (selected_db_file, db_files_list) 或 (None, []) 如果没有数据库
    """
    client = _db_manager_instance._ensure_client()
    if not client:
        st.error("❌ DB service not available. Please login again.")
        return None, []
    db_files = client.list_databases()
    if not db_files:
        return None, []
    db_names = [os.path.basename(p) for p in db_files]

    # 设定选中索引为当前已加载到内存的数据库
    current_memory_db_name = _db_manager_instance.get_database_name()
    selected_index = default_index
    for i, name in enumerate(db_names):
        if name == current_memory_db_name:
            selected_index = i
            break

    selected_db_name = st.selectbox(
        label,
        options=db_names,
        index=selected_index,
        key=key
    )

    # 获取完整的文件路径
    selected_db_file = db_files[db_names.index(selected_db_name)]

    # 检查是否需要加载新的数据库到内存
    if selected_db_file:
        current_memory_db_name = _db_manager_instance.get_database_name()
        selected_db_name = os.path.basename(selected_db_file)

        # 如果选择的数据库与当前内存中的不同，则加载新数据库
        if selected_db_name != current_memory_db_name:
            with st.spinner(f"🔄 正在切换到 {selected_db_name}..."):
                # 加载新数据库
                success = _db_manager_instance.load_database(selected_db_file)
                if success:
                    st.success(f"✅ 数据库 {selected_db_name} 已加载到内存")
                    # Database loading is synchronous, no need for st.rerun()
                    # The UI will update naturally when the function completes
                else:
                    st.error(f"❌ 无法加载数据库 {selected_db_name} 到内存")
                    return None, []

    return selected_db_file, db_files