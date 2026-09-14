from datetime import date

import pytest

from zut_balance import categorization
from zut_balance.categorization import classify_transaction, normalize_merchant_key
from zut_balance.models import Category, MovementType, Transaction


def _transaction(description: str, movement_type: MovementType = MovementType.DEBIT) -> Transaction:
    return Transaction(
        date=date(2026, 8, 4),
        description=description,
        document_number=None,
        branch_or_channel=None,
        amount=1,
        movement_type=movement_type,
        reported_balance=None,
    )


def test_normalize_merchant_key_ignores_case_accents_punctuation_and_spaces() -> None:
    assert normalize_merchant_key(" Pago:  Cineplánet-Webpay ") == "PAGO CINEPLANET WEBPAY"


@pytest.mark.parametrize(
    ("description", "category", "merchant_name", "rule_id"),
    [
        ("PAGO:CINEPLANET WEBPAY", Category.ENTERTAINMENT, "Cineplanet", "cineplanet-webpay"),
        ("PAGO:SERVICIOS MÉDICOS", Category.HEALTH, "Servicios Medicos", "servicios-medicos"),
        ("TRASPASO A:DESTINATARIO", Category.TRANSFERS, None, "transfer-out"),
        ("TRASPASO DE:ORIGEN", Category.TRANSFERS, None, "transfer-in"),
    ],
)
def test_classify_transaction_applies_versioned_rules(
    description: str, category: Category, merchant_name: str | None, rule_id: str
) -> None:
    classification = classify_transaction(_transaction(description), "2026-08-04T00:00:00+00:00")

    assert classification.category is category
    assert classification.merchant_name == merchant_name
    assert classification.rule_id == rule_id
    assert classification.ruleset_version == "1"


def test_exact_rule_wins_over_prefix_rule(monkeypatch) -> None:
    monkeypatch.setattr(
        categorization,
        "_RULES",
        (
            categorization._Rule("prefix", Category.SHOPPING, "PAGO", priority=100),
            categorization._Rule("exact", Category.ENTERTAINMENT, "PAGO CINE", exact=True),
        ),
    )

    assert classify_transaction(_transaction("PAGO:CINE"), "").rule_id == "exact"


def test_unknown_credit_remains_uncategorized() -> None:
    classification = classify_transaction(_transaction("ABONO DESCONOCIDO", MovementType.CREDIT), "")

    assert classification.category is Category.UNCATEGORIZED
    assert classification.merchant_name is None
    assert classification.rule_id is None
