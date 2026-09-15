from datetime import date

from zut_balance.analysis import AnalysisStatement, analyze_statements
from zut_balance.insights import INSIGHT_LIMIT, InsightKind, generate_insights
from zut_balance.models import Category, Classification, MovementType, Statement, StatementSummary, Transaction


def _transaction(
    transaction_date: date,
    amount: int,
    category: Category,
    merchant_key: str | None = None,
    merchant_name: str | None = None,
    ruleset_version: str = "1",
) -> Transaction:
    return Transaction(
        transaction_date,
        "private description",
        None,
        None,
        amount,
        MovementType.DEBIT,
        None,
        Classification(category, merchant_name, merchant_key, "rule" if merchant_key else None, ruleset_version, "2026-01-01T00:00:00+00:00"),
    )


def _result(transactions: tuple[Transaction, ...], start: date = date(2026, 1, 1), end: date = date(2026, 3, 31)):
    statement = Statement("Banco", "Vista", "****1234", "PESOS", start, end, None, None, None, StatementSummary(0, 0, None, None, None), transactions)
    return analyze_statements((AnalysisStatement("one", statement),), start, end)


def test_insights_are_deterministic_and_prioritized_with_evidence() -> None:
    result = _result(
        (
            _transaction(date(2026, 1, 2), 100, Category.FOOD, "MARKET", "Market"),
            _transaction(date(2026, 1, 3), 40, Category.UNCATEGORIZED),
            _transaction(date(2026, 2, 2), 200, Category.FOOD, "MARKET", "Market"),
            _transaction(date(2026, 3, 2), 300, Category.FOOD, "MARKET", "Market"),
        )
    )

    insights = generate_insights(result)

    assert insights == generate_insights(result)
    assert [item.kind for item in insights] == [
        InsightKind.DATA_QUALITY_WARNING,
        InsightKind.PERIOD_SUMMARY,
        InsightKind.MONTHLY_CHANGE,
        InsightKind.LEADING_CATEGORY,
        InsightKind.LEADING_MERCHANT,
    ]
    assert [item.priority for item in insights] == [1, 2, 3, 4, 5]
    assert all(item.evidence for item in insights)
    assert len(insights) == INSIGHT_LIMIT


def test_insights_warn_about_partial_coverage_and_empty_spending() -> None:
    result = _result((), date(2026, 1, 10), date(2026, 1, 20))

    insights = generate_insights(result)

    assert [item.kind for item in insights] == [InsightKind.COVERAGE_WARNING, InsightKind.PERIOD_SUMMARY]
    assert "cobertura disponible" in insights[1].body
    assert insights[0].caveat is not None


def test_monthly_change_uses_most_recent_month_on_absolute_tie() -> None:
    result = _result(
        (
            _transaction(date(2026, 1, 2), 100, Category.FOOD),
            _transaction(date(2026, 2, 2), 200, Category.FOOD),
            _transaction(date(2026, 3, 2), 100, Category.FOOD),
        )
    )

    change = next(item for item in generate_insights(result) if item.kind == InsightKind.MONTHLY_CHANGE)

    assert dict((item.label, item.value) for item in change.evidence)["mes_actual"] == "2026-03"


def test_category_tie_excludes_uncategorized() -> None:
    result = _result(
        (
            _transaction(date(2026, 1, 2), 100, Category.FOOD),
            _transaction(date(2026, 1, 3), 100, Category.HEALTH),
            _transaction(date(2026, 1, 4), 200, Category.UNCATEGORIZED),
        )
    )

    insights = generate_insights(result)
    category = next(item for item in insights if item.kind == InsightKind.LEADING_CATEGORY)

    assert dict((item.label, item.value) for item in category.evidence)["categoria"] == "alimentacion"


def test_recurrence_is_not_described_as_a_subscription() -> None:
    result = _result(
        (
            _transaction(date(2026, 1, 31), 10, Category.SERVICES, "VIDEO", "Video"),
            _transaction(date(2026, 2, 28), 11, Category.SERVICES, "VIDEO", "Video"),
            _transaction(date(2026, 3, 31), 12, Category.SERVICES, "VIDEO", "Video"),
        )
    )

    recurrence = next(item for item in generate_insights(result) if item.kind == InsightKind.RECURRENCE_CANDIDATE)

    assert "suscrip" not in f"{recurrence.title} {recurrence.body} {recurrence.caveat}".lower()
