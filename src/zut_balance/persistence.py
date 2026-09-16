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


SCHEMA_VERSION = 3
MAX_LOCK_RETRIES = 3
LOCK_RETRY_DELAY_SECONDS = 0.01

_V1_STATEMENT_COLUMN_SEQUENCE = (
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
)
_V1_STATEMENT_COLUMNS = frozenset(_V1_STATEMENT_COLUMN_SEQUENCE)
_STATEMENT_COLUMNS = _V1_STATEMENT_COLUMNS | frozenset({"account_id"})
_ACCOUNT_COLUMNS = frozenset(
    {
        "id",
        "bank",
        "product",
        "currency",
        "masked_account_number",
        "identity_status",
        "created_at",
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


@dataclass(frozen=True, slots=True)
class StoredAccountMetadata:
    id: str
    bank: str
    product: str
    currency: str | None
    masked_account_number: str | None
    identity_status: str
    statement_count: int
    period_start: date
    period_end: date


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
                    CREATE TABLE accounts (
                        id TEXT PRIMARY KEY,
                        bank TEXT NOT NULL,
                        product TEXT NOT NULL,
                        currency TEXT,
                        masked_account_number TEXT,
                        identity_status TEXT NOT NULL CHECK (
                            (identity_status = 'visible_mask' AND masked_account_number GLOB '*[0-9]*')
                            OR identity_status = 'ambiguous'
                        ),
                        created_at TEXT NOT NULL
                    );

                    CREATE UNIQUE INDEX accounts_visible_identity_with_currency
                    ON accounts(bank, product, currency, masked_account_number)
                    WHERE identity_status = 'visible_mask' AND currency IS NOT NULL;

                    CREATE UNIQUE INDEX accounts_visible_identity_without_currency
                    ON accounts(bank, product, masked_account_number)
                    WHERE identity_status = 'visible_mask' AND currency IS NULL;

                    CREATE TABLE statements (
                        id TEXT PRIMARY KEY,
                        account_id TEXT NOT NULL REFERENCES accounts(id),
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

                    CREATE TABLE transaction_classifications (
                        transaction_id INTEGER PRIMARY KEY REFERENCES transactions(id) ON DELETE CASCADE,
                        merchant_name TEXT,
                        merchant_key TEXT,
                        category TEXT NOT NULL,
                        rule_id TEXT,
                        ruleset_version TEXT NOT NULL,
                        classified_at TEXT NOT NULL
                    );

                    CREATE INDEX statements_account_period
                    ON statements(account_id, period_start, period_end, id);
                    """
                    )
                    self._validate_v3_schema(connection)
                    connection.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")
                return
            if version in (1, 2):
                self._migrate_to_v3(connection, version)
                return
            if version != SCHEMA_VERSION:
                raise IncompatibleSchemaError("The database schema version is not supported")
            self._validate_v3_schema(connection)

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

    def list_accounts(self) -> tuple[StoredAccountMetadata, ...]:
        with closing(self._connect()) as connection:
            rows = connection.execute(
                """
                SELECT accounts.*, COUNT(statements.id) AS statement_count,
                       MIN(statements.period_start) AS period_start,
                       MAX(statements.period_end) AS period_end
                FROM accounts JOIN statements ON statements.account_id = accounts.id
                GROUP BY accounts.id
                ORDER BY period_end DESC, period_start DESC, bank, product, accounts.id
                """
            ).fetchall()
        return tuple(self._account_metadata(row) for row in rows)

    def get_account(self, account_id: str) -> StoredAccountMetadata | None:
        with closing(self._connect()) as connection:
            row = connection.execute(
                """
                SELECT accounts.*, COUNT(statements.id) AS statement_count,
                       MIN(statements.period_start) AS period_start,
                       MAX(statements.period_end) AS period_end
                FROM accounts JOIN statements ON statements.account_id = accounts.id
                WHERE accounts.id = ?
                GROUP BY accounts.id
                """,
                (account_id,),
            ).fetchone()
        return None if row is None else self._account_metadata(row)

    def account_id_for_statement(self, statement_id: str) -> str | None:
        with closing(self._connect()) as connection:
            row = connection.execute(
                "SELECT account_id FROM statements WHERE id = ?", (statement_id,)
            ).fetchone()
        return None if row is None else row["account_id"]

    def history_for_account(
        self,
        account_id: str,
        from_date: date | None = None,
        to_date: date | None = None,
    ) -> tuple[StoredStatement, ...]:
        conditions = ["account_id = ?"]
        parameters: list[str] = [account_id]
        if from_date is not None:
            conditions.append("period_end >= ?")
            parameters.append(from_date.isoformat())
        if to_date is not None:
            conditions.append("period_start <= ?")
            parameters.append(to_date.isoformat())
        with closing(self._connect()) as connection:
            rows = connection.execute(
                f"SELECT * FROM statements WHERE {' AND '.join(conditions)} "
                "ORDER BY period_start, period_end, id",
                parameters,
            ).fetchall()
            return tuple(self._stored_statement(connection, row) for row in rows)

    def save(self, statement: Statement, source_sha256: str, created_at: str) -> StoredStatement:
        statement_id = str(uuid4())
        classified_transactions: list[Transaction] = []
        with closing(self._connect()) as connection, connection:
            with connection:
                account_id = self._resolve_account(connection, statement, created_at)
                connection.execute(
                    """
                    INSERT INTO statements (
                        id, account_id, source_sha256, created_at, bank, product,
                        masked_account_number, currency, period_start, period_end,
                        statement_number, page_number, total_pages, opening_balance,
                        closing_balance, one_day_retention, multi_day_retention,
                        available_balance
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        statement_id,
                        account_id,
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
                row = connection.execute(
                    "SELECT account_id FROM statements WHERE id = ?", (statement_id,)
                ).fetchone()
                if row is None:
                    return False
                deleted = connection.execute(
                    "DELETE FROM statements WHERE id = ?", (statement_id,)
                ).rowcount
                connection.execute(
                    """
                    DELETE FROM accounts
                    WHERE id = ? AND NOT EXISTS (
                        SELECT 1 FROM statements WHERE account_id = ?
                    )
                    """,
                    (row["account_id"], row["account_id"]),
                )
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
    def _validate_v1_schema(cls, connection: sqlite3.Connection) -> None:
        if not cls._table_exists(connection, "statements") or not cls._table_exists(
            connection, "transactions"
        ):
            raise IncompatibleSchemaError("The database schema is incomplete")
        if cls._column_names(connection, "statements") != _V1_STATEMENT_COLUMNS:
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
        cls._validate_v1_schema(connection)
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

    @classmethod
    def _validate_v2_schema(cls, connection: sqlite3.Connection) -> None:
        cls._validate_v1_schema(connection)
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

    @classmethod
    def _validate_v3_schema(cls, connection: sqlite3.Connection) -> None:
        if not cls._table_exists(connection, "accounts"):
            raise IncompatibleSchemaError("The accounts schema is incomplete")
        if cls._column_names(connection, "accounts") != _ACCOUNT_COLUMNS:
            raise IncompatibleSchemaError("The accounts schema is not supported")
        if cls._column_names(connection, "statements") != _STATEMENT_COLUMNS:
            raise IncompatibleSchemaError("The statements schema is not supported")
        if cls._column_names(connection, "transactions") != _TRANSACTION_COLUMNS:
            raise IncompatibleSchemaError("The transactions schema is not supported")
        if cls._column_names(connection, "transaction_classifications") != _CLASSIFICATION_COLUMNS:
            raise IncompatibleSchemaError("The classifications schema is not supported")
        if not cls._has_cascade(connection, "transactions", "statement_id", "statements", "id"):
            raise IncompatibleSchemaError("The transaction cascade is missing")
        if not cls._has_cascade(
            connection,
            "transaction_classifications",
            "transaction_id",
            "transactions",
            "id",
        ):
            raise IncompatibleSchemaError("The classification cascade is missing")
        if not cls._has_unique_index(connection, "statements", ("source_sha256",)):
            raise IncompatibleSchemaError("The statements hash constraint is missing")
        if not cls._has_unique_index(connection, "transactions", ("statement_id", "position")):
            raise IncompatibleSchemaError("The transaction position constraint is missing")
        if not cls._has_index(connection, "statements", ("account_id", "period_start", "period_end", "id")):
            raise IncompatibleSchemaError("The account period index is missing")
        expected_indexes = {
            "accounts_visible_identity_with_currency": (
                "bank,product,currency,masked_account_number",
                "identity_status='visible_mask'andcurrencyisnotnull",
            ),
            "accounts_visible_identity_without_currency": (
                "bank,product,masked_account_number",
                "identity_status='visible_mask'andcurrencyisnull",
            ),
        }
        for name, (columns, predicate) in expected_indexes.items():
            sql = cls._index_sql(connection, name)
            normalized_sql = "".join(sql.lower().split()) if sql is not None else ""
            if not normalized_sql.startswith("createuniqueindex") or columns not in normalized_sql or predicate not in normalized_sql:
                raise IncompatibleSchemaError("The visible account constraint is missing")
        if not cls._has_foreign_key(connection, "statements", "account_id", "accounts", "id"):
            raise IncompatibleSchemaError("The statement account foreign key is missing")

    @classmethod
    def _migrate_to_v3(cls, connection: sqlite3.Connection, version: int) -> None:
        if version == 1:
            cls._validate_v1_schema(connection)
        else:
            cls._validate_v2_schema(connection)
        connection.execute("PRAGMA foreign_keys = OFF")
        try:
            connection.execute("BEGIN")
            if version == 1:
                cls._migrate_v1_to_v2(connection)
            cls._validate_v2_schema(connection)
            connection.execute(
                """
                CREATE TABLE accounts (
                    id TEXT PRIMARY KEY,
                    bank TEXT NOT NULL,
                    product TEXT NOT NULL,
                    currency TEXT,
                    masked_account_number TEXT,
                    identity_status TEXT NOT NULL CHECK (
                        (identity_status = 'visible_mask' AND masked_account_number GLOB '*[0-9]*')
                        OR identity_status = 'ambiguous'
                    ),
                    created_at TEXT NOT NULL
                )
                """
            )
            cls._create_account_indexes(connection)
            connection.execute(
                """
                CREATE TABLE statements_v3 (
                    id TEXT PRIMARY KEY,
                    account_id TEXT NOT NULL REFERENCES accounts(id),
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
            visible_accounts: dict[tuple[str, str, str | None, str], str] = {}
            statement_rows = connection.execute("SELECT * FROM statements ORDER BY id").fetchall()
            for row in statement_rows:
                account = row["masked_account_number"]
                if account is not None and any(character.isdigit() for character in account):
                    key = (row["bank"], row["product"], row["currency"], account)
                    account_id = visible_accounts.get(key)
                    if account_id is None:
                        account_id = str(uuid4())
                        visible_accounts[key] = account_id
                        status = "visible_mask"
                    else:
                        status = None
                else:
                    account_id = str(uuid4())
                    status = "ambiguous"
                if status is not None:
                    connection.execute(
                        """
                        INSERT INTO accounts (
                            id, bank, product, currency, masked_account_number,
                            identity_status, created_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            account_id,
                            row["bank"],
                            row["product"],
                            row["currency"],
                            account,
                            status,
                            row["created_at"],
                        ),
                    )
                values = [row[column] for column in _V1_STATEMENT_COLUMN_SEQUENCE]
                connection.execute(
                    f"INSERT INTO statements_v3 (account_id, {', '.join(_V1_STATEMENT_COLUMN_SEQUENCE)}) "
                    f"VALUES ({', '.join('?' for _ in range(len(values) + 1))})",
                    [account_id, *values],
                )
            connection.execute("DROP TABLE statements")
            connection.execute("ALTER TABLE statements_v3 RENAME TO statements")
            connection.execute(
                "CREATE INDEX statements_account_period ON statements(account_id, period_start, period_end, id)"
            )
            cls._validate_v3_schema(connection)
            if connection.execute("PRAGMA foreign_key_check").fetchone() is not None:
                raise IncompatibleSchemaError("The migrated foreign keys are invalid")
            connection.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")
            connection.commit()
        except BaseException:
            connection.rollback()
            raise
        finally:
            connection.execute("PRAGMA foreign_keys = ON")

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
    def _has_index(
        connection: sqlite3.Connection, table_name: str, columns: tuple[str, ...]
    ) -> bool:
        return any(
            tuple(row["name"] for row in connection.execute(f"PRAGMA index_info({index['name']})"))
            == columns
            for index in connection.execute(f"PRAGMA index_list({table_name})")
        )

    @staticmethod
    def _index_sql(connection: sqlite3.Connection, index_name: str) -> str | None:
        row = connection.execute(
            "SELECT sql FROM sqlite_master WHERE type = 'index' AND name = ?", (index_name,)
        ).fetchone()
        return None if row is None else row["sql"]

    @staticmethod
    def _has_foreign_key(
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
            for foreign_key in connection.execute(f"PRAGMA foreign_key_list({table_name})")
        )

    @staticmethod
    def _create_account_indexes(connection: sqlite3.Connection) -> None:
        connection.execute(
            """
            CREATE UNIQUE INDEX accounts_visible_identity_with_currency
            ON accounts(bank, product, currency, masked_account_number)
            WHERE identity_status = 'visible_mask' AND currency IS NOT NULL
            """
        )
        connection.execute(
            """
            CREATE UNIQUE INDEX accounts_visible_identity_without_currency
            ON accounts(bank, product, masked_account_number)
            WHERE identity_status = 'visible_mask' AND currency IS NULL
            """
        )

    @staticmethod
    def _resolve_account(
        connection: sqlite3.Connection, statement: Statement, created_at: str
    ) -> str:
        account = statement.masked_account_number
        visible = account is not None and any(character.isdigit() for character in account)
        if not visible:
            account_id = str(uuid4())
            connection.execute(
                """
                INSERT INTO accounts (
                    id, bank, product, currency, masked_account_number, identity_status, created_at
                ) VALUES (?, ?, ?, ?, ?, 'ambiguous', ?)
                """,
                (account_id, statement.bank, statement.product, statement.currency, account, created_at),
            )
            return account_id
        row = connection.execute(
            """
            SELECT id FROM accounts
            WHERE bank = ? AND product = ? AND currency IS ? AND masked_account_number = ?
              AND identity_status = 'visible_mask'
            """,
            (statement.bank, statement.product, statement.currency, account),
        ).fetchone()
        if row is not None:
            return row["id"]
        account_id = str(uuid4())
        try:
            connection.execute(
                """
                INSERT INTO accounts (
                    id, bank, product, currency, masked_account_number, identity_status, created_at
                ) VALUES (?, ?, ?, ?, ?, 'visible_mask', ?)
                """,
                (account_id, statement.bank, statement.product, statement.currency, account, created_at),
            )
        except sqlite3.IntegrityError:
            row = connection.execute(
                """
                SELECT id FROM accounts
                WHERE bank = ? AND product = ? AND currency IS ? AND masked_account_number = ?
                  AND identity_status = 'visible_mask'
                """,
                (statement.bank, statement.product, statement.currency, account),
            ).fetchone()
            if row is None:
                raise
            return row["id"]
        return account_id

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

    @staticmethod
    def _account_metadata(row: sqlite3.Row) -> StoredAccountMetadata:
        return StoredAccountMetadata(
            id=row["id"],
            bank=row["bank"],
            product=row["product"],
            currency=row["currency"],
            masked_account_number=row["masked_account_number"],
            identity_status=row["identity_status"],
            statement_count=row["statement_count"],
            period_start=date.fromisoformat(row["period_start"]),
            period_end=date.fromisoformat(row["period_end"]),
        )
