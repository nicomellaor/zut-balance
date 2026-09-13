from dataclasses import FrozenInstanceError
from datetime import date

import pytest

from zut_balance import (
    EncryptedPdfError,
    InvalidPdfError,
    MovementType,
    Statement,
    StatementError,
    StatementSummary,
    TextExtractionError,
    Transaction,
    UnreliableExtractionError,
    UnsupportedStatementError,
)


def test_statement_models_preserve_normalized_and_optional_values() -> None:
    transaction = Transaction(
        date=date(2026, 8, 27),
        description="TRASPASO DE",
        document_number=None,
        branch_or_channel="INTERNET",
        amount=30_000,
        movement_type=MovementType.CREDIT,
        reported_balance=0,
    )
    summary = StatementSummary(
        opening_balance=61_891,
        closing_balance=68_251,
        one_day_retention=0,
        multi_day_retention=0,
        available_balance=68_251,
    )

    statement = Statement(
        bank="Banco de Chile",
        product="CUENTA VISTA",
        masked_account_number="XXXX1234",
        currency="PESOS",
        period_start=date(2026, 7, 31),
        period_end=date(2026, 8, 31),
        statement_number=None,
        page_number=1,
        total_pages=1,
        summary=summary,
        transactions=(transaction,),
    )

    assert statement.transactions[0].amount == 30_000
    assert statement.transactions[0].movement_type is MovementType.CREDIT
    assert statement.transactions[0].reported_balance == 0
    assert statement.statement_number is None


def test_statement_models_are_immutable() -> None:
    summary = StatementSummary(
        opening_balance=0,
        closing_balance=0,
        one_day_retention=None,
        multi_day_retention=None,
        available_balance=None,
    )

    with pytest.raises(FrozenInstanceError):
        summary.closing_balance = 1  # type: ignore[misc]


@pytest.mark.parametrize(
    "error_type",
    [
        InvalidPdfError,
        EncryptedPdfError,
        TextExtractionError,
        UnsupportedStatementError,
        UnreliableExtractionError,
    ],
)
def test_domain_errors_inherit_from_statement_error(
    error_type: type[StatementError],
) -> None:
    error = error_type("expected failure")

    assert isinstance(error, StatementError)
    assert str(error) == "expected failure"
