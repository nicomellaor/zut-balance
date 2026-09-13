"""Immutable normalized bank statement models."""

from dataclasses import dataclass
from datetime import date
from enum import StrEnum


class MovementType(StrEnum):
    """The direction of a transaction amount."""

    DEBIT = "debit"
    CREDIT = "credit"


@dataclass(frozen=True, slots=True)
class StatementSummary:
    """Balances and retentions reported by a statement, in CLP."""

    opening_balance: int
    closing_balance: int
    one_day_retention: int | None
    multi_day_retention: int | None
    available_balance: int | None


@dataclass(frozen=True, slots=True)
class StatementMetadata:
    """Statement data extracted before transaction parsing."""

    bank: str
    product: str
    masked_account_number: str | None
    currency: str | None
    period_start: date
    period_end: date
    statement_number: str | None
    page_number: int | None
    total_pages: int | None
    summary: StatementSummary


@dataclass(frozen=True, slots=True)
class Transaction:
    """A normalized statement transaction, with non-negative amount in CLP."""

    date: date
    description: str
    document_number: str | None
    branch_or_channel: str | None
    amount: int
    movement_type: MovementType
    reported_balance: int | None


@dataclass(frozen=True, slots=True)
class Statement:
    """A normalized bank statement without the full account identifier."""

    bank: str
    product: str
    masked_account_number: str | None
    currency: str | None
    period_start: date
    period_end: date
    statement_number: str | None
    page_number: int | None
    total_pages: int | None
    summary: StatementSummary
    transactions: tuple[Transaction, ...]
