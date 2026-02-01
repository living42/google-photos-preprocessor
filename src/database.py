"""Simplified database module - tracks processed files only."""

import sqlite3
import logging
from pathlib import Path
from contextlib import contextmanager
from typing import List


class ProgressDatabase:
    """Simplified database - only tracks successfully processed files."""
    
    def __init__(self, db_path: str, logger=None):
        self.db_path = Path(db_path)
        self.logger = logger or logging.getLogger(__name__)
        self._init_database()
    
    @contextmanager
    def _get_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
    
    def _init_database(self) -> None:
        schema = """
            CREATE TABLE IF NOT EXISTS processed_files (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                relative_path TEXT UNIQUE NOT NULL,
                processed_at REAL DEFAULT (unixepoch())
            );
            CREATE INDEX IF NOT EXISTS idx_path ON processed_files(relative_path);
        """
        with self._get_connection() as conn:
            conn.executescript(schema)
        self.logger.info(f"Database initialized at {self.db_path}")
    
    def is_processed(self, relative_path: str) -> bool:
        """Check if file has been processed."""
        with self._get_connection() as conn:
            cursor = conn.execute(
                "SELECT 1 FROM processed_files WHERE relative_path = ?",
                (relative_path,)
            )
            return cursor.fetchone() is not None
    
    def add_processed(self, paths: List[str]) -> None:
        """Add records of successfully processed files."""
        with self._get_connection() as conn:
            conn.executemany(
                "INSERT OR REPLACE INTO processed_files (relative_path) VALUES (?)",
                [(p,) for p in paths]
            )
        self.logger.info(f"Recorded {len(paths)} processed files")
    
    def get_count(self) -> int:
        """Get total count of processed files."""
        with self._get_connection() as conn:
            cursor = conn.execute("SELECT COUNT(*) as count FROM processed_files")
            return cursor.fetchone()['count']
