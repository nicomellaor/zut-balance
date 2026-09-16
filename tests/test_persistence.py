from datetime import UTC, date, datetime
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


def _downgrade_to_v2(database_path: Path) -> None:
    with sqlite3.connect(database_path) as connection:
        connection.execute("PRAGMA foreign_keys = OFF")
        connection.execute(
            """
            CREATE TABLE statements_v2 (
                id TEXT PRIMARY KEY,
                source_sha256 TEXT NOT NULL UNIQUE,
                created_at TEXT NOT NULL,
                bank TEXT NOT NULL,
                product TEXT NOT NULL,
                masked_account_number TEXT,
                currency TEXT,
                period_start TEXT NOT NULL,
                period_end TEXT NOT NULL,
                statement_number TEXT,
                page_number INTEGER,
                total_pages INTEGER,
                opening_balance INTEGER NOT NULL,
                closing_balance INTEGER NOT NULL,
                one_day_retention INTEGER,
                multi_day_retention INTEGER,
                available_balance INTEGER
            )
            """
        )
        columns = (
            "id, source_sha256, created_at, bank, product, masked_account_number, currency, "
            "period_start, period_end, statement_number, page_number, total_pages, opening_balance, "
            "closing_balance, one_day_retention, multi_day_retention, available_balance"
        )
        connection.execute(f"INSERT INTO statements_v2 ({columns}) SELECT {columns} FROM statements")
        connection.execute("DROP TABLE statements")
        connection.execute("ALTER TABLE statements_v2 RENAME TO statements")
        connection.execute("DROP TABLE accounts")
        connection.execute("PRAGMA user_version = 2")


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
        assert connection.execute("PRAGMA user_version").fetchone()[0] == 3
        account_columns = {row[1] for row in connection.execute("PRAGMA table_info(accounts)")}
        statement_columns = {
            row[1] for row in connection.execute("PRAGMA table_info(statements)")
        }
        transaction_columns = {
            row[1] for row in connection.execute("PRAGMA table_info(transactions)")
        }
        classification_columns = {
            row[1] for row in connection.execute("PRAGMA table_info(transaction_classifications)")
        }
        statement_foreign_keys = tuple(connection.execute("PRAGMA foreign_key_list(statements)"))
        statement_indexes = {row[1] for row in connection.execute("PRAGMA index_list(statements)")}
        account_indexes = {
            row[0]: row[1]
            for row in connection.execute(
                "SELECT name, sql FROM sqlite_master WHERE type = 'index' AND tbl_name = 'accounts'"
            )
        }

    assert "pdf" not in statement_columns
    assert "source_pdf" not in statement_columns
    assert "extracted_text" not in statement_columns
    assert "extracted_text" not in transaction_columns
    assert account_columns == {
        "id",
        "bank",
        "product",
        "currency",
        "masked_account_number",
        "identity_status",
        "created_at",
    }
    assert "account_id" in statement_columns
    assert any(foreign_key[2] == "accounts" and foreign_key[3] == "account_id" for foreign_key in statement_foreign_keys)
    assert "statements_account_period" in statement_indexes
    assert "WHERE identity_status = 'visible_mask' AND currency IS NOT NULL" in account_indexes[
        "accounts_visible_identity_with_currency"
    ]
    assert "WHERE identity_status = 'visible_mask' AND currency IS NULL" in account_indexes[
        "accounts_visible_identity_without_currency"
    ]
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
        assert connection.execute("SELECT COUNT(*) FROM accounts").fetchone()[0] == 0


def test_repository_get_many_preserves_requested_order_and_omits_missing_ids(tmp_path: Path) -> None:
    repository = StatementRepository(tmp_path / "statements.sqlite3")
    repository.initialize()
    statement = parse_banco_chile_cuenta_vista(FIXTURE_PDF.read_bytes())
    first = repository.save(statement, "i" * 64, datetime.now(UTC).isoformat())
    second = repository.save(statement, "j" * 64, datetime.now(UTC).isoformat())

    stored = repository.get_many((second.id, "missing", first.id))

    assert tuple(item.id for item in stored) == (second.id, first.id)
    assert all(transaction.classification is not None for item in stored for transaction in item.statement.transactions)


def test_repository_resolves_visible_account_history_in_period_order(tmp_path: Path) -> None:
    repository = StatementRepository(tmp_path / "statements.sqlite3")
    repository.initialize()
    base = parse_banco_chile_cuenta_vista(FIXTURE_PDF.read_bytes())
    first = repository.save(
        replace(base, masked_account_number="****1234", period_start=date(2026, 6, 30), period_end=date(2026, 7, 31)),
        "k" * 64,
        datetime.now(UTC).isoformat(),
    )
    second = repository.save(
        replace(base, masked_account_number="****1234", period_start=date(2026, 7, 31), period_end=date(2026, 8, 31)),
        "l" * 64,
        datetime.now(UTC).isoformat(),
    )
    repository.save(
        replace(base, masked_account_number="****9876", period_start=date(2026, 6, 1), period_end=date(2026, 6, 30)),
        "m" * 64,
        datetime.now(UTC).isoformat(),
    )
    hidden = repository.save(
        replace(base, masked_account_number="XXXXXXXX", period_start=date(2026, 5, 1), period_end=date(2026, 5, 31)),
        "n" * 64,
        datetime.now(UTC).isoformat(),
    )

    account_id = next(
        account.id for account in repository.list_accounts() if account.masked_account_number == "****1234"
    )
    hidden_account_id = next(
        account.id for account in repository.list_accounts() if account.masked_account_number == "XXXXXXXX"
    )
    assert tuple(item.id for item in repository.history_for_account(account_id)) == (first.id, second.id)
    assert repository.history_for_account(hidden_account_id) == (hidden,)


def test_repository_groups_visible_accounts_and_isolates_ambiguous_accounts(tmp_path: Path) -> None:
    repository = StatementRepository(tmp_path / "statements.sqlite3")
    repository.initialize()
    base = parse_banco_chile_cuenta_vista(FIXTURE_PDF.read_bytes())

    visible = replace(base, masked_account_number="****1234")
    no_currency = replace(visible, currency=None)
    repository.save(visible, "p" * 64, datetime.now(UTC).isoformat())
    repository.save(visible, "q" * 64, datetime.now(UTC).isoformat())
    repository.save(no_currency, "r" * 64, datetime.now(UTC).isoformat())
    repository.save(no_currency, "s" * 64, datetime.now(UTC).isoformat())
    repository.save(replace(base, masked_account_number="XXXXXXXX"), "t" * 64, datetime.now(UTC).isoformat())
    repository.save(replace(base, masked_account_number="XXXXXXXX"), "u" * 64, datetime.now(UTC).isoformat())

    accounts = repository.list_accounts()

    assert sorted(account.statement_count for account in accounts) == [1, 1, 2, 2]
    assert [account.identity_status for account in accounts].count("ambiguous") == 2
    assert len({account.id for account in accounts if account.currency is None}) == 1


def test_repository_concurrently_groups_visible_accounts_with_null_currency(tmp_path: Path) -> None:
    database_path = tmp_path / "statements.sqlite3"
    StatementRepository(database_path).initialize()
    base = replace(
        parse_banco_chile_cuenta_vista(FIXTURE_PDF.read_bytes()),
        masked_account_number="****1234",
        currency=None,
    )

    def save(index: int) -> tuple[object, bool]:
        return StatementRepository(database_path).save_or_get(
            base, f"{index:064x}", datetime.now(UTC).isoformat()
        )

    with ThreadPoolExecutor(max_workers=2) as executor:
        tuple(executor.map(save, range(2)))

    accounts = StatementRepository(database_path).list_accounts()
    assert len(accounts) == 1
    assert accounts[0].statement_count == 2


def test_repository_retains_account_until_its_last_statement_is_deleted(tmp_path: Path) -> None:
    repository = StatementRepository(tmp_path / "statements.sqlite3")
    repository.initialize()
    base = replace(parse_banco_chile_cuenta_vista(FIXTURE_PDF.read_bytes()), masked_account_number="****1234")
    first = repository.save(base, "v" * 64, datetime.now(UTC).isoformat())
    second = repository.save(base, "w" * 64, datetime.now(UTC).isoformat())
    account_id = repository.list_accounts()[0].id

    assert repository.delete(first.id) is True
    assert repository.get_account(account_id) is not None
    assert repository.delete(second.id) is True
    assert repository.get_account(account_id) is None


def test_repository_lists_accounts_and_filters_history_by_intersecting_period(tmp_path: Path) -> None:
    repository = StatementRepository(tmp_path / "statements.sqlite3")
    repository.initialize()
    base = parse_banco_chile_cuenta_vista(FIXTURE_PDF.read_bytes())
    older = repository.save(
        replace(base, masked_account_number="****1234", period_start=date(2026, 1, 1), period_end=date(2026, 1, 31)),
        "x" * 64,
        datetime.now(UTC).isoformat(),
    )
    intersecting = repository.save(
        replace(base, masked_account_number="****1234", period_start=date(2026, 2, 1), period_end=date(2026, 2, 28)),
        "y" * 64,
        datetime.now(UTC).isoformat(),
    )
    repository.save(
        replace(base, masked_account_number="****9876", period_start=date(2026, 3, 1), period_end=date(2026, 3, 31)),
        "z" * 64,
        datetime.now(UTC).isoformat(),
    )

    accounts = repository.list_accounts()
    account = next(item for item in accounts if item.masked_account_number == "****1234")

    assert repository.list_accounts()[0].masked_account_number == "****9876"
    assert (account.statement_count, account.period_start, account.period_end) == (2, date(2026, 1, 1), date(2026, 2, 28))
    assert repository.get_account("missing") is None
    assert tuple(item.id for item in repository.history_for_account(account.id, date(2026, 2, 15))) == (intersecting.id,)
    assert repository.history_for_account(account.id, date(2027, 1, 1)) == ()
    assert repository.history_for_account("missing") == ()
    assert older.id not in {item.id for item in repository.history_for_account(account.id, date(2026, 2, 1))}


def test_repository_catalog_does_not_limit_large_account_history(tmp_path: Path) -> None:
    repository = StatementRepository(tmp_path / "statements.sqlite3")
    repository.initialize()
    statement = replace(
        parse_banco_chile_cuenta_vista(FIXTURE_PDF.read_bytes()),
        masked_account_number="****1234",
        transactions=(),
    )

    for index in range(101):
        repository.save(statement, f"{index:064x}", datetime.now(UTC).isoformat())

    account = repository.list_accounts()[0]
    assert account.statement_count == 101
    assert len(repository.history_for_account(account.id)) == 101


def test_repository_migrates_v1_data_to_v3_accounts(tmp_path: Path) -> None:
    database_path = tmp_path / "statements.sqlite3"
    repository = StatementRepository(database_path)
    repository.initialize()
    base = parse_banco_chile_cuenta_vista(FIXTURE_PDF.read_bytes())
    first = repository.save(replace(base, masked_account_number="****1234"), "f" * 64, datetime.now(UTC).isoformat())
    second = repository.save(replace(base, masked_account_number="****1234"), "g" * 64, datetime.now(UTC).isoformat())
    hidden = repository.save(replace(base, masked_account_number="XXXXXXXX"), "h" * 64, datetime.now(UTC).isoformat())

    _downgrade_to_v2(database_path)
    with sqlite3.connect(database_path) as connection:
        connection.execute("DROP TABLE transaction_classifications")
        connection.execute("PRAGMA user_version = 1")

    repository.initialize()

    with sqlite3.connect(database_path) as connection:
        assert connection.execute("PRAGMA user_version").fetchone()[0] == 3
        assert connection.execute("SELECT COUNT(*) FROM statements").fetchone()[0] == 3
        assert connection.execute("SELECT COUNT(*) FROM transactions").fetchone()[0] == len(
            base.transactions
        ) * 3
        assert connection.execute(
            "SELECT COUNT(*) FROM transaction_classifications"
        ).fetchone()[0] == len(base.transactions) * 3
        account_ids = {
            row[0] for row in connection.execute("SELECT account_id FROM statements WHERE id IN (?, ?)", (first.id, second.id))
        }
        assert len(account_ids) == 1
        assert connection.execute("SELECT account_id FROM statements WHERE id = ?", (hidden.id,)).fetchone()[0] not in account_ids


def test_repository_migrates_v2_data_to_v3_accounts(tmp_path: Path) -> None:
    database_path = tmp_path / "statements.sqlite3"
    repository = StatementRepository(database_path)
    repository.initialize()
    statement = parse_banco_chile_cuenta_vista(FIXTURE_PDF.read_bytes())
    stored = repository.save(statement, "o" * 64, datetime.now(UTC).isoformat())

    _downgrade_to_v2(database_path)

    repository.initialize()

    with sqlite3.connect(database_path) as connection:
        assert connection.execute("PRAGMA user_version").fetchone()[0] == 3
        assert connection.execute("SELECT account_id FROM statements WHERE id = ?", (stored.id,)).fetchone()[0]
        assert connection.execute("PRAGMA foreign_key_check").fetchone() is None
    assert repository.get(stored.id) is not None


@pytest.mark.parametrize("version", (1, 2))
def test_repository_rolls_back_failed_v3_migration(tmp_path: Path, monkeypatch, version: int) -> None:
    database_path = tmp_path / "statements.sqlite3"
    repository = StatementRepository(database_path)
    repository.initialize()
    statement = repository.save(
        parse_banco_chile_cuenta_vista(FIXTURE_PDF.read_bytes()),
        "g" * 64,
        datetime.now(UTC).isoformat(),
    )

    _downgrade_to_v2(database_path)
    if version == 1:
        with sqlite3.connect(database_path) as connection:
            connection.execute("DROP TABLE transaction_classifications")
            connection.execute("PRAGMA user_version = 1")
    monkeypatch.setattr(StatementRepository, "_validate_v3_schema", classmethod(lambda *_: (_ for _ in ()).throw(RuntimeError("v3 failed"))))

    with pytest.raises(RuntimeError, match="v3 failed"):
        repository.initialize()

    with sqlite3.connect(database_path) as connection:
        assert connection.execute("PRAGMA user_version").fetchone()[0] == version
        assert connection.execute("SELECT COUNT(*) FROM statements").fetchone()[0] == 1
        assert connection.execute("SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'accounts'").fetchone() is None
        assert connection.execute(
            "SELECT 1 FROM pragma_table_info('statements') WHERE name = 'account_id'"
        ).fetchone() is None
        classification_count = (
            connection.execute("SELECT COUNT(*) FROM transaction_classifications").fetchone()[0]
            if version == 2
            else 0
        )
        assert classification_count == (len(statement.statement.transactions) if version == 2 else 0)


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
