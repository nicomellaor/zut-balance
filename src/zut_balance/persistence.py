"""SQLite persistence for normalized bank statements."""

from dataclasses import dataclass
from datetime import date
from pathlib import Path
import sqlite3
from contextlib import closing
from uuid import uuid4

from .models import MovementType, Statement, StatementSummary, Transaction


SCHEMA_VERSION = 1


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
        with closing(self._connect()) as connection, connection:
            version = connection.execute("PRAGMA user_version").fetchone()[0]
            if version > SCHEMA_VERSION:
                raise RuntimeError("The database schema version is not supported")
            if version == 0:
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
                connection.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")

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

    def save(self, statement: Statement, source_sha256: str, created_at: str) -> StoredStatement:
        statement_id = str(uuid4())
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
                connection.executemany(
                    """
                    INSERT INTO transactions (
                        statement_id, position, transaction_date, description,
                        document_number, branch_or_channel, amount, movement_type,
                        reported_balance
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    [
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
                        )
                        for position, transaction in enumerate(statement.transactions)
                    ],
                )
        return StoredStatement(statement_id, statement)

    def save_or_get(
        self, statement: Statement, source_sha256: str, created_at: str
    ) -> tuple[StoredStatement, bool]:
        existing = self.get_by_hash(source_sha256)
        if existing is not None:
            return existing, False
        try:
            return self.save(statement, source_sha256, created_at), True
        except sqlite3.IntegrityError:
            existing = self.get_by_hash(source_sha256)
            if existing is not None:
                return existing, False
            raise

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
    def _stored_statement(connection: sqlite3.Connection, row: sqlite3.Row) -> StoredStatement:
        transactions = connection.execute(
            "SELECT * FROM transactions WHERE statement_id = ? ORDER BY position",
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
