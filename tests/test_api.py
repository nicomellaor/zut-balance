from pathlib import Path

from fastapi.testclient import TestClient

from zut_balance import api
from zut_balance.api import MAX_FILE_SIZE_BYTES, app
from zut_balance.banco_chile_cuenta_vista import parse_banco_chile_cuenta_vista
from zut_balance.errors import UnsupportedStatementError


FIXTURE_PDF = Path(__file__).parent.parent / "media" / "cartola_ejemplo_banco_chile.pdf"


client = TestClient(app)


def test_health_reports_service_availability() -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_statement_upload_requires_one_file_named_file() -> None:
    response = client.post("/v1/statements")

    assert response.status_code == 400
    assert response.json() == {
        "error": {
            "code": "invalid_upload",
            "message": "Provide exactly one PDF file named file",
        }
    }


def test_statement_upload_rejects_multiple_files() -> None:
    response = client.post(
        "/v1/statements",
        files=[
            ("file", ("first.pdf", b"%PDF-1.7", "application/pdf")),
            ("file", ("second.pdf", b"%PDF-1.7", "application/pdf")),
        ],
    )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "invalid_upload"


def test_statement_upload_rejects_empty_or_non_pdf_files() -> None:
    empty_response = client.post(
        "/v1/statements",
        files={"file": ("empty.pdf", b"", "application/pdf")},
    )
    non_pdf_response = client.post(
        "/v1/statements",
        files={"file": ("statement.txt", b"not a PDF", "text/plain")},
    )

    assert empty_response.status_code == 400
    assert empty_response.json()["error"]["code"] == "empty_file"
    assert non_pdf_response.status_code == 400
    assert non_pdf_response.json()["error"]["code"] == "invalid_file_type"


def test_statement_upload_rejects_content_without_pdf_signature() -> None:
    response = client.post(
        "/v1/statements",
        files={"file": ("statement.pdf", b"not a PDF", "application/pdf")},
    )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "invalid_pdf"


def test_statement_upload_returns_structured_error_for_malformed_multipart() -> None:
    response = client.post(
        "/v1/statements",
        content=b"--missing-boundary\r\n",
        headers={"content-type": "multipart/form-data; boundary=declared-boundary"},
    )

    assert response.status_code == 400
    assert response.json() == {
        "error": {
            "code": "invalid_request",
            "message": "The request could not be processed",
        }
    }


def test_statement_upload_rejects_file_larger_than_limit() -> None:
    response = client.post(
        "/v1/statements",
        files={"file": ("statement.pdf", b"%PDF-" + b"0" * MAX_FILE_SIZE_BYTES, "application/pdf")},
    )

    assert response.status_code == 413
    assert response.json()["error"]["code"] == "file_too_large"


def test_statement_upload_rejects_pdf_with_too_many_pages(monkeypatch) -> None:
    class ReaderWithTooManyPages:
        pages = [object()] * 21

    monkeypatch.setattr(api, "PdfReader", lambda _: ReaderWithTooManyPages())

    response = client.post(
        "/v1/statements",
        files={"file": ("statement.pdf", b"%PDF-1.7", "application/pdf")},
    )

    assert response.status_code == 413
    assert response.json()["error"]["code"] == "too_many_pages"


def test_statement_upload_returns_the_normalized_statement() -> None:
    content = FIXTURE_PDF.read_bytes()
    statement = parse_banco_chile_cuenta_vista(content)

    response = client.post(
        "/v1/statements",
        files={"file": ("statement.pdf", content, "application/pdf")},
    )

    assert response.status_code == 200
    assert response.json()["metadata"] == {
        "bank": statement.bank,
        "product": statement.product,
        "masked_account_number": statement.masked_account_number,
        "currency": statement.currency,
        "period_start": statement.period_start.isoformat(),
        "period_end": statement.period_end.isoformat(),
        "statement_number": statement.statement_number,
        "page_number": statement.page_number,
        "total_pages": statement.total_pages,
    }
    assert response.json()["summary"] == {
        "opening_balance": statement.summary.opening_balance,
        "closing_balance": statement.summary.closing_balance,
        "one_day_retention": statement.summary.one_day_retention,
        "multi_day_retention": statement.summary.multi_day_retention,
        "available_balance": statement.summary.available_balance,
    }
    assert response.json()["transactions"] == [
        {
            "date": transaction.date.isoformat(),
            "description": transaction.description,
            "document_number": transaction.document_number,
            "branch_or_channel": transaction.branch_or_channel,
            "amount": transaction.amount,
            "movement_type": transaction.movement_type.value,
            "reported_balance": transaction.reported_balance,
        }
        for transaction in statement.transactions
    ]


def test_statement_upload_rejects_invalid_pdf_without_parser_details() -> None:
    response = client.post(
        "/v1/statements",
        files={"file": ("statement.pdf", b"%PDF-1.7", "application/pdf")},
    )

    assert response.status_code == 400
    assert response.json() == {
        "error": {
            "code": "invalid_pdf",
            "message": "The uploaded file is not a valid PDF",
        }
    }


def test_statement_upload_maps_rejected_statement_to_safe_error(monkeypatch) -> None:
    class ReaderWithOnePage:
        pages = [object()]

    monkeypatch.setattr(api, "PdfReader", lambda _: ReaderWithOnePage())
    monkeypatch.setattr(
        api,
        "parse_banco_chile_cuenta_vista",
        lambda _: (_ for _ in ()).throw(UnsupportedStatementError("Sensitive parser detail")),
    )

    response = client.post(
        "/v1/statements",
        files={"file": ("statement.pdf", b"%PDF-1.7", "application/pdf")},
    )

    assert response.status_code == 400
    assert response.json() == {
        "error": {
            "code": "statement_rejected",
            "message": "The statement could not be processed",
        }
    }


def test_statement_upload_hides_unexpected_errors(monkeypatch) -> None:
    class ReaderWithOnePage:
        pages = [object()]

    monkeypatch.setattr(api, "PdfReader", lambda _: ReaderWithOnePage())
    monkeypatch.setattr(
        api,
        "parse_banco_chile_cuenta_vista",
        lambda _: (_ for _ in ()).throw(RuntimeError("Sensitive stack detail")),
    )

    response = client.post(
        "/v1/statements",
        files={"file": ("statement.pdf", b"%PDF-1.7", "application/pdf")},
    )

    assert response.status_code == 500
    assert response.json() == {
        "error": {
            "code": "internal_error",
            "message": "The statement could not be processed",
        }
    }
