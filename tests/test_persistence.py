from datetime import UTC, datetime
from dataclasses import replace
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import sqlite3

import pytest

from zut_balance import persistence
from zut_balance.banco_chile_cuenta_vista import parse_banco_chile_cuenta_vista
from zut_balance.persistence import (
    DatabaseBusyError,
    IncompatibleSchemaError,
    MAX_LOCK_RETRIES,
    StatementRepository,
)


FIXTURE_PDF = Path(__file__).parent.parent / "media" / "cartola_ejemplo_banco_chile.pdf"


def test_repository_round_trips_normalized_statement(tmp_path: Path) -> None:
    repository = StatementRepository(tmp_path / "statements.sqlite3")
    repository.initialize()
    statement = parse_banco_chile_cuenta_vista(FIXTURE_PDF.read_bytes())

    stored = repository.save(
        statement,
        "a" * 64,
        datetime.now(UTC).isoformat(),
    )

    assert repository.get(stored.id) == stored
    assert repository.get_by_hash("a" * 64) == stored
    repository.initialize()
    assert repository.get(stored.id) == stored


def test_schema_does_not_store_source_pdf_or_extracted_text(tmp_path: Path) -> None:
    database_path = tmp_path / "statements.sqlite3"
    repository = StatementRepository(database_path)
    repository.initialize()

    with sqlite3.connect(database_path) as connection:
        assert connection.execute("PRAGMA user_version").fetchone()[0] == 2
        statement_columns = {
            row[1] for row in connection.execute("PRAGMA table_info(statements)")
        }
        transaction_columns = {
            row[1] for row in connection.execute("PRAGMA table_info(transactions)")
        }
        classification_columns = {
            row[1] for row in connection.execute("PRAGMA table_info(transaction_classifications)")
        }

    assert "pdf" not in statement_columns
    assert "source_pdf" not in statement_columns
    assert "extracted_text" not in statement_columns
    assert "extracted_text" not in transaction_columns
    assert classification_columns == {
        "transaction_id",
        "merchant_name",
        "merchant_key",
        "category",
        "rule_id",
        "ruleset_version",
        "classified_at",
    }


def test_repository_rejects_incompatible_schema_without_mutating_it(tmp_path: Path) -> None:
    database_path = tmp_path / "statements.sqlite3"
    with sqlite3.connect(database_path) as connection:
        connection.execute("CREATE TABLE statements (id TEXT PRIMARY KEY, legacy_value TEXT)")
        connection.execute("INSERT INTO statements VALUES ('legacy', 'preserve')")

    with pytest.raises(IncompatibleSchemaError):
        StatementRepository(database_path).initialize()

    with sqlite3.connect(database_path) as connection:
        assert connection.execute("PRAGMA user_version").fetchone()[0] == 0
        assert connection.execute("SELECT * FROM statements").fetchone() == ("legacy", "preserve")
        assert connection.execute(
            "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'transactions'"
        ).fetchone() is None


def test_repository_rejects_unsupported_schema_versions_without_mutation(tmp_path: Path) -> None:
    database_path = tmp_path / "statements.sqlite3"
    with sqlite3.connect(database_path) as connection:
        connection.execute("PRAGMA user_version = 3")

    with pytest.raises(IncompatibleSchemaError):
        StatementRepository(database_path).initialize()

    with sqlite3.connect(database_path) as connection:
        assert connection.execute("PRAGMA user_version").fetchone()[0] == 3
        assert connection.execute(
            "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'statements'"
        ).fetchone() is None


def test_repository_rejects_incomplete_v1_schema_without_mutation(tmp_path: Path) -> None:
    database_path = tmp_path / "statements.sqlite3"
    with sqlite3.connect(database_path) as connection:
        connection.execute("PRAGMA user_version = 1")

    with pytest.raises(IncompatibleSchemaError):
        StatementRepository(database_path).initialize()

    with sqlite3.connect(database_path) as connection:
        assert connection.execute("PRAGMA user_version").fetchone()[0] == 1


def test_repository_rejects_incomplete_v2_schema_without_mutation(tmp_path: Path) -> None:
    database_path = tmp_path / "statements.sqlite3"
    with sqlite3.connect(database_path) as connection:
        connection.execute("PRAGMA user_version = 2")

    with pytest.raises(IncompatibleSchemaError):
        StatementRepository(database_path).initialize()

    with sqlite3.connect(database_path) as connection:
        assert connection.execute("PRAGMA user_version").fetchone()[0] == 2


def test_repository_deduplicates_lists_and_deletes_statement(tmp_path: Path) -> None:
    database_path = tmp_path / "statements.sqlite3"
    repository = StatementRepository(database_path)
    repository.initialize()
    statement = parse_banco_chile_cuenta_vista(FIXTURE_PDF.read_bytes())
    created_at = datetime.now(UTC).isoformat()

    stored, created = repository.save_or_get(statement, "b" * 64, created_at)
    duplicate, duplicate_created = repository.save_or_get(statement, "b" * 64, created_at)

    assert created is True
    assert duplicate_created is False
    assert duplicate == stored
    assert repository.list_metadata(limit=1, offset=0)[0].id == stored.id
    assert repository.list_metadata(limit=1, offset=1) == ()
    assert repository.delete(stored.id) is True
    assert repository.get(stored.id) is None

    with sqlite3.connect(database_path) as connection:
        assert connection.execute("SELECT COUNT(*) FROM transactions").fetchone()[0] == 0
        assert connection.execute("SELECT COUNT(*) FROM transaction_classifications").fetchone()[0] == 0


def test_repository_migrates_v1_data_to_v2_classifications(tmp_path: Path) -> None:
    database_path = tmp_path / "statements.sqlite3"
    repository = StatementRepository(database_path)
    repository.initialize()
    statement = parse_banco_chile_cuenta_vista(FIXTURE_PDF.read_bytes())
    stored = repository.save(statement, "f" * 64, datetime.now(UTC).isoformat())

    with sqlite3.connect(database_path) as connection:
        connection.execute("DROP TABLE transaction_classifications")
        connection.execute("PRAGMA user_version = 1")

    repository.initialize()

    with sqlite3.connect(database_path) as connection:
        assert connection.execute("PRAGMA user_version").fetchone()[0] == 2
        assert connection.execute("SELECT COUNT(*) FROM statements").fetchone()[0] == 1
        assert connection.execute("SELECT COUNT(*) FROM transactions").fetchone()[0] == len(
            statement.transactions
        )
        assert connection.execute(
            "SELECT COUNT(*) FROM transaction_classifications"
        ).fetchone()[0] == len(statement.transactions)
    assert all(transaction.classification is not None for transaction in repository.get(stored.id).statement.transactions)


def test_repository_rolls_back_failed_v1_migration(tmp_path: Path, monkeypatch) -> None:
    database_path = tmp_path / "statements.sqlite3"
    repository = StatementRepository(database_path)
    repository.initialize()
    repository.save(
        parse_banco_chile_cuenta_vista(FIXTURE_PDF.read_bytes()),
        "g" * 64,
        datetime.now(UTC).isoformat(),
    )

    with sqlite3.connect(database_path) as connection:
        connection.execute("DROP TABLE transaction_classifications")
        connection.execute("PRAGMA user_version = 1")

    monkeypatch.setattr(
        persistence,
        "classify_transaction",
        lambda *_: (_ for _ in ()).throw(RuntimeError("classification failed")),
    )

    with pytest.raises(RuntimeError, match="classification failed"):
        repository.initialize()

    with sqlite3.connect(database_path) as connection:
        assert connection.execute("PRAGMA user_version").fetchone()[0] == 1
        assert connection.execute(
            "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'transaction_classifications'"
        ).fetchone() is None


def test_repository_deduplicates_concurrent_saves(tmp_path: Path) -> None:
    database_path = tmp_path / "statements.sqlite3"
    StatementRepository(database_path).initialize()
    statement = parse_banco_chile_cuenta_vista(FIXTURE_PDF.read_bytes())
    created_at = datetime.now(UTC).isoformat()

    def save() -> tuple[object, bool]:
        return StatementRepository(database_path).save_or_get(statement, "d" * 64, created_at)

    with ThreadPoolExecutor(max_workers=2) as executor:
        first, second = tuple(executor.map(lambda _: save(), range(2)))

    assert first[0] == second[0]
    assert sorted((first[1], second[1])) == [False, True]
    with sqlite3.connect(database_path) as connection:
        assert connection.execute("SELECT COUNT(*) FROM statements").fetchone()[0] == 1
        assert connection.execute("SELECT COUNT(*) FROM transactions").fetchone()[0] == len(
            statement.transactions
        )


def test_repository_fails_after_bounded_database_lock_retries(tmp_path: Path, monkeypatch) -> None:
    repository = StatementRepository(tmp_path / "statements.sqlite3")
    statement = parse_banco_chile_cuenta_vista(FIXTURE_PDF.read_bytes())
    attempts = 0

    monkeypatch.setattr(repository, "get_by_hash", lambda _: None)

    def locked_save(*_: object) -> object:
        nonlocal attempts
        attempts += 1
        raise sqlite3.OperationalError("database is locked")

    monkeypatch.setattr(repository, "save", locked_save)

    with pytest.raises(DatabaseBusyError):
        repository.save_or_get(statement, "e" * 64, datetime.now(UTC).isoformat())

    assert attempts == MAX_LOCK_RETRIES + 1


def test_repository_rolls_back_failed_statement_insert(tmp_path: Path) -> None:
    repository = StatementRepository(tmp_path / "statements.sqlite3")
    repository.initialize()
    statement = parse_banco_chile_cuenta_vista(FIXTURE_PDF.read_bytes())
    invalid_transaction = replace(statement.transactions[0], description=None)
    invalid_statement = replace(statement, transactions=(invalid_transaction,))

    with pytest.raises(sqlite3.IntegrityError):
        repository.save(invalid_statement, "c" * 64, datetime.now(UTC).isoformat())

    assert repository.list_metadata(limit=100, offset=0) == ()


def test_repository_rolls_back_failed_classification_insert(tmp_path: Path, monkeypatch) -> None:
    database_path = tmp_path / "statements.sqlite3"
    repository = StatementRepository(database_path)
    repository.initialize()
    statement = parse_banco_chile_cuenta_vista(FIXTURE_PDF.read_bytes())
    monkeypatch.setattr(
        persistence,
        "classify_transaction",
        lambda *_: (_ for _ in ()).throw(RuntimeError("classification failed")),
    )

    with pytest.raises(RuntimeError, match="classification failed"):
        repository.save(statement, "h" * 64, datetime.now(UTC).isoformat())

    with sqlite3.connect(database_path) as connection:
        assert connection.execute("SELECT COUNT(*) FROM statements").fetchone()[0] == 0
        assert connection.execute("SELECT COUNT(*) FROM transactions").fetchone()[0] == 0
        assert connection.execute(
            "SELECT COUNT(*) FROM transaction_classifications"
        ).fetchone()[0] == 0
