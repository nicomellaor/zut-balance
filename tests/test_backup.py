import sqlite3
from datetime import UTC, datetime
from pathlib import Path

import pytest

from zut_balance.backup import create_backup
from zut_balance.banco_chile_cuenta_vista import parse_banco_chile_cuenta_vista
from zut_balance.persistence import StatementRepository


FIXTURE_PDF = Path(__file__).parent.parent / "media" / "cartola_ejemplo_banco_chile.pdf"


def test_backup_contains_a_restorable_consistent_database(tmp_path: Path) -> None:
    database_path = tmp_path / "active.sqlite3"
    with sqlite3.connect(database_path) as connection:
        connection.execute("CREATE TABLE entries (value TEXT NOT NULL)")
        connection.execute("INSERT INTO entries VALUES ('persisted')")

    backup_path = create_backup(database_path, tmp_path / "backups")

    with sqlite3.connect(backup_path) as connection:
        assert connection.execute("SELECT value FROM entries").fetchone() == ("persisted",)


def test_backup_preserves_a_restorable_v3_account_scope(tmp_path: Path) -> None:
    database_path = tmp_path / "active.sqlite3"
    repository = StatementRepository(database_path)
    repository.initialize()
    stored = repository.save(
        parse_banco_chile_cuenta_vista(FIXTURE_PDF.read_bytes()),
        "a" * 64,
        datetime.now(UTC).isoformat(),
    )

    backup_path = create_backup(database_path, tmp_path / "backups")

    with sqlite3.connect(backup_path) as connection:
        assert connection.execute("PRAGMA user_version").fetchone()[0] == 3
        assert connection.execute("SELECT COUNT(*) FROM accounts").fetchone()[0] == 1
        assert connection.execute("SELECT COUNT(*) FROM statements").fetchone()[0] == 1
        assert connection.execute("SELECT COUNT(*) FROM transactions").fetchone()[0] == len(stored.statement.transactions)
        assert connection.execute("SELECT COUNT(*) FROM transaction_classifications").fetchone()[0] == len(stored.statement.transactions)
        assert connection.execute("PRAGMA foreign_key_check").fetchone() is None
    restored = StatementRepository(backup_path)
    restored.initialize()
    assert restored.get(stored.id) == stored


def test_backup_failure_does_not_modify_the_active_database(tmp_path: Path) -> None:
    database_path = tmp_path / "active.sqlite3"
    with sqlite3.connect(database_path) as connection:
        connection.execute("CREATE TABLE entries (value TEXT NOT NULL)")
        connection.execute("INSERT INTO entries VALUES ('persisted')")

    with pytest.raises(OSError):
        create_backup(database_path, database_path / "not-a-directory")

    with sqlite3.connect(database_path) as connection:
        assert connection.execute("SELECT value FROM entries").fetchone() == ("persisted",)
