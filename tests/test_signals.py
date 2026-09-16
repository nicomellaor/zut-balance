from datetime import date

from zut_balance.analysis import AnalysisStatement, analyze_statements
from zut_balance.models import Category, Classification, MovementType, Statement, StatementSummary, Transaction
from zut_balance.signals import NoticeKind, generate_signals


def _transaction(transaction_date: date, amount: int, category: Category, ruleset_version: str = "1") -> Transaction:
    return Transaction(
        transaction_date,
        "private description",
        None,
        None,
        amount,
        MovementType.DEBIT,
        None,
        Classification(category, "Store", "STORE", "rule", ruleset_version, "2026-01-01T00:00:00+00:00"),
    )


def _result(transactions: tuple[Transaction, ...], start: date = date(2026, 1, 1), end: date = date(2026, 3, 31)):
    statement = Statement("Banco", "Vista", "****1234", "PESOS", start, end, None, None, None, StatementSummary(0, 0, None, None, None), transactions)
    return analyze_statements((AnalysisStatement("one", statement),), start, end)


def test_signals_are_deterministic_and_order_coverage_before_classification() -> None:
    result = _result(
        (_transaction(date(2026, 1, 12), 100, Category.UNCATEGORIZED, "1"), _transaction(date(2026, 1, 13), 50, Category.UNCATEGORIZED, "2")),
        date(2026, 1, 10),
        date(2026, 1, 20),
    )

    signals = generate_signals(result)

    assert signals == generate_signals(result)
    assert [notice.kind for notice in signals.notices] == [NoticeKind.INCOMPLETE_COVERAGE, NoticeKind.LIMITED_CLASSIFICATION]
    classification = signals.notices[1]
    assert classification.uncategorized_amount == 150
    assert classification.ruleset_versions == ("1", "2")


def test_signals_omit_notices_without_limitations() -> None:
    result = _result(())

    assert generate_signals(result).notices == ()


def test_largest_monthly_change_uses_most_recent_month_on_absolute_tie() -> None:
    result = _result(
        (
            _transaction(date(2026, 1, 2), 100, Category.FOOD),
            _transaction(date(2026, 2, 2), 200, Category.FOOD),
            _transaction(date(2026, 3, 2), 100, Category.FOOD),
        )
    )

    highlight = generate_signals(result).largest_monthly_change

    assert highlight is not None
    assert highlight.current_month == "2026-03"
    assert highlight.absolute_change == -100


def test_signals_have_no_highlight_when_change_is_zero_or_unavailable() -> None:
    result = _result(())

    assert generate_signals(result).largest_monthly_change is None


def test_largest_monthly_change_preserves_an_unavailable_percentage() -> None:
    result = _result((_transaction(date(2026, 2, 2), 100, Category.FOOD),), end=date(2026, 2, 28))

    highlight = generate_signals(result).largest_monthly_change

    assert highlight is not None
    assert highlight.absolute_change == 100
    assert highlight.percentage_change is None
