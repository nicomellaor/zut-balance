"""Deterministic transaction categorization from packaged rule catalogs."""

from dataclasses import dataclass
from importlib import resources
import json
import re
import unicodedata

from .models import Category, Classification, MovementType, Transaction


_CATALOG_SCHEMA_VERSION = 1
_CATALOG_FIELDS = frozenset({"schema_version", "ruleset_version", "rules"})
_RULE_FIELDS = frozenset(
    {
        "id",
        "category",
        "match_type",
        "pattern",
        "merchant_name",
        "merchant_key",
        "priority",
        "movement_type",
    }
)
_MATCH_RANK = {"exact": 0, "prefix": 1, "token_prefix": 2}
_RULE_ID_PATTERN = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*\Z")


class CatalogValidationError(RuntimeError):
    """Raised when a packaged categorization catalog is invalid."""


@dataclass(frozen=True, slots=True)
class _Rule:
    id: str
    category: Category
    match_type: str
    pattern: str
    merchant_name: str | None
    merchant_key: str | None
    priority: int
    movement_type: MovementType | None


@dataclass(frozen=True, slots=True)
class RuleCatalog:
    schema_version: int
    ruleset_version: str
    rules: tuple[_Rule, ...]


def normalize_merchant_key(description: str) -> str:
    """Return a case- and accent-insensitive key without changing source text."""
    normalized = unicodedata.normalize("NFKD", description).upper()
    normalized = "".join(character for character in normalized if not unicodedata.combining(character))
    return re.sub(r"\s+", " ", re.sub(r"[^A-Z0-9]+", " ", normalized)).strip()


def _reject_duplicate_keys(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise CatalogValidationError("Catalog JSON contains a duplicate key")
        result[key] = value
    return result


def _require_fields(value: object, expected: frozenset[str], label: str) -> dict[str, object]:
    if type(value) is not dict or frozenset(value) != expected:
        raise CatalogValidationError(f"Catalog {label} fields are invalid")
    return value


def _require_string(value: object, label: str) -> str:
    if type(value) is not str or not value:
        raise CatalogValidationError(f"Catalog {label} is invalid")
    return value


def _catalog_from_data(value: object) -> RuleCatalog:
    catalog = _require_fields(value, _CATALOG_FIELDS, "object")
    schema_version = catalog["schema_version"]
    if type(schema_version) is not int or schema_version != _CATALOG_SCHEMA_VERSION:
        raise CatalogValidationError("Catalog schema version is not supported")
    ruleset_version = _require_string(catalog["ruleset_version"], "ruleset version")
    rules_data = catalog["rules"]
    if type(rules_data) is not list:
        raise CatalogValidationError("Catalog rules are invalid")

    rules: list[_Rule] = []
    ids: set[str] = set()
    domains: set[tuple[str, str, MovementType | None]] = set()
    for rule_data in rules_data:
        rule = _require_fields(rule_data, _RULE_FIELDS, "rule")
        rule_id = _require_string(rule["id"], "rule id")
        if not _RULE_ID_PATTERN.fullmatch(rule_id) or rule_id in ids:
            raise CatalogValidationError("Catalog rule id is invalid")
        ids.add(rule_id)
        try:
            category = Category(_require_string(rule["category"], "rule category"))
        except ValueError as error:
            raise CatalogValidationError("Catalog rule category is invalid") from error
        match_type = _require_string(rule["match_type"], "rule match type")
        if match_type not in _MATCH_RANK:
            raise CatalogValidationError("Catalog rule match type is invalid")
        pattern = _require_string(rule["pattern"], "rule pattern")
        if pattern != normalize_merchant_key(pattern):
            raise CatalogValidationError("Catalog rule pattern must be normalized")
        if match_type == "token_prefix" and not pattern.isalnum():
            raise CatalogValidationError("Catalog token prefix must be one alphanumeric token")
        priority = rule["priority"]
        if type(priority) is not int:
            raise CatalogValidationError("Catalog rule priority is invalid")

        movement_type_value = rule["movement_type"]
        if movement_type_value is None:
            movement_type = None
        else:
            try:
                movement_type = MovementType(_require_string(movement_type_value, "movement type"))
            except ValueError as error:
                raise CatalogValidationError("Catalog movement type is invalid") from error

        merchant_name = rule["merchant_name"]
        merchant_key = rule["merchant_key"]
        if (merchant_name is None) != (merchant_key is None):
            raise CatalogValidationError("Catalog merchant name and key must be paired")
        if merchant_name is not None:
            merchant_name = _require_string(merchant_name, "merchant name")
            merchant_key = _require_string(merchant_key, "merchant key")
            if merchant_key != normalize_merchant_key(merchant_key):
                raise CatalogValidationError("Catalog merchant key must be normalized")

        domain = (match_type, pattern, movement_type)
        if domain in domains:
            raise CatalogValidationError("Catalog rules have a duplicate match domain")
        domains.add(domain)
        rules.append(
            _Rule(
                rule_id,
                category,
                match_type,
                pattern,
                merchant_name,
                merchant_key,
                priority,
                movement_type,
            )
        )
    return RuleCatalog(schema_version, ruleset_version, tuple(rules))


def _load_catalog_json(source: str) -> RuleCatalog:
    """Parse and validate catalog JSON without accessing SQLite."""
    try:
        data = json.loads(source, object_pairs_hook=_reject_duplicate_keys)
    except json.JSONDecodeError as error:
        raise CatalogValidationError("Catalog JSON is invalid") from error
    return _catalog_from_data(data)


def load_catalog(version: str) -> RuleCatalog:
    """Load one versioned catalog from installed package resources."""
    if type(version) is not str or not version:
        raise CatalogValidationError("Catalog version is invalid")
    resource = resources.files("zut_balance").joinpath("catalogs", f"categorization-v{version}.json")
    try:
        catalog = _load_catalog_json(resource.read_text(encoding="utf-8"))
    except FileNotFoundError as error:
        raise CatalogValidationError("Catalog resource is missing") from error
    if catalog.ruleset_version != version:
        raise CatalogValidationError("Catalog resource version does not match its requested version")
    return catalog


def _matches(rule: _Rule, key: str) -> bool:
    if rule.match_type == "exact":
        return key == rule.pattern
    if rule.match_type == "prefix":
        return key.startswith(rule.pattern)
    return any(token.startswith(rule.pattern) for token in key.split())


def _classify_transaction(
    transaction: Transaction, classified_at: str, catalog: RuleCatalog
) -> Classification:
    key = normalize_merchant_key(transaction.description)
    matching_rules = [
        rule
        for rule in catalog.rules
        if (rule.movement_type is None or rule.movement_type is transaction.movement_type)
        and _matches(rule, key)
    ]
    if not matching_rules:
        return Classification(
            category=Category.UNCATEGORIZED,
            merchant_name=None,
            merchant_key=None,
            rule_id=None,
            ruleset_version=catalog.ruleset_version,
            classified_at=classified_at,
        )
    rule = min(matching_rules, key=lambda item: (_MATCH_RANK[item.match_type], -item.priority, item.id))
    return Classification(
        category=rule.category,
        merchant_name=rule.merchant_name,
        merchant_key=rule.merchant_key,
        rule_id=rule.id,
        ruleset_version=catalog.ruleset_version,
        classified_at=classified_at,
    )


_ACTIVE_CATALOG = load_catalog("2")
RULESET_VERSION = _ACTIVE_CATALOG.ruleset_version


def classify_transaction(transaction: Transaction, classified_at: str) -> Classification:
    """Classify a transaction with the active, validated ruleset."""
    return _classify_transaction(transaction, classified_at, _ACTIVE_CATALOG)
