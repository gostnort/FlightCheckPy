#!/usr/bin/env python3
"""
Database Manager Component

Provides centralized in-memory database management with synchronous memory updates
and asynchronous file persistence.
"""

import streamlit as st
import sqlite3
import os
import tempfile
import threading
import time
from datetime import datetime
from typing import Optional, Callable
from scripts.hbpr_info_processor import HbprDatabase


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
        self._memory_conn: Optional[sqlite3.Connection] = None
        self._db_name: Optional[str] = None
        self._file_path: Optional[str] = None
        self._auto_save_enabled = True
        self._save_lock = threading.Lock()
        self._last_save_time: Optional[datetime] = None
        self._pending_save = False

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

            # Create new in-memory database
            self._memory_conn = sqlite3.connect(":memory:", check_same_thread=False)

            # Load data from file
            with sqlite3.connect(file_path) as file_conn:
                file_conn.backup(self._memory_conn)

            self._file_path = file_path
            self._db_name = os.path.basename(file_path)
            self._last_save_time = datetime.now()

            st.success(f"✅ Database loaded: {self._db_name}")
            return True

        except Exception as e:
            st.error(f"❌ Failed to load database: {e}")
            if self._memory_conn:
                self._memory_conn.close()
                self._memory_conn = None
            return False

    def get_connection(self) -> Optional[sqlite3.Connection]:
        """
        Get the in-memory database connection.

        Returns:
            sqlite3.Connection or None: The database connection
        """
        return self._memory_conn

    def get_database_name(self) -> Optional[str]:
        """
        Get the current database name.

        Returns:
            str or None: Database name
        """
        return self._db_name

    def get_database_path(self) -> Optional[str]:
        """
        Get the current database file path.

        Returns:
            str or None: Database file path
        """
        return self._file_path

    def is_loaded(self) -> bool:
        """
        Check if database is loaded.

        Returns:
            bool: True if database is loaded
        """
        return self._memory_conn is not None

    def get_record_count(self) -> int:
        """
        Get total number of records in the database.

        Returns:
            int: Number of records
        """
        if not self._memory_conn:
            return 0

        try:
            cursor = self._memory_conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM hbpr_full_records")
            return cursor.fetchone()[0]
        except:
            return 0

    def save_to_file(self, show_progress: bool = True) -> bool:
        """
        Save in-memory database to file synchronously.

        Args:
            show_progress (bool): Whether to show progress messages

        Returns:
            bool: True if successful
        """
        if not self._memory_conn or not self._file_path:
            if show_progress:
                st.error("❌ No database loaded")
            return False

        try:
            if show_progress:
                with st.spinner("💾 Saving database..."):
                    self._perform_save()
            else:
                self._perform_save()

            self._last_save_time = datetime.now()
            if show_progress:
                st.success("✅ Database saved successfully")
            return True

        except Exception as e:
            if show_progress:
                st.error(f"❌ Failed to save database: {e}")
            return False

    def _perform_save(self):
        """Internal method to perform the actual save operation."""
        with self._save_lock:
            with sqlite3.connect(self._file_path, check_same_thread=False) as file_conn:
                self._memory_conn.backup(file_conn)

    def enable_auto_save(self, enabled: bool = True):
        """
        Enable or disable automatic saving.

        Args:
            enabled (bool): Whether to enable auto-save
        """
        self._auto_save_enabled = enabled

    def trigger_auto_save(self):
        """
        Trigger asynchronous auto-save if enabled.
        This is called after database modifications.
        """
        if not self._auto_save_enabled or not self._memory_conn or not self._file_path:
            return

        # Mark that a save is pending
        self._pending_save = True

        # Start async save in background thread
        save_thread = threading.Thread(target=self._async_save_worker, daemon=True)
        save_thread.start()

    def _async_save_worker(self):
        """Background worker for asynchronous saving."""
        try:
            time.sleep(0.1)  # Small delay to batch rapid changes
            if self._pending_save:
                self._perform_save()
                self._last_save_time = datetime.now()
                self._pending_save = False
        except Exception as e:
            print(f"Async save error: {e}")

    def get_last_save_time(self) -> Optional[datetime]:
        """
        Get the last save time.

        Returns:
            datetime or None: Last save timestamp
        """
        return self._last_save_time

    def create_backup(self, backup_name: Optional[str] = None) -> Optional[str]:
        """
        Create a backup of the current database.

        Args:
            backup_name (str, optional): Name for the backup file

        Returns:
            str or None: Path to the backup file if successful
        """
        if not self._memory_conn:
            st.error("❌ No database loaded")
            return None

        try:
            if not backup_name:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                base_name = os.path.splitext(self._db_name or "database")[0]
                backup_name = f"{base_name}_backup_{timestamp}.db"

            backup_dir = os.path.join("databases", "backups")
            os.makedirs(backup_dir, exist_ok=True)
            backup_path = os.path.join(backup_dir, backup_name)

            with sqlite3.connect(backup_path, check_same_thread=False) as backup_conn:
                self._memory_conn.backup(backup_conn)

            st.success(f"✅ Backup created: {backup_path}")
            return backup_path

        except Exception as e:
            st.error(f"❌ Failed to create backup: {e}")
            return None

    def close(self):
        """
        Close the database connection and cleanup resources.
        """
        if self._memory_conn:
            # Final save before closing
            try:
                self.save_to_file(show_progress=False)
            except:
                pass

            self._memory_conn.close()
            self._memory_conn = None

        self._db_name = None
        self._file_path = None
        self._last_save_time = None
        self._pending_save = False


# Global instance
db_manager = DatabaseManager()


def get_database_instance() -> Optional[HbprDatabase]:
    """
    Get a database instance for operations.

    Returns:
        HbprDatabase or None: Database instance if available
    """
    conn = db_manager.get_connection()
    if conn:
        return HbprDatabase(conn)
    return None


def require_database(func: Callable) -> Callable:
    """
    Decorator to ensure database is loaded before executing function.

    Args:
        func: Function to decorate

    Returns:
        Decorated function
    """
    def wrapper(*args, **kwargs):
        if not db_manager.is_loaded():
            st.error("❌ Please load a database first")
            st.stop()
        return func(*args, **kwargs)
    return wrapper
