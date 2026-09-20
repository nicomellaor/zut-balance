from datetime import date
import json

import pytest

from zut_balance import categorization
from zut_balance.categorization import (
    CatalogValidationError,
    _classify_transaction,
    _load_catalog_json,
    classify_transaction,
    load_catalog,
    normalize_merchant_key,
)
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


def _rule(**changes: object) -> dict[str, object]:
    rule: dict[str, object] = {
        "id": "rule",
        "category": "compras",
        "match_type": "prefix",
        "pattern": "PAGO",
        "merchant_name": None,
        "merchant_key": None,
        "priority": 0,
        "movement_type": None,
    }
    rule.update(changes)
    return rule


def _catalog_json(rules: list[dict[str, object]], ruleset_version: str = "test") -> str:
    return json.dumps({"schema_version": 1, "ruleset_version": ruleset_version, "rules": rules})


def _result(transaction: Transaction, catalog_version: str) -> tuple[str, str | None, str | None, str | None, str]:
    catalog = load_catalog(catalog_version)
    classification = _classify_transaction(transaction, "2026-08-04T00:00:00+00:00", catalog)
    return (
        classification.category.value,
        classification.merchant_name,
        classification.merchant_key,
        classification.rule_id,
        classification.ruleset_version,
    )


def test_normalize_merchant_key_ignores_case_accents_punctuation_and_spaces() -> None:
    assert normalize_merchant_key(" Pago:  Cineplánet-Webpay ") == "PAGO CINEPLANET WEBPAY"


@pytest.mark.parametrize(
    ("description", "expected"),
    [
        (
            "PAGO:CINEPLANET WEBPAY",
            ("entretenimiento", "Cineplanet", "CINEPLANET", "cineplanet-webpay", "1"),
        ),
        (
            "PAGO:SERVICIOS MÉDICOS",
            ("salud", "Servicios Medicos", "SERVICIOS MEDICOS", "servicios-medicos", "1"),
        ),
        ("TRASPASO A:DESTINATARIO", ("transferencias", None, None, "transfer-out", "1")),
        ("TRASPASO DE:ORIGEN", ("transferencias", None, None, "transfer-in", "1")),
    ],
)
def test_v1_catalog_reproduces_existing_rules(
    description: str, expected: tuple[str, str | None, str | None, str | None, str]
) -> None:
    assert _result(_transaction(description), "1") == expected


@pytest.mark.parametrize(
    ("description", "expected"),
    [
        ("PAGO:UNIMARC PROVIDENCIA", ("alimentacion", "Unimarc", "UNIMARC", "unimarc", "2")),
        ("PAGO:PEDIDOSYA RESTAURANTE", ("alimentacion", "PedidosYa", "PEDIDOSYA", "pedidosya", "2")),
        ("PAGO:DL*PEDIDOSYA 123", ("alimentacion", "PedidosYa", "PEDIDOSYA", "pedidosya-dl", "2")),
        ("PAGO:MERCADOPAGO*COMERCIO", ("compras", None, None, "mercadopago-generic", "2")),
        ("PAGO:CINEMARK", ("entretenimiento", None, None, "generic-cinema", "2")),
        ("PAGO:CAFE CENTRAL", ("alimentacion", None, None, "generic-cafe", "2")),
        ("PAGO:CAFETERIA LOCAL", ("alimentacion", None, None, "generic-cafe", "2")),
        (
            "PAGO:CINEPLANET WEBPAY",
            ("entretenimiento", "Cineplanet", "CINEPLANET", "cineplanet-webpay", "2"),
        ),
    ],
)
def test_v2_catalog_applies_approved_rules(
    description: str, expected: tuple[str, str | None, str | None, str | None, str]
) -> None:
    assert _result(_transaction(description), "2") == expected


@pytest.mark.parametrize(
    ("description", "movement_type", "expected_category", "expected_rule"),
    [
        ("PAGO:UNIMARC", MovementType.CREDIT, Category.UNCATEGORIZED, None),
        ("PAGO:CAFE CENTRAL", MovementType.CREDIT, Category.UNCATEGORIZED, None),
        ("MERCADOPAGO SIN PAGO", MovementType.DEBIT, Category.UNCATEGORIZED, None),
        ("PAGO:DESCAFEINADO", MovementType.DEBIT, Category.UNCATEGORIZED, None),
        ("TRASPASO A:CAFE CENTRAL", MovementType.DEBIT, Category.TRANSFERS, "transfer-out"),
        ("TRASPASO A:CINE HOYTS", MovementType.DEBIT, Category.TRANSFERS, "transfer-out"),
    ],
)
def test_v2_catalog_preserves_negative_evidence_and_transfer_precedence(
    description: str,
    movement_type: MovementType,
    expected_category: Category,
    expected_rule: str | None,
) -> None:
    classification = classify_transaction(_transaction(description, movement_type), "")

    assert classification.category is expected_category
    assert classification.rule_id == expected_rule


def test_precedence_is_independent_of_catalog_order() -> None:
    rules = [
        _rule(id="prefix", pattern="PAGO", priority=100),
        _rule(id="exact", category="entretenimiento", match_type="exact", pattern="PAGO CINE"),
    ]

    catalog = _load_catalog_json(_catalog_json(rules))
    reversed_catalog = _load_catalog_json(_catalog_json(list(reversed(rules))))

    assert _classify_transaction(_transaction("PAGO:CINE"), "", catalog).rule_id == "exact"
    assert _classify_transaction(_transaction("PAGO:CINE"), "", reversed_catalog).rule_id == "exact"


def test_prefix_wins_over_token_priority_and_rule_id_breaks_same_type_ties() -> None:
    catalog = _load_catalog_json(
        _catalog_json(
            [
                _rule(id="token", category="alimentacion", match_type="token_prefix", pattern="CAFE", priority=100),
                _rule(id="z-rule", category="servicios", pattern="PAGO", priority=1),
                _rule(id="a-rule", category="entretenimiento", pattern="PAGO CAFE", priority=1),
            ]
        )
    )

    classification = _classify_transaction(_transaction("PAGO CAFE"), "", catalog)

    assert classification.category is Category.ENTERTAINMENT
    assert classification.rule_id == "a-rule"


def test_specific_mercadopago_rule_can_win_over_generic_fallback() -> None:
    catalog = _load_catalog_json(
        _catalog_json(
            [
                _rule(id="mercadopago-generic", pattern="PAGO MERCADOPAGO", movement_type="debit"),
                _rule(
                    id="mercadopago-store",
                    category="alimentacion",
                    pattern="PAGO MERCADOPAGO CAFE CENTRAL",
                    merchant_name="Cafe Central",
                    merchant_key="CAFE CENTRAL",
                    priority=10,
                    movement_type="debit",
                ),
            ]
        )
    )

    classification = _classify_transaction(_transaction("PAGO:MERCADOPAGO CAFE CENTRAL"), "", catalog)

    assert classification.category is Category.FOOD
    assert classification.merchant_name == "Cafe Central"
    assert classification.rule_id == "mercadopago-store"


@pytest.mark.parametrize(
    "source",
    [
        '{"schema_version": 1, "schema_version": 1, "ruleset_version": "1", "rules": []}',
        "{",
        _catalog_json([_rule(extra="unexpected")]),
        _catalog_json([_rule(priority=True)]),
        _catalog_json([_rule(pattern="Pago Unimarc")]),
        _catalog_json([_rule(category="unknown")]),
        _catalog_json([_rule(movement_type="unknown")]),
        _catalog_json([_rule(merchant_name="Store")]),
        _catalog_json([_rule(match_type="token_prefix", pattern="PAGO CINE")]),
        _catalog_json([_rule(), _rule(id="other")]),
    ],
)
def test_catalog_validation_rejects_invalid_inputs(source: str) -> None:
    with pytest.raises(CatalogValidationError):
        _load_catalog_json(source)


def test_catalog_validation_rejects_duplicate_rule_ids() -> None:
    with pytest.raises(CatalogValidationError):
        _load_catalog_json(_catalog_json([_rule(), _rule()]))


def test_packaged_catalog_rejects_a_mismatched_declared_version(monkeypatch) -> None:
    class _Resource:
        def joinpath(self, *_: str) -> "_Resource":
            return self

        def read_text(self, *, encoding: str) -> str:
            assert encoding == "utf-8"
            return _catalog_json([], ruleset_version="1")

    monkeypatch.setattr(categorization.resources, "files", lambda _: _Resource())

    with pytest.raises(CatalogValidationError):
        categorization.load_catalog("2")


def test_invalid_catalog_fails_without_creating_a_database(tmp_path) -> None:
    database_path = tmp_path / "statements.sqlite3"

    with pytest.raises(CatalogValidationError):
        _load_catalog_json(_catalog_json([_rule(pattern="Pago Unimarc")]))

    assert not database_path.exists()
