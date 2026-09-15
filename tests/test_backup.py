import sqlite3
from pathlib import Path

import pytest

from zut_balance.backup import create_backup


def test_backup_contains_a_restorable_consistent_database(tmp_path: Path) -> None:
    database_path = tmp_path / "active.sqlite3"
    with sqlite3.connect(database_path) as connection:
        connection.execute("CREATE TABLE entries (value TEXT NOT NULL)")
        connection.execute("INSERT INTO entries VALUES ('persisted')")

    backup_path = create_backup(database_path, tmp_path / "backups")

    with sqlite3.connect(backup_path) as connection:
        assert connection.execute("SELECT value FROM entries").fetchone() == ("persisted",)


def test_backup_failure_does_not_modify_the_active_database(tmp_path: Path) -> None:
    database_path = tmp_path / "active.sqlite3"
    with sqlite3.connect(database_path) as connection:
        connection.execute("CREATE TABLE entries (value TEXT NOT NULL)")
        connection.execute("INSERT INTO entries VALUES ('persisted')")

    with pytest.raises(OSError):
        create_backup(database_path, database_path / "not-a-directory")

    with sqlite3.connect(database_path) as connection:
        assert connection.execute("SELECT value FROM entries").fetchone() == ("persisted",)
