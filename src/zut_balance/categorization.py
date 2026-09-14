"""Deterministic transaction categorization rules."""

from dataclasses import dataclass
import re
import unicodedata

from .models import Category, Classification, MovementType, Transaction


RULESET_VERSION = "1"


@dataclass(frozen=True, slots=True)
class _Rule:
    id: str
    category: Category
    pattern: str
    merchant_name: str | None = None
    merchant_key: str | None = None
    priority: int = 0
    exact: bool = False
    movement_type: MovementType | None = None


_RULES = (
    _Rule(
        id="cineplanet-webpay",
        category=Category.ENTERTAINMENT,
        pattern="PAGO CINEPLANET WEBPAY",
        merchant_name="Cineplanet",
        merchant_key="CINEPLANET",
        exact=True,
    ),
    _Rule(
        id="servicios-medicos",
        category=Category.HEALTH,
        pattern="PAGO SERVICIOS MEDICOS",
        merchant_name="Servicios Medicos",
        merchant_key="SERVICIOS MEDICOS",
        exact=True,
    ),
    _Rule(
        id="transfer-out",
        category=Category.TRANSFERS,
        pattern="TRASPASO A",
        priority=10,
    ),
    _Rule(
        id="transfer-in",
        category=Category.TRANSFERS,
        pattern="TRASPASO DE",
        priority=10,
    ),
)


def normalize_merchant_key(description: str) -> str:
    """Return a case- and accent-insensitive key without changing source text."""
    normalized = unicodedata.normalize("NFKD", description).upper()
    normalized = "".join(character for character in normalized if not unicodedata.combining(character))
    return re.sub(r"\s+", " ", re.sub(r"[^A-Z0-9]+", " ", normalized)).strip()


def classify_transaction(transaction: Transaction, classified_at: str) -> Classification:
    """Classify a transaction with the fixed, versioned ruleset."""
    key = normalize_merchant_key(transaction.description)
    matching_rules = [
        rule
        for rule in _RULES
        if (rule.movement_type is None or rule.movement_type is transaction.movement_type)
        and (key == rule.pattern if rule.exact else key.startswith(rule.pattern))
    ]
    if not matching_rules:
        return Classification(
            category=Category.UNCATEGORIZED,
            merchant_name=None,
            merchant_key=None,
            rule_id=None,
            ruleset_version=RULESET_VERSION,
            classified_at=classified_at,
        )
    rule = sorted(matching_rules, key=lambda item: (not item.exact, -item.priority, item.id))[0]
    return Classification(
        category=rule.category,
        merchant_name=rule.merchant_name,
        merchant_key=rule.merchant_key,
        rule_id=rule.id,
        ruleset_version=RULESET_VERSION,
        classified_at=classified_at,
    )
