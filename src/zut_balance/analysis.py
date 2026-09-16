"""Pure deterministic spending analysis over classified statements."""

from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP
from enum import StrEnum
from calendar import monthrange

from .models import Category, Statement, Transaction


TOP_MERCHANT_LIMIT = 10
_EXPENSE_CATEGORIES = frozenset(
    {
        Category.FOOD,
        Category.TRANSPORT,
        Category.HEALTH,
        Category.ENTERTAINMENT,
        Category.HOME,
        Category.SERVICES,
        Category.SHOPPING,
        Category.FEES,
        Category.UNCATEGORIZED,
    }
)


class AnalysisError(ValueError):
    """Raised when a statement selection cannot be analyzed safely."""


class AnalysisValidationError(AnalysisError):
    """Raised when the requested analysis parameters are invalid."""


class AnalysisScopeError(AnalysisError):
    """Raised when persisted statements cannot form a safe aggregate scope."""


class RecurrenceCadence(StrEnum):
    WEEKLY = "weekly"
    MONTHLY = "monthly"


@dataclass(frozen=True, slots=True)
class AnalysisStatement:
    id: str
    statement: Statement


@dataclass(frozen=True, slots=True)
class AmountCount:
    amount: int
    count: int


@dataclass(frozen=True, slots=True)
class CategoryTotal:
    category: Category
    amount: int
    count: int


@dataclass(frozen=True, slots=True)
class Coverage:
    covered_ranges: tuple[tuple[date, date], ...]
    gaps: tuple[tuple[date, date], ...]
    partial_months: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class MonthlyTotal:
    month: str
    amount: int
    count: int
    categories: tuple[CategoryTotal, ...]
    absolute_change: int | None
    percentage_change: str | None


@dataclass(frozen=True, slots=True)
class TopMerchant:
    merchant_name: str | None
    amount: int
    count: int


@dataclass(frozen=True, slots=True)
class RecurrenceCandidate:
    merchant_name: str | None
    cadence: RecurrenceCadence
    dates: tuple[date, ...]
    amounts: tuple[int, ...]
    count: int
    minimum_amount: int
    average_amount: int
    maximum_amount: int


@dataclass(frozen=True, slots=True)
class AnalysisScope:
    statement_ids: tuple[str, ...]
    from_date: date
    to_date: date
    currency: str
    ruleset_versions: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class AnalysisResult:
    scope: AnalysisScope
    coverage: Coverage
    spending: AmountCount
    credits: AmountCount
    excluded_debits: AmountCount
    uncategorized: AmountCount
    merchant_coverage: tuple[AmountCount, AmountCount]
    categories: tuple[CategoryTotal, ...]
    monthly: tuple[MonthlyTotal, ...]
    top_merchants: tuple[TopMerchant, ...]
    recurrence_candidates: tuple[RecurrenceCandidate, ...]


def analyze_statements(
    statements: tuple[AnalysisStatement, ...], from_date: date, to_date: date
) -> AnalysisResult:
    """Analyze a compatible, non-overlapping selection without mutating it."""
    scope = _validate_scope(statements, from_date, to_date)
    coverage = _coverage(statements, from_date, to_date)
    transactions = tuple(
        transaction
        for item in statements
        for transaction in item.statement.transactions
        if from_date <= transaction.date <= to_date
    )
    spending_transactions = tuple(
        transaction for transaction in transactions if _is_spending(transaction)
    )
    credits = tuple(transaction for transaction in transactions if transaction.movement_type == "credit")
    excluded_debits = tuple(
        transaction
        for transaction in transactions
        if transaction.movement_type == "debit" and not _is_spending(transaction)
    )
    uncategorized = tuple(
        transaction
        for transaction in spending_transactions
        if transaction.classification is not None
        and transaction.classification.category == Category.UNCATEGORIZED
    )
    with_merchant = tuple(
        transaction
        for transaction in spending_transactions
        if transaction.classification is not None and transaction.classification.merchant_key is not None
    )
    without_merchant = tuple(
        transaction
        for transaction in spending_transactions
        if transaction.classification is None or transaction.classification.merchant_key is None
    )
    return AnalysisResult(
        scope=scope,
        coverage=coverage,
        spending=_amount_count(spending_transactions),
        credits=_amount_count(credits),
        excluded_debits=_amount_count(excluded_debits),
        uncategorized=_amount_count(uncategorized),
        merchant_coverage=(_amount_count(with_merchant), _amount_count(without_merchant)),
        categories=_category_totals(spending_transactions),
        monthly=_monthly_totals(spending_transactions, coverage, from_date, to_date),
        top_merchants=_top_merchants(with_merchant),
        recurrence_candidates=_recurrences(with_merchant),
    )


def _validate_scope(
    statements: tuple[AnalysisStatement, ...], from_date: date, to_date: date
) -> AnalysisScope:
    if not statements:
        raise AnalysisValidationError("statements must not be empty")
    ids = tuple(item.id for item in statements)
    if len(set(ids)) != len(ids):
        raise AnalysisValidationError("statement_ids must be unique")
    if from_date > to_date:
        raise AnalysisValidationError("from must not be after to")
    first = statements[0].statement
    if first.currency != "PESOS":
        raise AnalysisScopeError("currency is not supported")
    for item in statements[1:]:
        statement = item.statement
        if (statement.bank, statement.product, statement.currency) != (
            first.bank,
            first.product,
            first.currency,
        ):
            raise AnalysisScopeError("statements are incompatible")
        if not _has_visible_account(first.masked_account_number) or (
            statement.masked_account_number != first.masked_account_number
            or not _has_visible_account(statement.masked_account_number)
        ):
            raise AnalysisScopeError("statement account scope is ambiguous")
    periods = sorted((item.statement.period_start, item.statement.period_end) for item in statements)
    if any(current[0] < previous[1] for previous, current in zip(periods, periods[1:])):
        raise AnalysisScopeError("statement periods overlap")
    versions = tuple(
        sorted(
            {
                transaction.classification.ruleset_version
                for item in statements
                for transaction in item.statement.transactions
                if transaction.classification is not None
            }
        )
    )
    return AnalysisScope(ids, from_date, to_date, "CLP", versions)


def _has_visible_account(masked_account_number: str | None) -> bool:
    return masked_account_number is not None and any(character.isdigit() for character in masked_account_number)


def _is_spending(transaction: Transaction) -> bool:
    return (
        transaction.movement_type == "debit"
        and transaction.classification is not None
        and transaction.classification.category in _EXPENSE_CATEGORIES
    )


def _amount_count(transactions: tuple[Transaction, ...]) -> AmountCount:
    return AmountCount(sum(transaction.amount for transaction in transactions), len(transactions))


def _category_totals(transactions: tuple[Transaction, ...]) -> tuple[CategoryTotal, ...]:
    totals: dict[Category, list[int]] = {}
    for transaction in transactions:
        assert transaction.classification is not None
        total = totals.setdefault(transaction.classification.category, [0, 0])
        total[0] += transaction.amount
        total[1] += 1
    return tuple(
        CategoryTotal(category, total[0], total[1])
        for category, total in sorted(totals.items(), key=lambda item: item[0].value)
    )


def _coverage(
    statements: tuple[AnalysisStatement, ...], from_date: date, to_date: date
) -> Coverage:
    ranges = sorted(
        (
            max(item.statement.period_start, from_date),
            min(item.statement.period_end, to_date),
        )
        for item in statements
        if item.statement.period_end >= from_date and item.statement.period_start <= to_date
    )
    merged: list[tuple[date, date]] = []
    for start, end in ranges:
        if merged and start <= merged[-1][1] + timedelta(days=1):
            merged[-1] = (merged[-1][0], max(merged[-1][1], end))
        else:
            merged.append((start, end))
    gaps: list[tuple[date, date]] = []
    cursor = from_date
    for start, end in merged:
        if cursor < start:
            gaps.append((cursor, start - timedelta(days=1)))
        cursor = end + timedelta(days=1)
    if cursor <= to_date:
        gaps.append((cursor, to_date))
    partial_months = tuple(
        _month_key(month)
        for month in _months(from_date, to_date)
        if not _is_interval_covered(month, _month_end(month), merged)
    )
    return Coverage(tuple(merged), tuple(gaps), partial_months)


def _monthly_totals(
    transactions: tuple[Transaction, ...], coverage: Coverage, from_date: date, to_date: date
) -> tuple[MonthlyTotal, ...]:
    totals: dict[date, list[Transaction]] = {}
    for transaction in transactions:
        totals.setdefault(transaction.date.replace(day=1), []).append(transaction)
    months = _months(from_date, to_date)
    result: list[MonthlyTotal] = []
    previous: MonthlyTotal | None = None
    for month in months:
        month_transactions = tuple(totals.get(month, []))
        total = _amount_count(month_transactions)
        incomplete = _month_key(month) in coverage.partial_months
        absolute_change: int | None = None
        percentage_change: str | None = None
        if previous is not None and not incomplete and previous.month not in coverage.partial_months:
            absolute_change = total.amount - previous.amount
            if previous.amount:
                percentage_change = str(
                    (Decimal(absolute_change) * Decimal(100) / Decimal(previous.amount)).quantize(
                        Decimal("0.01"), rounding=ROUND_HALF_UP
                    )
                )
        current = MonthlyTotal(
            _month_key(month), total.amount, total.count, _category_totals(month_transactions), absolute_change, percentage_change
        )
        result.append(current)
        previous = current
    return tuple(result)


def _top_merchants(transactions: tuple[Transaction, ...]) -> tuple[TopMerchant, ...]:
    totals: dict[str, list[object]] = {}
    for transaction in transactions:
        assert transaction.classification is not None
        key = transaction.classification.merchant_key
        assert key is not None
        total = totals.setdefault(key, [transaction.classification.merchant_name, 0, 0])
        total[1] += transaction.amount
        total[2] += 1
    ranked = sorted(totals.items(), key=lambda item: (-item[1][1], -item[1][2], item[0]))
    return tuple(TopMerchant(total[0], total[1], total[2]) for _, total in ranked[:TOP_MERCHANT_LIMIT])


def _recurrences(transactions: tuple[Transaction, ...]) -> tuple[RecurrenceCandidate, ...]:
    groups: dict[str, list[Transaction]] = {}
    for transaction in transactions:
        assert transaction.classification is not None
        assert transaction.classification.merchant_key is not None
        groups.setdefault(transaction.classification.merchant_key, []).append(transaction)
    candidates: list[tuple[str, RecurrenceCandidate]] = []
    for key, grouped in groups.items():
        ordered = tuple(sorted(grouped, key=lambda transaction: transaction.date))
        cadence = _recurrence_cadence(ordered)
        if cadence is None:
            continue
        amounts = tuple(transaction.amount for transaction in ordered)
        candidates.append(
            (
                key,
                RecurrenceCandidate(
                    ordered[0].classification.merchant_name if ordered[0].classification else None,
                    cadence,
                    tuple(transaction.date for transaction in ordered),
                    amounts,
                    len(ordered),
                    min(amounts),
                    int((Decimal(sum(amounts)) / Decimal(len(amounts))).quantize(Decimal("1"), rounding=ROUND_HALF_UP)),
                    max(amounts),
                ),
            )
        )
    return tuple(candidate for _, candidate in sorted(candidates, key=lambda item: item[0]))


def _recurrence_cadence(transactions: tuple[Transaction, ...]) -> RecurrenceCadence | None:
    if len(transactions) < 3:
        return None
    dates = tuple(transaction.date for transaction in transactions)
    if all(5 <= (current - previous).days <= 9 for previous, current in zip(dates, dates[1:])):
        return RecurrenceCadence.WEEKLY
    anchor = dates[0]
    if all(
        abs((current - _add_months(anchor, index)).days) <= 3
        for index, current in enumerate(dates[1:], start=1)
    ):
        return RecurrenceCadence.MONTHLY
    return None


def _months(from_date: date, to_date: date) -> tuple[date, ...]:
    month = from_date.replace(day=1)
    end = to_date.replace(day=1)
    result: list[date] = []
    while month <= end:
        result.append(month)
        month = _add_months(month, 1)
    return tuple(result)


def _month_key(month: date) -> str:
    return f"{month.year:04d}-{month.month:02d}"


def _month_end(month: date) -> date:
    return _add_months(month, 1) - timedelta(days=1)


def _is_interval_covered(start: date, end: date, ranges: list[tuple[date, date]]) -> bool:
    return any(start >= covered_start and end <= covered_end for covered_start, covered_end in ranges)


def _add_months(value: date, months: int) -> date:
    month_index = value.month - 1 + months
    year = value.year + month_index // 12
    month = month_index % 12 + 1
    day = min(value.day, monthrange(year, month)[1])
    return date(year, month, day)
