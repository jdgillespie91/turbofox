import sqlite3
import tempfile
from pathlib import Path
from unittest.mock import Mock, mock_open, patch

import pytest

from app.v1.repositories.upgrade import _apply_migration, _get_current_version, _get_migration_files, upgrade


class TestGetMigrationFiles:
    def test_get_migration_files_returns_sorted_files(self):
        """Test that migration files are returned sorted by version number."""
        mock_migrations_dir = Mock()
        
        mock_file1 = Mock()
        mock_file1.stem = "001"
        mock_file2 = Mock()
        mock_file2.stem = "003"
        mock_file3 = Mock()
        mock_file3.stem = "002"
        mock_file4 = Mock()
        mock_file4.stem = "invalid"  # Should be ignored
        
        mock_migrations_dir.glob.return_value = [mock_file1, mock_file2, mock_file3, mock_file4]
        
        with patch("app.v1.repositories.upgrade.Path") as mock_path:
            mock_path.return_value.parent.__truediv__.return_value = mock_migrations_dir
            result = _get_migration_files()
        
        assert len(result) == 3
        assert result[0] == (1, mock_file1)
        assert result[1] == (2, mock_file3)
        assert result[2] == (3, mock_file2)

    def test_get_migration_files_empty_directory(self):
        """Test behavior when migrations directory is empty."""
        mock_migrations_dir = Mock()
        mock_migrations_dir.glob.return_value = []
        
        with patch("app.v1.repositories.upgrade.Path") as mock_path:
            mock_path.return_value.parent.__truediv__.return_value = mock_migrations_dir
            result = _get_migration_files()
        
        assert result == []

    def test_get_migration_files_ignores_non_numeric_files(self):
        """Test that non-numeric migration files are ignored."""
        mock_migrations_dir = Mock()
        
        mock_file1 = Mock()
        mock_file1.stem = "001"
        mock_file2 = Mock()
        mock_file2.stem = "abc"
        mock_file3 = Mock()
        mock_file3.stem = "readme"
        
        mock_migrations_dir.glob.return_value = [mock_file1, mock_file2, mock_file3]
        
        with patch("app.v1.repositories.upgrade.Path") as mock_path:
            mock_path.return_value.parent.__truediv__.return_value = mock_migrations_dir
            result = _get_migration_files()
        
        assert len(result) == 1
        assert result[0] == (1, mock_file1)


class TestGetCurrentVersion:
    def test_get_current_version_with_existing_version(self):
        """Test getting current version when schema_version table exists."""
        mock_cursor = Mock()
        mock_cursor.fetchone.return_value = (5,)
        
        result = _get_current_version(mock_cursor)
        
        assert result == 5
        mock_cursor.execute.assert_called_once_with(
            "SELECT version FROM schema_version ORDER BY version DESC LIMIT 1"
        )

    def test_get_current_version_no_records(self):
        """Test getting current version when schema_version table is empty."""
        mock_cursor = Mock()
        mock_cursor.fetchone.return_value = None
        
        result = _get_current_version(mock_cursor)
        
        assert result == 0

    def test_get_current_version_table_not_exists(self):
        """Test getting current version when schema_version table doesn't exist."""
        mock_cursor = Mock()
        mock_cursor.execute.side_effect = sqlite3.OperationalError("no such table: schema_version")
        
        result = _get_current_version(mock_cursor)
        
        assert result == 0


class TestApplyMigration:
    def test_apply_migration_single_statement(self):
        """Test applying migration with single SQL statement."""
        mock_cursor = Mock()
        mock_file = Mock()
        
        sql_content = "CREATE TABLE test (id INTEGER);"
        
        with patch("builtins.open", mock_open(read_data=sql_content)):
            _apply_migration(mock_cursor, 1, mock_file)
        
        assert mock_cursor.execute.call_count == 2
        mock_cursor.execute.assert_any_call("CREATE TABLE test (id INTEGER)")
        mock_cursor.execute.assert_any_call(
            "UPDATE schema_version SET version = ? WHERE id = 'singleton'", (1,)
        )

    def test_apply_migration_multiple_statements(self):
        """Test applying migration with multiple SQL statements."""
        mock_cursor = Mock()
        mock_file = Mock()
        
        sql_content = """CREATE TABLE test1 (id INTEGER);
CREATE TABLE test2 (name TEXT);
INSERT INTO test1 VALUES (1);"""
        
        with patch("builtins.open", mock_open(read_data=sql_content)):
            _apply_migration(mock_cursor, 2, mock_file)
        
        assert mock_cursor.execute.call_count == 4
        mock_cursor.execute.assert_any_call("CREATE TABLE test1 (id INTEGER)")
        mock_cursor.execute.assert_any_call("\nCREATE TABLE test2 (name TEXT)")
        mock_cursor.execute.assert_any_call("\nINSERT INTO test1 VALUES (1)")
        mock_cursor.execute.assert_any_call(
            "UPDATE schema_version SET version = ? WHERE id = 'singleton'", (2,)
        )

    def test_apply_migration_ignores_empty_statements(self):
        """Test that empty statements are ignored during migration."""
        mock_cursor = Mock()
        mock_file = Mock()
        
        sql_content = "CREATE TABLE test (id INTEGER);;;"
        
        with patch("builtins.open", mock_open(read_data=sql_content)):
            _apply_migration(mock_cursor, 1, mock_file)
        
        assert mock_cursor.execute.call_count == 2
        mock_cursor.execute.assert_any_call("CREATE TABLE test (id INTEGER)")
        mock_cursor.execute.assert_any_call(
            "UPDATE schema_version SET version = ? WHERE id = 'singleton'", (1,)
        )


class TestUpgrade:
    @patch("app.v1.repositories.upgrade._get_migration_files")
    @patch("app.v1.repositories.upgrade._get_current_version")
    @patch("app.v1.repositories.upgrade._apply_migration")
    @patch("app.v1.repositories.upgrade.get_db_connection")
    def test_upgrade_applies_pending_migrations(
        self, mock_get_db_connection, mock_apply_migration, mock_get_current_version, mock_get_migration_files
    ):
        """Test that upgrade applies all pending migrations."""
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_conn.cursor.return_value = mock_cursor
        mock_get_db_connection.return_value.__enter__.return_value = mock_conn
        
        mock_get_current_version.return_value = 1
        mock_file2 = Mock()
        mock_file3 = Mock()
        mock_get_migration_files.return_value = [(1, Mock()), (2, mock_file2), (3, mock_file3)]
        
        upgrade()
        
        assert mock_apply_migration.call_count == 2
        mock_apply_migration.assert_any_call(mock_cursor, 2, mock_file2)
        mock_apply_migration.assert_any_call(mock_cursor, 3, mock_file3)
        mock_conn.commit.assert_called_once()

    @patch("app.v1.repositories.upgrade._get_migration_files")
    @patch("app.v1.repositories.upgrade._get_current_version")
    @patch("app.v1.repositories.upgrade._apply_migration")
    @patch("app.v1.repositories.upgrade.get_db_connection")
    def test_upgrade_no_pending_migrations(
        self, mock_get_db_connection, mock_apply_migration, mock_get_current_version, mock_get_migration_files
    ):
        """Test that upgrade does nothing when no pending migrations."""
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_conn.cursor.return_value = mock_cursor
        mock_get_db_connection.return_value.__enter__.return_value = mock_conn
        
        mock_get_current_version.return_value = 3
        mock_get_migration_files.return_value = [(1, Mock()), (2, Mock()), (3, Mock())]
        
        upgrade()
        
        mock_apply_migration.assert_not_called()
        mock_conn.commit.assert_called_once()

    @patch("app.v1.repositories.upgrade._get_migration_files")
    @patch("app.v1.repositories.upgrade._get_current_version")
    @patch("app.v1.repositories.upgrade._apply_migration")
    @patch("app.v1.repositories.upgrade.get_db_connection")
    def test_upgrade_calls_callback_for_each_migration(
        self, mock_get_db_connection, mock_apply_migration, mock_get_current_version, mock_get_migration_files
    ):
        """Test that upgrade calls callback function for each applied migration."""
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_conn.cursor.return_value = mock_cursor
        mock_get_db_connection.return_value.__enter__.return_value = mock_conn
        
        mock_get_current_version.return_value = 0
        mock_get_migration_files.return_value = [(1, Mock()), (2, Mock())]
        
        callback = Mock()
        upgrade(on_migration=callback)
        
        assert callback.call_count == 2
        callback.assert_any_call(1)
        callback.assert_any_call(2)

    @patch("app.v1.repositories.upgrade._get_migration_files")
    @patch("app.v1.repositories.upgrade._get_current_version")
    @patch("app.v1.repositories.upgrade._apply_migration")
    @patch("app.v1.repositories.upgrade.get_db_connection")
    def test_upgrade_no_callback(
        self, mock_get_db_connection, mock_apply_migration, mock_get_current_version, mock_get_migration_files
    ):
        """Test that upgrade works without callback function."""
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_conn.cursor.return_value = mock_cursor
        mock_get_db_connection.return_value.__enter__.return_value = mock_conn
        
        mock_get_current_version.return_value = 0
        mock_get_migration_files.return_value = [(1, Mock())]
        
        upgrade()  # No callback provided
        
        mock_apply_migration.assert_called_once()
        mock_conn.commit.assert_called_once()

    @patch("app.v1.repositories.upgrade._get_migration_files")
    @patch("app.v1.repositories.upgrade._get_current_version")
    @patch("app.v1.repositories.upgrade.get_db_connection")
    def test_upgrade_empty_migration_list(
        self, mock_get_db_connection, mock_get_current_version, mock_get_migration_files
    ):
        """Test upgrade behavior when no migration files exist."""
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_conn.cursor.return_value = mock_cursor
        mock_get_db_connection.return_value.__enter__.return_value = mock_conn
        
        mock_get_current_version.return_value = 0
        mock_get_migration_files.return_value = []
        
        upgrade()
        
        mock_conn.commit.assert_called_once()
