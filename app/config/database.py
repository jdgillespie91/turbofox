import sqlite3
from collections.abc import Generator
from contextlib import contextmanager

import logfire

from app.config.settings import settings

__all__ = ["get_db_connection", "execute_sql_file"]


@contextmanager
def get_db_connection() -> Generator[sqlite3.Connection]:
    """Context manager for database connections"""
    conn = sqlite3.connect(settings.sqlite_database)
    conn.row_factory = sqlite3.Row

    with logfire.span("PRAGMA settings"):
        cursor = conn.cursor()
        cursor.execute("PRAGMA synchronous = NORMAL")
        cursor.execute("PRAGMA busy_timeout = 5000")
        cursor.execute("PRAGMA cache_size = -20000")
        cursor.execute("PRAGMA foreign_keys = ON")
        cursor.execute("PRAGMA temp_store = MEMORY")
        cursor.execute("PRAGMA mmap_size = 268435456")
        cursor.close()

    # Enable SQLite logging.
    conn.set_trace_callback(lambda sql: logfire.info("SQL", args=[sql]))

    try:
        yield conn
    finally:
        conn.close()


def execute_sql_file(file_path: str) -> None:
    """Execute a SQL file"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.executescript(open(file_path).read())
        conn.commit()
