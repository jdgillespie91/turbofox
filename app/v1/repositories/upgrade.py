import sqlite3
from collections.abc import Callable
from pathlib import Path

from app.config.database import get_db_connection


def _get_migration_files() -> list[tuple[int, Path]]:
    """Get all migration files sorted by version number."""
    migrations_dir = Path(__file__).parent / "migrations"
    migration_files: list[tuple[int, Path]] = []

    for file in migrations_dir.glob("*.sql"):
        if not file.stem.startswith("00"):
            continue
        version = int(file.stem)
        migration_files.append((version, file))

    return sorted(migration_files, key=lambda x: x[0])


def _get_current_version(cursor: sqlite3.Cursor) -> int:
    """Get the current schema version from the database."""
    try:
        cursor.execute("SELECT version FROM schema_version ORDER BY version DESC LIMIT 1")
        result = cursor.fetchone()
        return int(result[0]) if result else 0
    except sqlite3.OperationalError:
        return 0


def _apply_migration(cursor: sqlite3.Cursor, version: int, file_path: Path) -> None:
    """Apply a single migration file."""
    with open(file_path) as f:
        sql = f.read()

    # Split the SQL file into individual statements
    statements = sql.split(";")

    # Execute each statement
    for statement in statements:
        if statement.strip():
            cursor.execute(statement)

    # Update the schema version
    cursor.execute("UPDATE schema_version SET version = ? WHERE id = 'singleton'", (version,))


def upgrade(on_migration: Callable[[int], None] | None = None) -> None:
    """
    Upgrade the database schema to the latest version by applying any pending migrations.

    Args:
        on_migration: Optional callback function that will be called with the version
            of each migration as it is applied.
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()

        # Get current version
        current_version = _get_current_version(cursor)

        # Get all migration files
        migration_files = _get_migration_files()

        # Apply pending migrations
        for version, file_path in migration_files:
            if version > current_version:
                _apply_migration(cursor, version, file_path)
                if on_migration:
                    on_migration(version)

        conn.commit()
