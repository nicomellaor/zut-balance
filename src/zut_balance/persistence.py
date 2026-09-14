"""SQLite persistence for normalized bank statements."""

from dataclasses import dataclass, replace
from datetime import UTC, date, datetime
from pathlib import Path
import sqlite3
from contextlib import closing
import time
from uuid import uuid4

from .categorization import classify_transaction
from .models import Category, Classification, MovementType, Statement, StatementSummary, Transaction


SCHEMA_VERSION = 2
MAX_LOCK_RETRIES = 3
LOCK_RETRY_DELAY_SECONDS = 0.01

_STATEMENT_COLUMNS = frozenset(
    {
        "id",
        "source_sha256",
        "created_at",
        "bank",
        "product",
        "masked_account_number",
        "currency",
        "period_start",
        "period_end",
        "statement_number",
        "page_number",
        "total_pages",
        "opening_balance",
        "closing_balance",
        "one_day_retention",
        "multi_day_retention",
        "available_balance",
    }
)
_TRANSACTION_COLUMNS = frozenset(
    {
        "id",
        "statement_id",
        "position",
        "transaction_date",
        "description",
        "document_number",
        "branch_or_channel",
        "amount",
        "movement_type",
        "reported_balance",
    }
)
_CLASSIFICATION_COLUMNS = frozenset(
    {
        "transaction_id",
        "merchant_name",
        "merchant_key",
        "category",
        "rule_id",
        "ruleset_version",
        "classified_at",
    }
)


class PersistenceError(RuntimeError):
    """Base class for expected persistence failures."""


class IncompatibleSchemaError(PersistenceError):
    """Raised when a database does not match the supported schema."""


class DatabaseBusyError(PersistenceError):
    """Raised when bounded retries cannot acquire SQLite's write lock."""


@dataclass(frozen=True, slots=True)
class StoredStatement:
    id: str
    statement: Statement


@dataclass(frozen=True, slots=True)
class StoredStatementMetadata:
    id: str
    bank: str
    product: str
    masked_account_number: str | None
    currency: str | None
    period_start: date
    period_end: date
    statement_number: str | None
    page_number: int | None
    total_pages: int | None
    created_at: str


class StatementRepository:
    """Store normalized statements without retaining their source documents."""

    def __init__(self, database_path: str | Path) -> None:
        self._database_path = str(database_path)

    def initialize(self) -> None:
        with closing(self._connect()) as connection:
            version = connection.execute("PRAGMA user_version").fetchone()[0]
            if version > SCHEMA_VERSION:
                raise IncompatibleSchemaError("The database schema version is not supported")
            if version == 0:
                if self._table_exists(connection, "statements") or self._table_exists(
                    connection, "transactions"
                ):
                    raise IncompatibleSchemaError("The database schema is incomplete")
                with connection:
                    connection.executescript(
                        """
                    CREATE TABLE IF NOT EXISTS statements (
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
                    );

                    CREATE TABLE IF NOT EXISTS transactions (
                        id INTEGER PRIMARY KEY,
                        statement_id TEXT NOT NULL REFERENCES statements(id) ON DELETE CASCADE,
                        position INTEGER NOT NULL,
                        transaction_date TEXT NOT NULL,
                        description TEXT NOT NULL,
                        document_number TEXT,
                        branch_or_channel TEXT,
                        amount INTEGER NOT NULL,
                        movement_type TEXT NOT NULL CHECK (movement_type IN ('debit', 'credit')),
                        reported_balance INTEGER,
                        UNIQUE(statement_id, position)
                    );

                    CREATE INDEX IF NOT EXISTS transactions_statement_position
                    ON transactions(statement_id, position);
                    """
                    )
                    self._validate_schema(connection)
                    connection.execute("PRAGMA user_version = 1")
                    self._migrate_v1_to_v2(connection)
                return
            if version == 1:
                with connection:
                    self._migrate_v1_to_v2(connection)
                return
            if version != SCHEMA_VERSION:
                raise IncompatibleSchemaError("The database schema version is not supported")
            self._validate_v2_schema(connection)

    def get(self, statement_id: str) -> StoredStatement | None:
        with closing(self._connect()) as connection:
            row = connection.execute(
                "SELECT * FROM statements WHERE id = ?", (statement_id,)
            ).fetchone()
            if row is None:
                return None
            return self._stored_statement(connection, row)

    def get_by_hash(self, source_sha256: str) -> StoredStatement | None:
        with closing(self._connect()) as connection:
            row = connection.execute(
                "SELECT * FROM statements WHERE source_sha256 = ?", (source_sha256,)
            ).fetchone()
            if row is None:
                return None
            return self._stored_statement(connection, row)

    def get_many(self, statement_ids: tuple[str, ...]) -> tuple[StoredStatement, ...]:
        """Return complete stored statements in the caller's requested order."""
        if not statement_ids:
            return ()
        placeholders = ", ".join("?" for _ in statement_ids)
        with closing(self._connect()) as connection:
            rows = {
                row["id"]: row
                for row in connection.execute(
                    f"SELECT * FROM statements WHERE id IN ({placeholders})", statement_ids
                )
            }
            return tuple(
                self._stored_statement(connection, rows[statement_id])
                for statement_id in statement_ids
                if statement_id in rows
            )

    def save(self, statement: Statement, source_sha256: str, created_at: str) -> StoredStatement:
        statement_id = str(uuid4())
        classified_transactions: list[Transaction] = []
        with closing(self._connect()) as connection, connection:
            with connection:
                connection.execute(
                    """
                    INSERT INTO statements (
                        id, source_sha256, created_at, bank, product,
                        masked_account_number, currency, period_start, period_end,
                        statement_number, page_number, total_pages, opening_balance,
                        closing_balance, one_day_retention, multi_day_retention,
                        available_balance
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        statement_id,
                        source_sha256,
                        created_at,
                        statement.bank,
                        statement.product,
                        statement.masked_account_number,
                        statement.currency,
                        statement.period_start.isoformat(),
                        statement.period_end.isoformat(),
                        statement.statement_number,
                        statement.page_number,
                        statement.total_pages,
                        statement.summary.opening_balance,
                        statement.summary.closing_balance,
                        statement.summary.one_day_retention,
                        statement.summary.multi_day_retention,
                        statement.summary.available_balance,
                    ),
                )
                for position, transaction in enumerate(statement.transactions):
                    transaction_id = connection.execute(
                        """
                    INSERT INTO transactions (
                        statement_id, position, transaction_date, description,
                        document_number, branch_or_channel, amount, movement_type,
                        reported_balance
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                        (
                            statement_id,
                            position,
                            transaction.date.isoformat(),
                            transaction.description,
                            transaction.document_number,
                            transaction.branch_or_channel,
                            transaction.amount,
                            transaction.movement_type.value,
                            transaction.reported_balance,
                        ),
                    ).lastrowid
                    classification = classify_transaction(transaction, created_at)
                    connection.execute(
                        """
                        INSERT INTO transaction_classifications (
                            transaction_id, merchant_name, merchant_key, category,
                            rule_id, ruleset_version, classified_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            transaction_id,
                            classification.merchant_name,
                            classification.merchant_key,
                            classification.category.value,
                            classification.rule_id,
                            classification.ruleset_version,
                            classification.classified_at,
                        ),
                    )
                    classified_transactions.append(
                        replace(transaction, classification=classification)
                    )
        return StoredStatement(statement_id, replace(statement, transactions=tuple(classified_transactions)))

    def save_or_get(
        self, statement: Statement, source_sha256: str, created_at: str
    ) -> tuple[StoredStatement, bool]:
        for attempt in range(MAX_LOCK_RETRIES + 1):
            try:
                existing = self.get_by_hash(source_sha256)
                if existing is not None:
                    return existing, False
                try:
                    return self.save(statement, source_sha256, created_at), True
                except sqlite3.IntegrityError:
                    # A competing request committed the same unique hash.
                    continue
            except sqlite3.OperationalError as error:
                if not self._is_transient_lock(error):
                    raise
                if attempt == MAX_LOCK_RETRIES:
                    raise DatabaseBusyError("The SQLite database is busy") from error
                time.sleep(LOCK_RETRY_DELAY_SECONDS)
        raise DatabaseBusyError("The SQLite database is busy")

    def list_metadata(self, limit: int, offset: int) -> tuple[StoredStatementMetadata, ...]:
        with closing(self._connect()) as connection:
            rows = connection.execute(
                """
                SELECT id, bank, product, masked_account_number, currency,
                       period_start, period_end, statement_number, page_number,
                       total_pages, created_at
                FROM statements
                ORDER BY created_at DESC, id DESC
                LIMIT ? OFFSET ?
                """,
                (limit, offset),
            ).fetchall()
        return tuple(self._metadata(row) for row in rows)

    def delete(self, statement_id: str) -> bool:
        with closing(self._connect()) as connection, connection:
            with connection:
                deleted = connection.execute(
                    "DELETE FROM statements WHERE id = ?", (statement_id,)
                ).rowcount
        return deleted == 1

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self._database_path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    @staticmethod
    def _table_exists(connection: sqlite3.Connection, table_name: str) -> bool:
        return connection.execute(
            "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?", (table_name,)
        ).fetchone() is not None

    @classmethod
    def _validate_schema(cls, connection: sqlite3.Connection) -> None:
        if not cls._table_exists(connection, "statements") or not cls._table_exists(
            connection, "transactions"
        ):
            raise IncompatibleSchemaError("The database schema is incomplete")
        if cls._column_names(connection, "statements") != _STATEMENT_COLUMNS:
            raise IncompatibleSchemaError("The statements schema is not supported")
        if cls._column_names(connection, "transactions") != _TRANSACTION_COLUMNS:
            raise IncompatibleSchemaError("The transactions schema is not supported")
        if not cls._has_unique_index(connection, "statements", ("source_sha256",)):
            raise IncompatibleSchemaError("The statements hash constraint is missing")
        if not cls._has_unique_index(connection, "transactions", ("statement_id", "position")):
            raise IncompatibleSchemaError("The transaction position constraint is missing")
        if not cls._has_statement_cascade(connection):
            raise IncompatibleSchemaError("The transaction cascade is missing")

    @classmethod
    def _migrate_v1_to_v2(cls, connection: sqlite3.Connection) -> None:
        cls._validate_schema(connection)
        connection.execute("BEGIN")
        connection.execute(
            """
            CREATE TABLE transaction_classifications (
                transaction_id INTEGER PRIMARY KEY REFERENCES transactions(id) ON DELETE CASCADE,
                merchant_name TEXT,
                merchant_key TEXT,
                category TEXT NOT NULL,
                rule_id TEXT,
                ruleset_version TEXT NOT NULL,
                classified_at TEXT NOT NULL
            )
            """
        )
        classified_at = datetime.now(UTC).isoformat()
        for row in connection.execute(
            """
            SELECT id, transaction_date, description, document_number, branch_or_channel,
                   amount, movement_type, reported_balance
            FROM transactions
            """
        ):
            transaction = Transaction(
                date=date.fromisoformat(row["transaction_date"]),
                description=row["description"],
                document_number=row["document_number"],
                branch_or_channel=row["branch_or_channel"],
                amount=row["amount"],
                movement_type=MovementType(row["movement_type"]),
                reported_balance=row["reported_balance"],
            )
            classification = classify_transaction(transaction, classified_at)
            connection.execute(
                """
                INSERT INTO transaction_classifications (
                    transaction_id, merchant_name, merchant_key, category,
                    rule_id, ruleset_version, classified_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    row["id"],
                    classification.merchant_name,
                    classification.merchant_key,
                    classification.category.value,
                    classification.rule_id,
                    classification.ruleset_version,
                    classification.classified_at,
                ),
            )
        cls._validate_v2_schema(connection)
        connection.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")

    @classmethod
    def _validate_v2_schema(cls, connection: sqlite3.Connection) -> None:
        cls._validate_schema(connection)
        if not cls._table_exists(connection, "transaction_classifications"):
            raise IncompatibleSchemaError("The classifications schema is incomplete")
        if cls._column_names(connection, "transaction_classifications") != _CLASSIFICATION_COLUMNS:
            raise IncompatibleSchemaError("The classifications schema is not supported")
        if not cls._has_cascade(
            connection,
            "transaction_classifications",
            "transaction_id",
            "transactions",
            "id",
        ):
            raise IncompatibleSchemaError("The classification cascade is missing")

    @staticmethod
    def _column_names(connection: sqlite3.Connection, table_name: str) -> frozenset[str]:
        return frozenset(row["name"] for row in connection.execute(f"PRAGMA table_info({table_name})"))

    @staticmethod
    def _has_unique_index(
        connection: sqlite3.Connection, table_name: str, columns: tuple[str, ...]
    ) -> bool:
        for index in connection.execute(f"PRAGMA index_list({table_name})"):
            if not index["unique"]:
                continue
            index_columns = tuple(
                row["name"]
                for row in connection.execute(f"PRAGMA index_info({index['name']})")
            )
            if index_columns == columns:
                return True
        return False

    @staticmethod
    def _has_statement_cascade(connection: sqlite3.Connection) -> bool:
        return StatementRepository._has_cascade(
            connection, "transactions", "statement_id", "statements", "id"
        )

    @staticmethod
    def _has_cascade(
        connection: sqlite3.Connection,
        table_name: str,
        source_column: str,
        target_table: str,
        target_column: str,
    ) -> bool:
        return any(
            foreign_key["table"] == target_table
            and foreign_key["from"] == source_column
            and foreign_key["to"] == target_column
            and foreign_key["on_delete"] == "CASCADE"
            for foreign_key in connection.execute(f"PRAGMA foreign_key_list({table_name})")
        )

    @staticmethod
    def _is_transient_lock(error: sqlite3.OperationalError) -> bool:
        return "locked" in str(error).lower() or "busy" in str(error).lower()

    @staticmethod
    def _stored_statement(connection: sqlite3.Connection, row: sqlite3.Row) -> StoredStatement:
        transactions = connection.execute(
            """
            SELECT transactions.*, transaction_classifications.merchant_name,
                   transaction_classifications.merchant_key,
                   transaction_classifications.category,
                   transaction_classifications.rule_id,
                   transaction_classifications.ruleset_version,
                   transaction_classifications.classified_at
            FROM transactions
            JOIN transaction_classifications
            ON transaction_classifications.transaction_id = transactions.id
            WHERE statement_id = ?
            ORDER BY position
            """,
            (row["id"],),
        ).fetchall()
        return StoredStatement(
            id=row["id"],
            statement=Statement(
                bank=row["bank"],
                product=row["product"],
                masked_account_number=row["masked_account_number"],
                currency=row["currency"],
                period_start=date.fromisoformat(row["period_start"]),
                period_end=date.fromisoformat(row["period_end"]),
                statement_number=row["statement_number"],
                page_number=row["page_number"],
                total_pages=row["total_pages"],
                summary=StatementSummary(
                    opening_balance=row["opening_balance"],
                    closing_balance=row["closing_balance"],
                    one_day_retention=row["one_day_retention"],
                    multi_day_retention=row["multi_day_retention"],
                    available_balance=row["available_balance"],
                ),
                transactions=tuple(
                    Transaction(
                        date=date.fromisoformat(transaction["transaction_date"]),
                        description=transaction["description"],
                        document_number=transaction["document_number"],
                        branch_or_channel=transaction["branch_or_channel"],
                        amount=transaction["amount"],
                        movement_type=MovementType(transaction["movement_type"]),
                        reported_balance=transaction["reported_balance"],
                        classification=Classification(
                            category=Category(transaction["category"]),
                            merchant_name=transaction["merchant_name"],
                            merchant_key=transaction["merchant_key"],
                            rule_id=transaction["rule_id"],
                            ruleset_version=transaction["ruleset_version"],
                            classified_at=transaction["classified_at"],
                        ),
                    )
                    for transaction in transactions
                ),
            ),
        )

    @staticmethod
    def _metadata(row: sqlite3.Row) -> StoredStatementMetadata:
        return StoredStatementMetadata(
            id=row["id"],
            bank=row["bank"],
            product=row["product"],
            masked_account_number=row["masked_account_number"],
            currency=row["currency"],
            period_start=date.fromisoformat(row["period_start"]),
            period_end=date.fromisoformat(row["period_end"]),
            statement_number=row["statement_number"],
            page_number=row["page_number"],
            total_pages=row["total_pages"],
            created_at=row["created_at"],
        )
