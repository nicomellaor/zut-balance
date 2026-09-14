from datetime import UTC, datetime
from dataclasses import replace
from pathlib import Path
import sqlite3

import pytest

from zut_balance.banco_chile_cuenta_vista import parse_banco_chile_cuenta_vista
from zut_balance.persistence import StatementRepository


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


def test_schema_does_not_store_source_pdf_or_extracted_text(tmp_path: Path) -> None:
    database_path = tmp_path / "statements.sqlite3"
    repository = StatementRepository(database_path)
    repository.initialize()

    with sqlite3.connect(database_path) as connection:
        statement_columns = {
            row[1] for row in connection.execute("PRAGMA table_info(statements)")
        }
        transaction_columns = {
            row[1] for row in connection.execute("PRAGMA table_info(transactions)")
        }

    assert "pdf" not in statement_columns
    assert "source_pdf" not in statement_columns
    assert "extracted_text" not in statement_columns
    assert "extracted_text" not in transaction_columns


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


def test_repository_rolls_back_failed_statement_insert(tmp_path: Path) -> None:
    repository = StatementRepository(tmp_path / "statements.sqlite3")
    repository.initialize()
    statement = parse_banco_chile_cuenta_vista(FIXTURE_PDF.read_bytes())
    invalid_transaction = replace(statement.transactions[0], description=None)
    invalid_statement = replace(statement, transactions=(invalid_transaction,))

    with pytest.raises(sqlite3.IntegrityError):
        repository.save(invalid_statement, "c" * 64, datetime.now(UTC).isoformat())

    assert repository.list_metadata(limit=100, offset=0) == ()
