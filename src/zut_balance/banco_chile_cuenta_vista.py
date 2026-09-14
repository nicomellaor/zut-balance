"""Recognition utilities for Banco de Chile Cuenta Vista statements."""

import re
import unicodedata
from dataclasses import dataclass, replace
from datetime import date, datetime
from pathlib import Path

from .errors import InvalidPdfError, UnreliableExtractionError, UnsupportedStatementError
from .models import MovementType, Statement, StatementMetadata, StatementSummary, Transaction
from .pdf_validation import extract_pdf_text


_ORIGINAL_REQUIRED_MARKERS = (
    "BANCO DE CHILE",
    "ESTADO DE CUENTA",
    "CUENTA VISTA",
    "DESDE",
    "HASTA",
    "DIA/MES",
    "DETALLE DE TRANSACCION",
    "CARGOS",
    "SALDO",
)
_V2_REQUIRED_MARKERS = (
    "ESTADO DE CUENTA",
    "CUENTA VISTA",
    "EJECUTIVO DE CUENTA",
    "DE CUENTA",
    "MONEDA",
    "CARTOLA N",
    "DESDE",
    "HASTA",
    "FECHA",
    "DIA/MES",
    "DETALLE DE TRANSACCION",
    "SUCURSAL",
    "MONTO CARGOS",
    "MONTO DEPOSITOS",
    "SALDO",
)
_MONEY_PATTERN = r"\d{1,3}(?:\.\d{3})*|\d+"


@dataclass(frozen=True)
class _Page:
    text: str
    normalized: str
    number: int | None
    total: int | None
    table_header_index: int | None


@dataclass(frozen=True)
class _TransactionColumns:
    description_start: int
    description_end: int
    document_start: int
    document_end: int
    branch_start: int
    branch_end: int
    monetary_start: int
    credit_start: int
    balance_start: int
    branch_before_document: bool


@dataclass
class _TransactionRow:
    day_month: str
    description: str
    document_number: str | None
    branch_or_channel: str | None
    amount: int
    movement_type: MovementType
    reported_balance: int | None


def parse_banco_chile_cuenta_vista(pdf: bytes | str | Path) -> Statement:
    """Parse a supported Banco de Chile Cuenta Vista PDF into a statement."""
    pdf_content = _read_pdf_content(pdf)
    pages = extract_pdf_text(pdf_content)
    validate_banco_chile_cuenta_vista_format(pages)
    metadata = extract_statement_metadata(pages)
    if metadata.masked_account_number is None:
        metadata = replace(
            metadata,
            masked_account_number=_consistent_optional_value(
                [_extract_masked_account_number(page) for page in extract_pdf_text(pdf_content, extraction_mode=None)],
                "account number",
            ),
        )
    transactions = extract_transactions(pages, metadata.period_start, metadata.period_end)
    _validate_document_evidence(pages, transactions)
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
    if not _has_required_markers(document_text, _ORIGINAL_REQUIRED_MARKERS) and not _has_required_markers(
        document_text, _V2_REQUIRED_MARKERS
    ):
        raise UnsupportedStatementError(
            "The PDF does not match the Banco de Chile Cuenta Vista format"
        )


def extract_statement_metadata(pages: tuple[str, ...]) -> StatementMetadata:
    """Extract normalized header and summary data from a supported statement."""
    validate_banco_chile_cuenta_vista_format(pages)
    page_details = _analyze_pages(pages)
    period_start_value = _consistent_optional_value(
        [_optional_value(r"DESDE\s*:\s*(\d{2}/\d{2}/\d{4})", page.normalized) for page in page_details],
        "period start",
    )
    period_end_value = _consistent_optional_value(
        [_optional_value(r"HASTA\s*:\s*(\d{2}/\d{2}/\d{4})", page.normalized) for page in page_details],
        "period end",
    )
    if period_start_value is None or period_end_value is None:
        raise UnreliableExtractionError("The statement period could not be extracted")
    period_start = _parse_date(period_start_value)
    period_end = _parse_date(period_end_value)
    if period_start > period_end:
        raise UnreliableExtractionError("The statement period is invalid")

    summaries = [
        summary
        for page in page_details
        if (summary := _optional_summary(page.normalized)) is not None
    ]
    if not summaries:
        raise UnreliableExtractionError("The statement summary could not be extracted")

    return StatementMetadata(
        bank="Banco de Chile",
        product="CUENTA VISTA",
        masked_account_number=_consistent_optional_value(
            [_extract_masked_account_number(page.text) for page in page_details],
            "account number",
        ),
        currency=_consistent_optional_value(
            [_optional_value(r"MONEDA\s*:\s*([A-Z]+)", page.normalized) for page in page_details],
            "currency",
        ),
        period_start=period_start,
        period_end=period_end,
        statement_number=_consistent_optional_value(
            [_optional_statement_number(page.text) for page in page_details],
            "statement number",
        ),
        page_number=page_details[0].number,
        total_pages=page_details[0].total,
        summary=_consistent_value(summaries, "statement summary"),
    )


def extract_transactions(
    pages: tuple[str, ...], period_start: date, period_end: date
) -> tuple[Transaction, ...]:
    """Extract normalized transaction rows from a supported statement."""
    validate_banco_chile_cuenta_vista_format(pages)
    if period_start > period_end:
        raise UnreliableExtractionError("The statement period is invalid")
    rows = _extract_transaction_rows(_analyze_pages(pages))
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
    expected_closing_balance = metadata.summary.opening_balance - total_debits + total_credits
    if expected_closing_balance != metadata.summary.closing_balance:
        raise UnreliableExtractionError("The statement balances do not reconcile")


def _analyze_pages(pages: tuple[str, ...]) -> tuple[_Page, ...]:
    page_details = tuple(
        _Page(
            text=page,
            normalized=_normalize_document_text((page,)),
            number=_page_marker(page, 1),
            total=_page_marker(page, 2),
            table_header_index=_table_header_index(page),
        )
        for page in pages
    )
    declared_pages = [page for page in page_details if page.number is not None]
    if not declared_pages:
        if len(page_details) > 1:
            raise UnreliableExtractionError("The statement pagination is missing")
        return page_details
    if len(declared_pages) != len(page_details) or any(page.total is None for page in page_details):
        raise UnreliableExtractionError("The statement pagination is incomplete")

    totals = {page.total for page in page_details}
    if len(totals) != 1 or None in totals:
        raise UnreliableExtractionError("The statement pagination is inconsistent")
    total = totals.pop()
    if total != len(page_details):
        raise UnreliableExtractionError("The statement page total does not match the PDF")
    if [page.number for page in page_details] != list(range(1, total + 1)):
        raise UnreliableExtractionError("The statement page sequence is inconsistent")
    return page_details


def _page_marker(page: str, position: int) -> int | None:
    match = re.search(r"N[°ºO]\s*DE\s*PAGINA\s*:\s*(\d+)\s+DE\s*(\d+)", page, re.IGNORECASE)
    return int(match.group(position)) if match else None


def _table_header_index(page: str) -> int | None:
    return next(
        (index for index, line in enumerate(page.splitlines()) if "DIA/MES" in line.upper()),
        None,
    )


def _extract_transaction_rows(pages: tuple[_Page, ...]) -> list[_TransactionRow]:
    rows: list[_TransactionRow] = []
    for page in pages:
        if page.table_header_index is None:
            if _contains_transaction_candidate(page.text):
                raise UnreliableExtractionError("The transaction table header is missing")
            continue

        lines = page.text.splitlines()
        table_header = lines[page.table_header_index]
        if "DETALLE DE TRANSACCION" not in table_header.upper():
            if page.table_header_index == 0:
                raise UnreliableExtractionError("The transaction columns could not be located")
            table_header = lines[page.table_header_index - 1]
        columns = _transaction_columns(table_header)
        for line in lines[page.table_header_index + 1 :]:
            if "SALDO FINAL" in _normalize_document_text((line,)):
                break
            if not line.strip() or "SALDO INICIAL" in _normalize_document_text((line,)):
                continue
            if _is_non_transaction_text(line):
                continue

            match = re.match(r"\s*(\d{2}/\d{2})\s+", line)
            if match is None:
                _append_description_continuation(rows, line, columns)
                continue
            rows.append(_parse_transaction_row(line, match.group(1), match.end(), columns))
    return rows


def _contains_transaction_candidate(page: str) -> bool:
    return any(
        re.match(r"\s*\d{2}/\d{2}\s+", line)
        and "SALDO" not in _normalize_document_text((line,))
        for line in page.splitlines()
    )


def _transaction_columns(header: str) -> _TransactionColumns:
    labels = {
        "description": r"DETALLE\s+DE\s+TRANSACCION",
        "document": r"N[°ºO]\s*DOCTO",
        "branch": r"SUCURSAL",
        "debit": r"(?:MONTO\s+)?CARGOS",
        "credit": r"(?:MONTO\s+DEPOSITOS|O\s+ABONOS)",
        "balance": r"SALDO",
    }
    positions = {}
    for name, pattern in labels.items():
        match = re.search(pattern, header, re.IGNORECASE)
        if match is None:
            raise UnreliableExtractionError("The transaction columns could not be located")
        positions[name] = match.start()

    text_columns = sorted((positions["document"], positions["branch"]))
    ordered = [positions["description"], *text_columns, positions["debit"], positions["credit"], positions["balance"]]
    if ordered != sorted(ordered) or len(set(ordered)) != len(ordered):
        raise UnreliableExtractionError("The transaction columns are ambiguous")
    if positions["branch"] < positions["document"]:
        branch_start = (positions["description"] + positions["branch"]) // 2
        branch_end = (positions["branch"] + positions["document"]) // 2
        document_start = branch_end
        document_end = (positions["document"] + positions["debit"]) // 2
    else:
        branch_start = positions["branch"]
        branch_end = positions["debit"]
        document_start = positions["document"]
        document_end = positions["branch"]
    return _TransactionColumns(
        description_start=positions["description"],
        description_end=text_columns[0],
        document_start=document_start,
        document_end=document_end,
        branch_start=branch_start,
        branch_end=branch_end,
        monetary_start=(text_columns[-1] + positions["debit"]) // 2,
        credit_start=positions["credit"],
        balance_start=positions["balance"],
        branch_before_document=positions["branch"] < positions["document"],
    )


def _parse_transaction_row(
    line: str, day_month: str, description_start: int, columns: _TransactionColumns
) -> _TransactionRow:
    values = list(re.finditer(_MONEY_PATTERN, line[columns.monetary_start :]))
    if not values:
        raise UnreliableExtractionError("A transaction must have an amount")
    if len(values) > 2:
        raise UnreliableExtractionError("A transaction row contains unexpected monetary values")

    amount_match = values[0]
    amount_position = columns.monetary_start + amount_match.start()
    description = _clean_cell(line[description_start : columns.description_end])
    document_number = _optional_cell(line[columns.document_start : columns.document_end])
    branch_or_channel = _optional_cell(line[columns.branch_start : columns.branch_end])
    if columns.branch_before_document:
        cells = re.split(r"\s{2,}", line.strip())
        if len(cells) != 5 or cells[0] != day_month:
            raise UnreliableExtractionError("A transaction row is incomplete")
        description = cells[1]
        document_number = None
        branch_or_channel = cells[2]
    return _TransactionRow(
        day_month=day_month,
        description=description,
        document_number=document_number,
        branch_or_channel=branch_or_channel,
        amount=_parse_clp(amount_match.group()),
        movement_type=(
            MovementType.DEBIT
            if amount_position < columns.credit_start
            else MovementType.CREDIT
        ),
        reported_balance=_parse_clp(values[1].group()) if len(values) == 2 else None,
    )


def _append_description_continuation(
    rows: list[_TransactionRow], line: str, columns: _TransactionColumns
) -> None:
    if not rows:
        return
    if re.search(_MONEY_PATTERN, line[columns.monetary_start :]):
        raise UnreliableExtractionError("A transaction continuation contains monetary data")
    if _clean_cell(line[columns.document_start : columns.document_end]) or _clean_cell(
        line[columns.branch_start : columns.branch_end]
    ):
        raise UnreliableExtractionError("A transaction continuation contains other columns")
    continuation = _clean_cell(line[columns.description_start : columns.document_start])
    if continuation:
        rows[-1].description = f"{rows[-1].description} {continuation}"


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


def _validate_document_evidence(
    pages: tuple[str, ...], transactions: tuple[Transaction, ...]
) -> None:
    document_text = _normalize_document_text(pages)
    declared_count = _optional_int(r"TOTAL MOVIMIENTOS\s*:\s*(\d+)", document_text)
    if declared_count is not None and declared_count != len(transactions):
        raise UnreliableExtractionError("The statement transaction count is inconsistent")

    declared_debits = _optional_money(r"TOTAL CARGOS\s*:\s*([\d.]+)", document_text)
    actual_debits = sum(transaction.amount for transaction in transactions if transaction.movement_type is MovementType.DEBIT)
    if declared_debits is not None and declared_debits != actual_debits:
        raise UnreliableExtractionError("The statement debit total is inconsistent")

    declared_credits = _optional_money(r"TOTAL ABONOS\s*:\s*([\d.]+)", document_text)
    actual_credits = sum(transaction.amount for transaction in transactions if transaction.movement_type is MovementType.CREDIT)
    if declared_credits is not None and declared_credits != actual_credits:
        raise UnreliableExtractionError("The statement credit total is inconsistent")


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
    if match is None:
        return None
    statement_number = re.split(r"\s+N[°ºO]\s*DE\s*PAGINA", match.group(1), flags=re.IGNORECASE)[0].strip()
    return statement_number or None


def _optional_summary(document_text: str) -> StatementSummary | None:
    if "SALDO INICIAL" not in document_text or "SALDO FINAL" not in document_text:
        return None
    return _extract_summary(document_text)


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


def _consistent_value(values: list[object], field: str):
    if not values:
        raise UnreliableExtractionError(f"The {field} could not be extracted")
    if any(value != values[0] for value in values[1:]):
        raise UnreliableExtractionError(f"The {field} is inconsistent across pages")
    return values[0]


def _consistent_optional_value(values: list[str | None], field: str) -> str | None:
    present_values = [value for value in values if value is not None]
    if not present_values:
        return None
    return _consistent_value(present_values, field)


def _required_value(pattern: str, document_text: str, field: str) -> str:
    match = re.search(pattern, document_text)
    if match is None:
        raise UnreliableExtractionError(f"The {field} could not be extracted")
    return match.group(1)


def _optional_value(pattern: str, document_text: str) -> str | None:
    match = re.search(pattern, document_text)
    return match.group(1) if match else None


def _optional_int(pattern: str, document_text: str) -> int | None:
    match = re.search(pattern, document_text)
    return int(match.group(1)) if match else None


def _optional_money(pattern: str, document_text: str) -> int | None:
    match = re.search(pattern, document_text)
    return _parse_clp(match.group(1)) if match else None


def _parse_date(value: str) -> date:
    try:
        return datetime.strptime(value, "%d/%m/%Y").date()
    except ValueError as error:
        raise UnreliableExtractionError("The statement period date is invalid") from error


def _parse_clp(value: str) -> int:
    if not re.fullmatch(_MONEY_PATTERN, value):
        raise UnreliableExtractionError("The monetary value could not be normalized")
    return int(value.replace(".", ""))


def _clean_cell(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def _optional_cell(value: str) -> str | None:
    normalized = _clean_cell(value)
    return normalized or None


def _normalize_document_text(pages: tuple[str, ...]) -> str:
    text = " ".join(pages).upper()
    text = unicodedata.normalize("NFKD", text)
    text = "".join(character for character in text if not unicodedata.combining(character))
    return re.sub(r"\s+", " ", text)


def _has_required_markers(document_text: str, markers: tuple[str, ...]) -> bool:
    return all(marker in document_text for marker in markers)
