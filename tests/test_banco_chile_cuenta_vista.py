from dataclasses import replace
from pathlib import Path
import re

import pytest

from zut_balance import (
    UnreliableExtractionError,
    UnsupportedStatementError,
    parse_banco_chile_cuenta_vista,
)
from zut_balance.banco_chile_cuenta_vista import (
    extract_statement_metadata,
    extract_transactions,
    validate_statement_completeness_and_reconciliation,
    validate_banco_chile_cuenta_vista_format,
)
from zut_balance.pdf_validation import extract_pdf_text


SAMPLE_PDF = Path(__file__).parents[1] / "media" / "cartola_ejemplo_banco_chile.pdf"
V2_SAMPLE_PDF = Path(__file__).parents[1] / "media" / "cartola_v2_ejemplo_banco_chile.pdf"


def test_validate_format_accepts_supported_sample() -> None:
    pages = extract_pdf_text(SAMPLE_PDF.read_bytes())

    validate_banco_chile_cuenta_vista_format(pages)


def test_validate_format_rejects_bank_name_without_statement_markers() -> None:
    with pytest.raises(UnsupportedStatementError, match="does not match"):
        validate_banco_chile_cuenta_vista_format(("Banco de Chile",))


def test_extract_statement_metadata_normalizes_supported_sample() -> None:
    metadata = extract_statement_metadata(extract_pdf_text(SAMPLE_PDF.read_bytes()))

    assert metadata.bank == "Banco de Chile"
    assert metadata.product == "CUENTA VISTA"
    assert metadata.currency == "PESOS"
    assert metadata.period_start.isoformat() == "2026-07-31"
    assert metadata.period_end.isoformat() == "2026-08-31"
    assert metadata.statement_number is None
    assert metadata.page_number == 1
    assert metadata.total_pages == 1
    assert metadata.summary.opening_balance == 61_891
    assert metadata.summary.closing_balance == 68_251
    assert metadata.summary.one_day_retention == 0
    assert metadata.summary.multi_day_retention == 0
    assert metadata.summary.available_balance == 68_251
    assert metadata.masked_account_number == "XXXXXXXX"


def test_extract_statement_metadata_masks_numeric_account_number() -> None:
    pages = extract_pdf_text(SAMPLE_PDF.read_bytes())
    pages_with_numeric_account = (pages[0].replace("XXXXXXXX", "12345678"),)

    metadata = extract_statement_metadata(pages_with_numeric_account)

    assert metadata.masked_account_number == "****5678"


def test_extract_statement_metadata_masks_short_account_number() -> None:
    pages = extract_pdf_text(SAMPLE_PDF.read_bytes())
    pages_with_short_account = (pages[0].replace("XXXXXXXX", "1234"),)

    metadata = extract_statement_metadata(pages_with_short_account)

    assert metadata.masked_account_number == "*234"


def test_extract_statement_metadata_represents_missing_currency_as_absent() -> None:
    pages = extract_pdf_text(SAMPLE_PDF.read_bytes())
    pages_without_currency = (re.sub(r"MONEDA\s*:\s*PESOS", "", pages[0]),)

    metadata = extract_statement_metadata(pages_without_currency)

    assert metadata.currency is None


def test_extract_transactions_normalizes_supported_sample() -> None:
    pages = extract_pdf_text(SAMPLE_PDF.read_bytes())
    metadata = extract_statement_metadata(pages)

    transactions = extract_transactions(
        pages, metadata.period_start, metadata.period_end
    )

    assert len(transactions) == 6
    assert [transaction.movement_type for transaction in transactions] == [
        "debit",
        "debit",
        "debit",
        "debit",
        "debit",
        "credit",
    ]
    assert [transaction.amount for transaction in transactions] == [
        4_870,
        5_000,
        5_070,
        5_000,
        3_700,
        30_000,
    ]
    assert transactions[0].date.isoformat() == "2026-08-04"
    assert transactions[0].description == "PAGO:MERCADOPAGO MASAP"
    assert transactions[-1].reported_balance == 0


def test_extract_transactions_reconstructs_description_continuation() -> None:
    pages = extract_pdf_text(SAMPLE_PDF.read_bytes())
    metadata = extract_statement_metadata(pages)
    lines = pages[0].splitlines()
    first_transaction = next(
        index for index, line in enumerate(lines) if line.startswith("04/08")
    )
    lines[first_transaction] = lines[first_transaction].replace(" MASAP", "      ")
    lines.insert(first_transaction + 1, "         MASAP")
    wrapped_pages = ("\n".join(lines),)

    transactions = extract_transactions(
        wrapped_pages, metadata.period_start, metadata.period_end
    )

    assert transactions[0].description == "PAGO:MERCADOPAGO MASAP"


def test_extract_transactions_ignores_interleaved_sample_watermark() -> None:
    pages = extract_pdf_text(SAMPLE_PDF.read_bytes())
    metadata = extract_statement_metadata(pages)
    lines = pages[0].splitlines()
    first_transaction = next(
        index for index, line in enumerate(lines) if line.startswith("04/08")
    )
    lines.insert(first_transaction + 1, "         MUESTRA DIDÁCTICA")

    transactions = extract_transactions(
        ("\n".join(lines),), metadata.period_start, metadata.period_end
    )

    assert transactions[0].description == "PAGO:MERCADOPAGO MASAP"


def test_validate_statement_reconciles_supported_sample() -> None:
    pages = extract_pdf_text(SAMPLE_PDF.read_bytes())
    metadata = extract_statement_metadata(pages)
    transactions = extract_transactions(pages, metadata.period_start, metadata.period_end)

    validate_statement_completeness_and_reconciliation(metadata, transactions)


def test_validate_statement_rejects_incomplete_transaction_table() -> None:
    pages = extract_pdf_text(SAMPLE_PDF.read_bytes())
    metadata = extract_statement_metadata(pages)
    transactions = extract_transactions(pages, metadata.period_start, metadata.period_end)

    with pytest.raises(UnreliableExtractionError, match="do not reconcile"):
        validate_statement_completeness_and_reconciliation(metadata, transactions[:-1])


def test_validate_statement_rejects_inconsistent_closing_balance() -> None:
    pages = extract_pdf_text(SAMPLE_PDF.read_bytes())
    metadata = extract_statement_metadata(pages)
    transactions = extract_transactions(pages, metadata.period_start, metadata.period_end)
    inconsistent_metadata = replace(
        metadata,
        summary=replace(metadata.summary, closing_balance=0),
    )

    with pytest.raises(UnreliableExtractionError, match="do not reconcile"):
        validate_statement_completeness_and_reconciliation(
            inconsistent_metadata, transactions
        )


def test_parse_banco_chile_cuenta_vista_returns_accepted_statement() -> None:
    statement = parse_banco_chile_cuenta_vista(SAMPLE_PDF)

    assert statement.bank == "Banco de Chile"
    assert statement.product == "CUENTA VISTA"
    assert statement.currency == "PESOS"
    assert statement.period_start.isoformat() == "2026-07-31"
    assert statement.period_end.isoformat() == "2026-08-31"
    assert statement.summary.opening_balance == 61_891
    assert statement.summary.closing_balance == 68_251
    assert len(statement.transactions) == 6
    assert statement.transactions[-1].reported_balance == 0


def test_parse_banco_chile_cuenta_vista_returns_v2_normalized_statement() -> None:
    statement = parse_banco_chile_cuenta_vista(V2_SAMPLE_PDF)

    assert statement.bank == "Banco de Chile"
    assert statement.product == "CUENTA VISTA"
    assert statement.masked_account_number == "*****6789"
    assert statement.currency == "PESOS"
    assert statement.period_start.isoformat() == "2026-06-30"
    assert statement.period_end.isoformat() == "2026-07-31"
    assert statement.statement_number == "5"
    assert statement.page_number == 1
    assert statement.total_pages == 1
    assert statement.summary.opening_balance == 48_210
    assert statement.summary.closing_balance == 61_891
    assert statement.summary.one_day_retention == 0
    assert statement.summary.multi_day_retention == 0
    assert statement.summary.available_balance == 61_891
    assert [(transaction.date.isoformat(), transaction.description) for transaction in statement.transactions] == [
        ("2026-07-27", "TRASPASO A:Sociedad Procesadora De"),
        ("2026-07-27", "TRASPASO DE:ROSALES, PEDRO JUAN"),
        ("2026-07-28", "TRASPASO DE:ROSALES, PEDRO JUAN"),
        ("2026-07-28", "TRASPASO DE:ROSALES, PEDRO JUAN"),
        ("2026-07-29", "PAGO:SERVICIOS MEDICOS"),
        ("2026-07-30", "PAGO:CINEPLANET WEBPAY"),
    ]
    assert [transaction.amount for transaction in statement.transactions] == [
        5_000,
        30_000,
        50_000,
        50_000,
        91_519,
        19_800,
    ]
    assert [transaction.movement_type for transaction in statement.transactions] == [
        "debit",
        "credit",
        "credit",
        "credit",
        "debit",
        "debit",
    ]
    assert [transaction.document_number for transaction in statement.transactions] == [None] * 6
    assert [transaction.branch_or_channel for transaction in statement.transactions] == [
        "INTERNET",
        "INTERNET",
        "INTERNET",
        "INTERNET",
        "CENTRAL",
        "CENTRAL",
    ]
    assert [transaction.reported_balance for transaction in statement.transactions] == [
        0,
        73_210,
        0,
        173_210,
        81_691,
        0,
    ]


def test_parse_banco_chile_cuenta_vista_rejects_partial_extraction(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    pages = extract_pdf_text(SAMPLE_PDF.read_bytes())
    metadata = extract_statement_metadata(pages)
    complete_transactions = extract_transactions(
        pages, metadata.period_start, metadata.period_end
    )

    monkeypatch.setattr(
        "zut_balance.banco_chile_cuenta_vista.extract_transactions",
        lambda *_: complete_transactions[:-1],
    )

    with pytest.raises(UnreliableExtractionError, match="do not reconcile"):
        parse_banco_chile_cuenta_vista(SAMPLE_PDF.read_bytes())
