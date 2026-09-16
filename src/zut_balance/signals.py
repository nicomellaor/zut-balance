"""Typed deterministic signals derived from spending analysis."""

from dataclasses import dataclass
from enum import StrEnum

from .analysis import AnalysisResult, MonthlyTotal


class NoticeKind(StrEnum):
    INCOMPLETE_COVERAGE = "incomplete_coverage"
    LIMITED_CLASSIFICATION = "limited_classification"


class NoticeSeverity(StrEnum):
    WARNING = "warning"
    INFO = "info"


@dataclass(frozen=True, slots=True)
class CoverageNotice:
    kind: NoticeKind
    severity: NoticeSeverity
    gaps: tuple[tuple[str, str], ...]
    partial_months: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ClassificationNotice:
    kind: NoticeKind
    severity: NoticeSeverity
    uncategorized_amount: int
    uncategorized_count: int
    unidentified_merchant_amount: int
    unidentified_merchant_count: int
    ruleset_versions: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class LargestMonthlyChange:
    previous_month: str
    current_month: str
    previous_amount: int
    current_amount: int
    absolute_change: int
    percentage_change: str | None


@dataclass(frozen=True, slots=True)
class AnalysisSignals:
    notices: tuple[CoverageNotice | ClassificationNotice, ...]
    largest_monthly_change: LargestMonthlyChange | None


def generate_signals(result: AnalysisResult) -> AnalysisSignals:
    """Return deterministic, non-narrative signals supported by analysis facts."""
    notices: list[CoverageNotice | ClassificationNotice] = []
    if result.coverage.gaps or result.coverage.partial_months:
        notices.append(
            CoverageNotice(
                NoticeKind.INCOMPLETE_COVERAGE,
                NoticeSeverity.WARNING,
                tuple((start.isoformat(), end.isoformat()) for start, end in result.coverage.gaps),
                result.coverage.partial_months,
            )
        )
    _, unidentified = result.merchant_coverage
    if (
        result.uncategorized.amount
        or result.uncategorized.count
        or unidentified.amount
        or unidentified.count
        or len(result.scope.ruleset_versions) > 1
    ):
        notices.append(
            ClassificationNotice(
                NoticeKind.LIMITED_CLASSIFICATION,
                NoticeSeverity.INFO,
                result.uncategorized.amount,
                result.uncategorized.count,
                unidentified.amount,
                unidentified.count,
                result.scope.ruleset_versions,
            )
        )
    return AnalysisSignals(tuple(notices), _largest_monthly_change(result.monthly))


def _largest_monthly_change(months: tuple[MonthlyTotal, ...]) -> LargestMonthlyChange | None:
    changes = tuple(month for month in months if month.absolute_change not in (None, 0))
    if not changes:
        return None
    current = max(changes, key=lambda month: (abs(month.absolute_change or 0), month.month))
    index = months.index(current)
    assert index > 0 and current.absolute_change is not None
    previous = months[index - 1]
    return LargestMonthlyChange(
        previous.month,
        current.month,
        previous.amount,
        current.amount,
        current.absolute_change,
        current.percentage_change,
    )
