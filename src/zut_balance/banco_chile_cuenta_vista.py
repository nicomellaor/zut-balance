"""Recognition utilities for Banco de Chile Cuenta Vista statements."""

import re
import unicodedata
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path

from .errors import InvalidPdfError, UnreliableExtractionError, UnsupportedStatementError
from .models import MovementType, Statement, StatementMetadata, StatementSummary, Transaction
from .pdf_validation import extract_pdf_text


_REQUIRED_MARKERS = (
    "BANCO DE CHILE",
    "ESTADO DE CUENTA",
    "CUENTA VISTA",
    "DESDE",
    "HASTA",
    "DIA/MES",
    "DETALLE DE TRANSACCION",
    "CARGOS",
    "DEPOSITOS",
    "SALDO",
)


def parse_banco_chile_cuenta_vista(pdf: bytes | str | Path) -> Statement:
    """Parse a supported Banco de Chile Cuenta Vista PDF into a statement."""
    pdf_content = _read_pdf_content(pdf)
    pages = extract_pdf_text(pdf_content)
    validate_banco_chile_cuenta_vista_format(pages)
    metadata = extract_statement_metadata(pages)
    transactions = extract_transactions(
        pages, metadata.period_start, metadata.period_end
    )
    validate_statement_completeness_and_reconciliation(metadata, transactions)

    return Statement(
        bank=metadata.bank,
        product=metadata.product,
        masked_account_number=metadata.masked_account_number,
        currency=metadata.currency,
        period_start=metadata.period_start,
        period_end=metadata.period_end,
        statement_number=metadata.statement_number,
        page_number=metadata.page_number,
        total_pages=metadata.total_pages,
        summary=metadata.summary,
        transactions=transactions,
    )


def _read_pdf_content(pdf: bytes | str | Path) -> bytes:
    if isinstance(pdf, bytes):
        return pdf
    try:
        return Path(pdf).read_bytes()
    except OSError as error:
        raise InvalidPdfError("The PDF file could not be read") from error


def validate_banco_chile_cuenta_vista_format(pages: tuple[str, ...]) -> None:
    """Raise when extracted pages do not match the supported statement layout."""
    document_text = _normalize_document_text(pages)
    missing_markers = [
        marker for marker in _REQUIRED_MARKERS if marker not in document_text
    ]

    if missing_markers:
        raise UnsupportedStatementError(
            "The PDF does not match the Banco de Chile Cuenta Vista format"
        )


def extract_statement_metadata(pages: tuple[str, ...]) -> StatementMetadata:
    """Extract normalized header and summary data from a supported statement."""
    validate_banco_chile_cuenta_vista_format(pages)
    document_text = _normalize_document_text(pages)
    source_text = "\n".join(pages)

    return StatementMetadata(
        bank="Banco de Chile",
        product="CUENTA VISTA",
        masked_account_number=_extract_masked_account_number(source_text),
        currency=_optional_value(r"MONEDA\s*:\s*([A-Z]+)", document_text),
        period_start=_parse_date(_required_value(r"DESDE\s*:\s*(\d{2}/\d{2}/\d{4})", document_text, "period start")),
        period_end=_parse_date(_required_value(r"HASTA\s*:\s*(\d{2}/\d{2}/\d{4})", document_text, "period end")),
        statement_number=_optional_statement_number(source_text),
        page_number=_extract_page_number(document_text, 1),
        total_pages=_extract_page_number(document_text, 2),
        summary=_extract_summary(document_text),
    )


def extract_transactions(
    pages: tuple[str, ...], period_start: date, period_end: date
) -> tuple[Transaction, ...]:
    """Extract normalized transaction rows from a supported statement."""
    validate_banco_chile_cuenta_vista_format(pages)
    rows = _extract_transaction_rows(pages)
    if not rows:
        raise UnreliableExtractionError("No transaction rows could be extracted")

    return tuple(
        Transaction(
            date=_transaction_date(row.day_month, period_start, period_end),
            description=row.description,
            document_number=row.document_number,
            branch_or_channel=row.branch_or_channel,
            amount=row.amount,
            movement_type=row.movement_type,
            reported_balance=row.reported_balance,
        )
        for row in rows
    )


def validate_statement_completeness_and_reconciliation(
    metadata: StatementMetadata, transactions: tuple[Transaction, ...]
) -> None:
    """Reject incomplete transactions and statements with inconsistent final balances."""
    if not transactions:
        raise UnreliableExtractionError("No transaction rows could be extracted")

    for transaction in transactions:
        if not transaction.description or transaction.amount <= 0:
            raise UnreliableExtractionError("A transaction contains incomplete required data")
        if not metadata.period_start <= transaction.date <= metadata.period_end:
            raise UnreliableExtractionError("A transaction falls outside the statement period")

    total_debits = sum(
        transaction.amount
        for transaction in transactions
        if transaction.movement_type is MovementType.DEBIT
    )
    total_credits = sum(
        transaction.amount
        for transaction in transactions
        if transaction.movement_type is MovementType.CREDIT
    )
    expected_closing_balance = (
        metadata.summary.opening_balance - total_debits + total_credits
    )
    if expected_closing_balance != metadata.summary.closing_balance:
        raise UnreliableExtractionError("The statement balances do not reconcile")


@dataclass
class _TransactionRow:
    day_month: str
    description: str
    document_number: str | None
    branch_or_channel: str | None
    amount: int
    movement_type: MovementType
    reported_balance: int | None


def _extract_transaction_rows(pages: tuple[str, ...]) -> list[_TransactionRow]:
    rows: list[_TransactionRow] = []
    for page in pages:
        lines = page.splitlines()
        header_index = next(
            (index for index, line in enumerate(lines) if "DIA/MES" in line), None
        )
        if header_index is None:
            raise UnreliableExtractionError("The transaction table header is missing")

        header = lines[header_index]
        columns = _transaction_columns(header)
        for line in lines[header_index + 1 :]:
            if "SALDO FINAL" in line:
                break
            if not line.strip() or "SALDO INICIAL" in line:
                continue
            if _is_non_transaction_text(line):
                continue

            match = re.match(r"\s*(\d{2}/\d{2})\s+", line)
            if match is None:
                if rows:
                    _append_description_continuation(rows[-1], line, columns)
                continue

            rows.append(_parse_transaction_row(line, match.group(1), columns))
    return rows


def _transaction_columns(header: str) -> tuple[int, int, int, int, int, int]:
    try:
        description_start = header.index("DETALLE")
        document_start = header.index("N° DOCTO")
        branch_start = header.index("SUCURSAL")
        deposit_start = header.index("O ABONOS")
        balance_start = header.index("SALDO", deposit_start)
    except ValueError as error:
        raise UnreliableExtractionError("The transaction columns could not be located") from error
    charge_start = header.index("CARGOS") - 20
    return description_start, document_start, branch_start, charge_start, deposit_start, balance_start


def _parse_transaction_row(
    line: str, day_month: str, columns: tuple[int, int, int, int, int, int]
) -> _TransactionRow:
    description_start, document_start, branch_start, charge_start, deposit_start, balance_start = columns
    values = list(re.finditer(r"\d{1,3}(?:\.\d{3})*|\d+", line[charge_start:]))
    if not values:
        raise UnreliableExtractionError("A transaction must have an amount")

    amount_match = values[0]
    amount_position = charge_start + amount_match.start()
    amount = _parse_clp(amount_match.group())
    reported_balance = _parse_clp(values[1].group()) if len(values) > 1 else None
    if len(values) > 2:
        raise UnreliableExtractionError("A transaction row contains unexpected monetary values")

    return _TransactionRow(
        day_month=day_month,
        description=_clean_cell(line[description_start:document_start]),
        document_number=_optional_cell(line[document_start:branch_start]),
        branch_or_channel=_optional_cell(line[branch_start:charge_start]),
        amount=amount,
        movement_type=(
            MovementType.DEBIT
            if amount_position < deposit_start
            else MovementType.CREDIT
        ),
        reported_balance=reported_balance,
    )


def _append_description_continuation(
    row: _TransactionRow, line: str, columns: tuple[int, int, int, int, int, int]
) -> None:
    description_start, document_start, _, _, _, _ = columns
    continuation = _clean_cell(line[description_start:document_start])
    if continuation:
        row.description = f"{row.description} {continuation}"


def _is_non_transaction_text(line: str) -> bool:
    normalized_line = _normalize_document_text((line,))
    return any(
        marker in normalized_line
        for marker in (
            "MUESTRA DIDACTICA",
            "MUESTRADIDACTICA",
            "DOCUMENTO DE EJEMPLO",
            "INFORMESE SOBRE LA GARANTIA ESTATAL",
        )
    )


def _clean_cell(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def _optional_cell(value: str) -> str | None:
    normalized = _clean_cell(value)
    return normalized or None


def _transaction_date(day_month: str, period_start: date, period_end: date) -> date:
    day, month = (int(part) for part in day_month.split("/"))
    candidates = []
    for year in range(period_start.year, period_end.year + 1):
        try:
            candidate = date(year, month, day)
        except ValueError:
            continue
        if period_start <= candidate <= period_end:
            candidates.append(candidate)

    if len(candidates) != 1:
        raise UnreliableExtractionError("The transaction year could not be determined")
    return candidates[0]


def _extract_masked_account_number(source_text: str) -> str | None:
    match = re.search(r"N[°ºO]\s*DE\s*CUENTA\s*:\s*([^\n]+)", source_text, re.IGNORECASE)
    if match is None:
        return None

    account_number = match.group(1).strip()
    if not account_number:
        return None
    if set(account_number) <= {"X", "*"}:
        return account_number

    digits = re.sub(r"\D", "", account_number)
    if not digits:
        raise UnreliableExtractionError("The account number could not be normalized")
    visible_digits = min(4, max(len(digits) - 1, 0))
    if not visible_digits:
        return "*" * len(digits)
    return f"{'*' * (len(digits) - visible_digits)}{digits[-visible_digits:]}"


def _optional_statement_number(source_text: str) -> str | None:
    match = re.search(r"CARTOLA\s+N[°ºO][ \t]*:[ \t]*([^\n]+)", source_text, re.IGNORECASE)
    return match.group(1).strip() if match and match.group(1).strip() else None


def _extract_page_number(document_text: str, position: int) -> int | None:
    match = re.search(r"N[°ºO]\s*DE\s*PAGINA\s*:\s*(\d+)\s+DE\s+(\d+)", document_text)
    return int(match.group(position)) if match else None


def _extract_summary(document_text: str) -> StatementSummary:
    opening_balance = _parse_clp(
        _required_value(r"\d{2}/\d{2}\s+SALDO INICIAL\s+([\d.]+)", document_text, "opening balance")
    )
    closing_balance = _parse_clp(
        _required_value(r"\d{2}/\d{2}\s+SALDO FINAL\s+([\d.]+)", document_text, "closing balance")
    )
    match = re.search(
        r"RETENCION A 1 DIA\s+RETENCION A MAS DE 1 DIA\s+SALDO DISPONIBLE A LA FECHA\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)",
        document_text,
    )
    if match is None:
        raise UnreliableExtractionError("The statement summary could not be extracted")

    return StatementSummary(
        opening_balance=opening_balance,
        closing_balance=closing_balance,
        one_day_retention=_parse_clp(match.group(1)),
        multi_day_retention=_parse_clp(match.group(2)),
        available_balance=_parse_clp(match.group(3)),
    )


def _required_value(pattern: str, document_text: str, field: str) -> str:
    match = re.search(pattern, document_text)
    if match is None:
        raise UnreliableExtractionError(f"The {field} could not be extracted")
    return match.group(1)


def _optional_value(pattern: str, document_text: str) -> str | None:
    match = re.search(pattern, document_text)
    return match.group(1) if match else None


def _parse_date(value: str):
    return datetime.strptime(value, "%d/%m/%Y").date()


def _parse_clp(value: str) -> int:
    if not re.fullmatch(r"\d{1,3}(?:\.\d{3})*|\d+", value):
        raise UnreliableExtractionError("The monetary value could not be normalized")
    return int(value.replace(".", ""))


def _normalize_document_text(pages: tuple[str, ...]) -> str:
    text = " ".join(pages).upper()
    text = unicodedata.normalize("NFKD", text)
    text = "".join(character for character in text if not unicodedata.combining(character))
    return re.sub(r"\s+", " ", text)
