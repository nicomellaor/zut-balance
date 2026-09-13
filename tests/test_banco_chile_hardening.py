from dataclasses import replace
from datetime import date
from pathlib import Path
import re

import pytest

from zut_balance import UnreliableExtractionError, parse_banco_chile_cuenta_vista
from zut_balance.banco_chile_cuenta_vista import (
    _validate_document_evidence,
    extract_statement_metadata,
    extract_transactions,
)
from zut_balance.pdf_validation import extract_pdf_text


FIXTURES = Path(__file__).parent / "fixtures"
MULTIPAGE_PDF = FIXTURES / "cartola_banco_chile_multipagina.pdf"
CROSS_YEAR_PDF = FIXTURES / "cartola_banco_chile_cruce_anio.pdf"
SHIFTED_COLUMNS_PDF = FIXTURES / "cartola_banco_chile_columnas_desplazadas.pdf"
REORDERED_METADATA_PDF = FIXTURES / "cartola_banco_chile_metadatos_reordenados.pdf"


def test_parse_multipage_statement_combines_sections_and_transactions() -> None:
    statement = parse_banco_chile_cuenta_vista(MULTIPAGE_PDF)

    assert statement.page_number == 1
    assert statement.total_pages == 3
    assert statement.period_start.isoformat() == "2026-12-15"
    assert statement.period_end.isoformat() == "2027-01-15"
    assert [transaction.date.isoformat() for transaction in statement.transactions] == [
        "2026-12-16",
        "2026-12-20",
        "2027-01-05",
        "2027-01-10",
    ]
    assert [transaction.description for transaction in statement.transactions] == [
        "PAGO SERVICIO",
        "TRANSFERENCIA",
        "ABONO NOMINA CONTINUACION",
        "PAGO COMERCIO",
    ]
    assert statement.summary.opening_balance == 100_000
    assert statement.summary.closing_balance == 100_000
    assert all(
        "MUESTRA" not in transaction.description
        and "GARANTIA" not in transaction.description
        for transaction in statement.transactions
    )


def test_parse_cross_year_statement_normalizes_transaction_years() -> None:
    statement = parse_banco_chile_cuenta_vista(CROSS_YEAR_PDF)

    assert [transaction.date.isoformat() for transaction in statement.transactions] == [
        "2026-12-20",
        "2027-01-10",
    ]


def test_shifted_columns_and_reordered_metadata_match_expected_values() -> None:
    shifted = parse_banco_chile_cuenta_vista(SHIFTED_COLUMNS_PDF)
    reordered = parse_banco_chile_cuenta_vista(REORDERED_METADATA_PDF)

    assert [transaction.amount for transaction in shifted.transactions] == [10_000, 20_000]
    assert [transaction.movement_type for transaction in shifted.transactions] == [
        "debit",
        "credit",
    ]
    assert reordered.period_start.isoformat() == "2026-08-01"
    assert reordered.period_end.isoformat() == "2026-08-31"
    assert reordered.currency == "PESOS"


@pytest.mark.parametrize(
    ("replacement", "message"),
    [
        ("N° DE PAGINA: 2 DE 3", "page sequence"),
        ("N° DE PAGINA: 1 DE 2", "pagination"),
    ],
)
def test_metadata_rejects_inconsistent_pagination(replacement: str, message: str) -> None:
    pages = extract_pdf_text(MULTIPAGE_PDF.read_bytes())
    altered_pages = (pages[0].replace("N° DE PAGINA: 1 DE 3", replacement), *pages[1:])

    with pytest.raises(UnreliableExtractionError, match=message):
        extract_statement_metadata(altered_pages)


def test_metadata_rejects_inconsistent_repeated_metadata() -> None:
    pages = extract_pdf_text(MULTIPAGE_PDF.read_bytes())
    altered_pages = (*pages[:1], pages[1].replace("MONEDA: PESOS", "MONEDA: DOLARES"), pages[2])

    with pytest.raises(UnreliableExtractionError, match="currency is inconsistent"):
        extract_statement_metadata(altered_pages)


def test_metadata_rejects_conflicting_metadata_without_period_labels() -> None:
    pages = extract_pdf_text(MULTIPAGE_PDF.read_bytes())
    page_without_period = re.sub(r"(?:DESDE|HASTA): \d{2}/\d{2}/\d{4}\n", "", pages[1])
    altered_pages = (*pages[:1], page_without_period.replace("MONEDA: PESOS", "MONEDA: DOLARES"), pages[2])

    with pytest.raises(UnreliableExtractionError, match="currency is inconsistent"):
        extract_statement_metadata(altered_pages)


def test_metadata_rejects_multipage_statement_without_pagination() -> None:
    pages = extract_pdf_text(MULTIPAGE_PDF.read_bytes())
    altered_pages = tuple(
        re.sub(r"N° DE PAGINA: \d+ DE \d+\n", "", page) for page in pages
    )

    with pytest.raises(UnreliableExtractionError, match="pagination is missing"):
        extract_statement_metadata(altered_pages)


@pytest.mark.parametrize(
    ("alter_pages", "message"),
    [
        (lambda pages: pages[:2], "page total"),
        (lambda pages: (pages[0], pages[1], pages[1]), "page sequence"),
        (
            lambda pages: (
                pages[0].replace("N° DE PAGINA: 1 DE 3", "N° DE PAGINA: 4 DE 3"),
                *pages[1:],
            ),
            "page sequence",
        ),
    ],
)
def test_metadata_rejects_missing_duplicated_or_out_of_range_pages(
    alter_pages, message: str
) -> None:
    pages = extract_pdf_text(MULTIPAGE_PDF.read_bytes())

    with pytest.raises(UnreliableExtractionError, match=message):
        extract_statement_metadata(alter_pages(pages))


def test_metadata_rejects_invalid_period_date() -> None:
    pages = extract_pdf_text(CROSS_YEAR_PDF.read_bytes())
    altered_pages = (pages[0].replace("HASTA: 15/01/2027", "HASTA: 31/99/2027"),)

    with pytest.raises(UnreliableExtractionError, match="period date is invalid"):
        extract_statement_metadata(altered_pages)


def test_transaction_extraction_rejects_ambiguous_columns() -> None:
    pages = extract_pdf_text(SHIFTED_COLUMNS_PDF.read_bytes())
    metadata = extract_statement_metadata(pages)
    altered_pages = (pages[0].replace("O ABONOS", "ABONOS"),)

    with pytest.raises(UnreliableExtractionError, match="columns could not be located"):
        extract_transactions(altered_pages, metadata.period_start, metadata.period_end)


def test_transaction_extraction_rejects_reordered_columns() -> None:
    pages = extract_pdf_text(SHIFTED_COLUMNS_PDF.read_bytes())
    metadata = extract_statement_metadata(pages)
    altered_pages = (
        pages[0]
        .replace("CARGOS", "TEMPORAL")
        .replace("O ABONOS", "CARGOS")
        .replace("TEMPORAL", "O ABONOS"),
    )

    with pytest.raises(UnreliableExtractionError, match="columns are ambiguous"):
        extract_transactions(altered_pages, metadata.period_start, metadata.period_end)


def test_transaction_extraction_rejects_continuation_with_other_columns() -> None:
    pages = extract_pdf_text(MULTIPAGE_PDF.read_bytes())
    metadata = extract_statement_metadata(pages)
    lines = pages[2].splitlines()
    continuation_index = next(index for index, line in enumerate(lines) if "CONTINUACION" in line)
    header = next(line for line in lines if "DIA/MES" in line)
    document_start = header.index("N° DOCTO")
    lines[continuation_index] = f"{' ' * document_start}999"
    altered_pages = (*pages[:2], "\n".join(lines))

    with pytest.raises(UnreliableExtractionError, match="continuation contains other columns"):
        extract_transactions(altered_pages, metadata.period_start, metadata.period_end)


def test_transaction_extraction_rejects_invalid_period_and_ambiguous_date() -> None:
    pages = extract_pdf_text(CROSS_YEAR_PDF.read_bytes())

    with pytest.raises(UnreliableExtractionError, match="period is invalid"):
        extract_transactions(pages, period_start=date(2027, 1, 15), period_end=date(2026, 12, 15))
    with pytest.raises(UnreliableExtractionError, match="year could not be determined"):
        extract_transactions(pages, period_start=date(2026, 1, 1), period_end=date(2028, 12, 31))


def test_document_evidence_rejects_missing_transaction() -> None:
    pages = extract_pdf_text(MULTIPAGE_PDF.read_bytes())
    statement = parse_banco_chile_cuenta_vista(MULTIPAGE_PDF)

    with pytest.raises(UnreliableExtractionError, match="transaction count"):
        _validate_document_evidence(pages, statement.transactions[:-1])


def test_document_evidence_rejects_mismatched_totals() -> None:
    pages = extract_pdf_text(MULTIPAGE_PDF.read_bytes())
    statement = parse_banco_chile_cuenta_vista(MULTIPAGE_PDF)
    altered_transaction = replace(statement.transactions[0], amount=1)

    with pytest.raises(UnreliableExtractionError, match="debit total"):
        _validate_document_evidence(pages, (altered_transaction, *statement.transactions[1:]))


@pytest.mark.parametrize(
    "fixture",
    [MULTIPAGE_PDF, CROSS_YEAR_PDF, SHIFTED_COLUMNS_PDF, REORDERED_METADATA_PDF],
)
def test_fixture_parsing_is_deterministic(fixture: Path) -> None:
    assert parse_banco_chile_cuenta_vista(fixture) == parse_banco_chile_cuenta_vista(fixture)
