from datetime import date, timedelta

import pytest

from zut_balance.analysis import (
    AnalysisError,
    AnalysisStatement,
    RecurrenceCadence,
    analyze_statements,
)
from zut_balance.models import Category, Classification, MovementType, Statement, StatementSummary, Transaction


def _classification(
    category: Category, merchant_key: str | None = None, merchant_name: str | None = None
) -> Classification:
    return Classification(category, merchant_name, merchant_key, "rule" if merchant_key else None, "1", "2026-01-01T00:00:00+00:00")


def _transaction(
    transaction_date: date,
    amount: int,
    category: Category,
    merchant_key: str | None = None,
    merchant_name: str | None = None,
    movement_type: MovementType = MovementType.DEBIT,
) -> Transaction:
    return Transaction(
        transaction_date,
        "private description",
        None,
        None,
        amount,
        movement_type,
        None,
        _classification(category, merchant_key, merchant_name),
    )


def _statement(
    statement_id: str,
    period_start: date,
    period_end: date,
    transactions: tuple[Transaction, ...],
    **overrides: object,
) -> AnalysisStatement:
    statement = Statement(
        bank=overrides.get("bank", "Banco"),
        product=overrides.get("product", "Vista"),
        masked_account_number=overrides.get("account", "****1234"),
        currency=overrides.get("currency", "PESOS"),
        period_start=period_start,
        period_end=period_end,
        statement_number=None,
        page_number=None,
        total_pages=None,
        summary=StatementSummary(0, 0, None, None, None),
        transactions=transactions,
    )
    return AnalysisStatement(statement_id, statement)


def test_analysis_reconciles_spending_credits_exclusions_and_merchant_coverage() -> None:
    statement = _statement(
        "one",
        date(2026, 1, 1),
        date(2026, 1, 31),
        (
            _transaction(date(2026, 1, 2), 100, Category.FOOD, "MARKET", "Market"),
            _transaction(date(2026, 1, 3), 40, Category.UNCATEGORIZED),
            _transaction(date(2026, 1, 4), 20, Category.FEES),
            _transaction(date(2026, 1, 5), 50, Category.TRANSFERS),
            _transaction(date(2026, 1, 6), 70, Category.UNCATEGORIZED, movement_type=MovementType.CREDIT),
        ),
    )

    result = analyze_statements((statement,), date(2026, 1, 1), date(2026, 1, 31))

    assert result.spending.amount == 160
    assert result.spending.count == 3
    assert result.credits.amount == 70
    assert result.excluded_debits.amount == 50
    assert result.uncategorized.amount == 40
    assert result.merchant_coverage[0].amount == 100
    assert result.merchant_coverage[1].amount == 60


def test_analysis_returns_months_and_safe_variations() -> None:
    statement = _statement(
        "one",
        date(2026, 1, 1),
        date(2026, 3, 31),
        (
            _transaction(date(2026, 1, 2), 100, Category.FOOD),
            _transaction(date(2026, 3, 2), 200, Category.FOOD),
        ),
    )

    result = analyze_statements((statement,), date(2026, 1, 1), date(2026, 3, 31))

    assert [(month.month, month.amount, month.absolute_change, month.percentage_change) for month in result.monthly] == [
        ("2026-01", 100, None, None),
        ("2026-02", 0, -100, "-100.00"),
        ("2026-03", 200, 200, None),
    ]
    assert result.coverage.partial_months == ()


def test_analysis_uses_merchant_key_for_top_merchants_and_monthly_recurrence() -> None:
    statement = _statement(
        "one",
        date(2026, 1, 1),
        date(2026, 3, 31),
        (
            _transaction(date(2026, 1, 31), 100, Category.SERVICES, "VIDEO", "Video"),
            _transaction(date(2026, 2, 28), 101, Category.SERVICES, "VIDEO", "Video"),
            _transaction(date(2026, 3, 31), 102, Category.SERVICES, "VIDEO", "Video"),
            _transaction(date(2026, 1, 2), 500, Category.SERVICES, "SHOP", "Shop"),
        ),
    )

    result = analyze_statements((statement,), date(2026, 1, 1), date(2026, 3, 31))

    assert [(merchant.merchant_name, merchant.amount) for merchant in result.top_merchants] == [
        ("Shop", 500),
        ("Video", 303),
    ]
    assert result.recurrence_candidates[0].cadence is RecurrenceCadence.MONTHLY
    assert result.recurrence_candidates[0].average_amount == 101


def test_analysis_reports_gaps_and_partial_months() -> None:
    statements = (
        _statement("one", date(2026, 1, 10), date(2026, 1, 20), ()),
        _statement("two", date(2026, 3, 1), date(2026, 3, 31), ()),
    )

    result = analyze_statements(statements, date(2026, 1, 1), date(2026, 3, 31))

    assert result.coverage.covered_ranges == (
        (date(2026, 1, 10), date(2026, 1, 20)),
        (date(2026, 3, 1), date(2026, 3, 31)),
    )
    assert result.coverage.gaps == ((date(2026, 1, 1), date(2026, 1, 9)), (date(2026, 1, 21), date(2026, 2, 28)))
    assert result.coverage.partial_months == ("2026-01", "2026-02")


def test_analysis_detects_weekly_candidates_and_rejects_irregular_sequences() -> None:
    statement = _statement(
        "one",
        date(2026, 1, 1),
        date(2026, 1, 31),
        (
            _transaction(date(2026, 1, 2), 10, Category.SERVICES, "WEEKLY", "Weekly"),
            _transaction(date(2026, 1, 9), 11, Category.SERVICES, "WEEKLY", "Weekly"),
            _transaction(date(2026, 1, 16), 12, Category.SERVICES, "WEEKLY", "Weekly"),
            _transaction(date(2026, 1, 3), 20, Category.SERVICES, "IRREGULAR", "Irregular"),
            _transaction(date(2026, 1, 10), 20, Category.SERVICES, "IRREGULAR", "Irregular"),
            _transaction(date(2026, 1, 25), 20, Category.SERVICES, "IRREGULAR", "Irregular"),
        ),
    )

    result = analyze_statements((statement,), date(2026, 1, 1), date(2026, 1, 31))

    assert [(item.merchant_name, item.cadence, item.average_amount) for item in result.recurrence_candidates] == [
        ("Weekly", RecurrenceCadence.WEEKLY, 11)
    ]


@pytest.mark.parametrize(
    ("override", "message"),
    [
        ({"bank": "Otro banco"}, "incompatible"),
        ({"product": "Otro producto"}, "incompatible"),
        ({"currency": "USD"}, "incompatible"),
        ({"account": "****9876"}, "ambiguous"),
    ],
)
def test_analysis_rejects_incompatible_multi_statement_accounts(
    override: dict[str, str], message: str
) -> None:
    statements = (
        _statement("one", date(2026, 1, 1), date(2026, 1, 31), ()),
        _statement("two", date(2026, 2, 1), date(2026, 2, 28), (), **override),
    )

    with pytest.raises(AnalysisError, match=message):
        analyze_statements(statements, date(2026, 1, 1), date(2026, 2, 28))


@pytest.mark.parametrize(
    "statements, from_date, to_date",
    [
        ((), date(2026, 1, 1), date(2026, 1, 1)),
        (
            (
                _statement("one", date(2026, 1, 1), date(2026, 1, 31), ()),
                _statement("two", date(2026, 1, 30), date(2026, 2, 28), ()),
            ),
            date(2026, 1, 1),
            date(2026, 2, 28),
        ),
    ],
)
def test_analysis_rejects_empty_or_truly_overlapping_scope(
    statements: tuple[AnalysisStatement, ...], from_date: date, to_date: date
) -> None:
    with pytest.raises(AnalysisError):
        analyze_statements(statements, from_date, to_date)


def test_analysis_accepts_shared_period_boundary_and_counts_each_statement() -> None:
    statements = (
        _statement(
            "july",
            date(2026, 7, 1),
            date(2026, 7, 31),
            (_transaction(date(2026, 7, 31), 100, Category.FOOD),),
        ),
        _statement(
            "august",
            date(2026, 7, 31),
            date(2026, 8, 31),
            (_transaction(date(2026, 7, 31), 200, Category.FOOD),),
        ),
    )

    result = analyze_statements(statements, date(2026, 7, 1), date(2026, 8, 31))

    assert result.scope.statement_ids == ("july", "august")
    assert result.spending.amount == 300
    assert result.coverage.gaps == ()


def test_analysis_has_no_statement_or_month_range_limit() -> None:
    start = date(2020, 1, 1)
    statements = tuple(
        _statement(
            str(index),
            start + timedelta(days=index),
            start + timedelta(days=index),
            (),
        )
        for index in range(101)
    )

    result = analyze_statements(statements, start, date(2030, 1, 1))

    assert len(result.scope.statement_ids) == 101
    assert result.scope.to_date == date(2030, 1, 1)
