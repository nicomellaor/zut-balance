"""Deterministic, evidence-linked explanations for spending analysis."""

from dataclasses import dataclass
from enum import StrEnum

from .analysis import AnalysisResult, MonthlyTotal
from .models import Category


INSIGHT_LIMIT = 5


class InsightKind(StrEnum):
    COVERAGE_WARNING = "coverage_warning"
    DATA_QUALITY_WARNING = "data_quality_warning"
    PERIOD_SUMMARY = "period_summary"
    MONTHLY_CHANGE = "monthly_change"
    LEADING_CATEGORY = "leading_category"
    LEADING_MERCHANT = "leading_merchant"
    RECURRENCE_CANDIDATE = "recurrence_candidate"


@dataclass(frozen=True, slots=True)
class InsightEvidence:
    label: str
    value: int | str


@dataclass(frozen=True, slots=True)
class Insight:
    kind: InsightKind
    priority: int
    title: str
    body: str
    evidence: tuple[InsightEvidence, ...]
    caveat: str | None


def generate_insights(result: AnalysisResult) -> tuple[Insight, ...]:
    """Return the highest-priority explanations supported by an analysis result."""
    candidates = (
        _coverage_warning(result),
        _data_quality_warning(result),
        _period_summary(result),
        _monthly_change(result),
        _leading_category(result),
        _leading_merchant(result),
        _recurrence_candidate(result),
    )
    return tuple(
        Insight(candidate.kind, priority, candidate.title, candidate.body, candidate.evidence, candidate.caveat)
        for priority, candidate in enumerate((item for item in candidates if item is not None), start=1)
    )[:INSIGHT_LIMIT]


def _coverage_warning(result: AnalysisResult) -> Insight | None:
    coverage = result.coverage
    if not coverage.gaps and not coverage.partial_months:
        return None
    evidence = tuple(
        [
            InsightEvidence("hueco", f"{start.isoformat()} a {end.isoformat()}")
            for start, end in coverage.gaps
        ]
        + [InsightEvidence("mes_parcial", month) for month in coverage.partial_months]
    )
    return Insight(
        InsightKind.COVERAGE_WARNING,
        0,
        "Cobertura incompleta",
        "El período seleccionado tiene huecos o meses parciales.",
        evidence,
        "No interpretes estos períodos como cobertura completa.",
    )


def _data_quality_warning(result: AnalysisResult) -> Insight | None:
    _, unidentified = result.merchant_coverage
    evidence: list[InsightEvidence] = []
    limitations: list[str] = []
    if result.uncategorized.amount:
        evidence.extend(
            (
                InsightEvidence("monto_sin_categoria", result.uncategorized.amount),
                InsightEvidence("movimientos_sin_categoria", result.uncategorized.count),
            )
        )
        limitations.append("gasto sin categoría")
    if unidentified.amount:
        evidence.extend(
            (
                InsightEvidence("monto_sin_comercio", unidentified.amount),
                InsightEvidence("movimientos_sin_comercio", unidentified.count),
            )
        )
        limitations.append("gasto sin comercio identificado")
    if len(result.scope.ruleset_versions) > 1:
        evidence.append(InsightEvidence("versiones_ruleset", ", ".join(result.scope.ruleset_versions)))
        limitations.append("versiones de reglas distintas")
    if not limitations:
        return None
    return Insight(
        InsightKind.DATA_QUALITY_WARNING,
        0,
        "Cobertura de clasificación limitada",
        f"El análisis incluye {' y '.join(limitations)}.",
        tuple(evidence),
        "Las categorías y comercios mostrados no representan necesariamente todo el gasto.",
    )


def _period_summary(result: AnalysisResult) -> Insight:
    spending = result.spending
    if spending.amount:
        body = "El período seleccionado registra gasto de consumo calculado sobre movimientos clasificados."
    else:
        body = "No se registró gasto de consumo dentro de la cobertura disponible para el período seleccionado."
    return Insight(
        InsightKind.PERIOD_SUMMARY,
        0,
        "Resumen del período",
        body,
        (
            InsightEvidence("gasto", spending.amount),
            InsightEvidence("movimientos_de_gasto", spending.count),
            InsightEvidence("creditos", result.credits.amount),
            InsightEvidence("debitos_excluidos", result.excluded_debits.amount),
        ),
        None,
    )


def _monthly_change(result: AnalysisResult) -> Insight | None:
    changes = tuple(month for month in result.monthly if month.absolute_change not in (None, 0))
    if not changes:
        return None
    current = max(changes, key=lambda month: (abs(month.absolute_change or 0), month.month))
    previous = _previous_month(result.monthly, current)
    assert current.absolute_change is not None
    evidence = [
        InsightEvidence("mes_actual", current.month),
        InsightEvidence("gasto_actual", current.amount),
        InsightEvidence("mes_anterior", previous.month),
        InsightEvidence("gasto_anterior", previous.amount),
        InsightEvidence("cambio_absoluto", current.absolute_change),
    ]
    if current.percentage_change is not None:
        evidence.append(InsightEvidence("cambio_porcentual", current.percentage_change))
    return Insight(
        InsightKind.MONTHLY_CHANGE,
        0,
        "Variación mensual destacada",
        "Esta es la mayor variación absoluta entre meses con comparación disponible.",
        tuple(evidence),
        None,
    )


def _previous_month(months: tuple[MonthlyTotal, ...], current: MonthlyTotal) -> MonthlyTotal:
    index = months.index(current)
    assert index > 0
    return months[index - 1]


def _leading_category(result: AnalysisResult) -> Insight | None:
    categories = tuple(item for item in result.categories if item.category != Category.UNCATEGORIZED)
    if not categories:
        return None
    category = min(categories, key=lambda item: (-item.amount, item.category.value))
    return Insight(
        InsightKind.LEADING_CATEGORY,
        0,
        "Categoría principal",
        f"{category.category.value} concentra el mayor monto entre las categorías identificadas.",
        (
            InsightEvidence("categoria", category.category.value),
            InsightEvidence("monto", category.amount),
            InsightEvidence("movimientos", category.count),
        ),
        None,
    )


def _leading_merchant(result: AnalysisResult) -> Insight | None:
    if not result.top_merchants:
        return None
    merchant = result.top_merchants[0]
    if merchant.merchant_name is None:
        return None
    return Insight(
        InsightKind.LEADING_MERCHANT,
        0,
        "Comercio principal identificado",
        f"{merchant.merchant_name} concentra el mayor monto entre los comercios identificados.",
        (
            InsightEvidence("comercio", merchant.merchant_name),
            InsightEvidence("monto", merchant.amount),
            InsightEvidence("movimientos", merchant.count),
        ),
        "El ranking considera únicamente movimientos con comercio identificado.",
    )


def _recurrence_candidate(result: AnalysisResult) -> Insight | None:
    if not result.recurrence_candidates:
        return None
    candidate = result.recurrence_candidates[0]
    if candidate.merchant_name is None:
        return None
    return Insight(
        InsightKind.RECURRENCE_CANDIDATE,
        0,
        "Candidato de recurrencia",
        f"{candidate.merchant_name} presenta una cadencia {candidate.cadence.value} observada en el período.",
        (
            InsightEvidence("comercio", candidate.merchant_name),
            InsightEvidence("cadencia", candidate.cadence.value),
            InsightEvidence("ocurrencias", candidate.count),
            InsightEvidence("desde", candidate.dates[0].isoformat()),
            InsightEvidence("hasta", candidate.dates[-1].isoformat()),
        ),
        "Es un candidato basado en fechas observadas, no una confirmación.",
    )
