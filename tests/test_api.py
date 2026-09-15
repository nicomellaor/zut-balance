from pathlib import Path
import re
import sqlite3
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from unittest.mock import ANY

from fastapi.testclient import TestClient
import pytest

from zut_balance import api
from zut_balance.api import MAX_FILE_SIZE_BYTES, ServiceSettings, create_app
from zut_balance.banco_chile_cuenta_vista import parse_banco_chile_cuenta_vista
from zut_balance.categorization import classify_transaction
from zut_balance.errors import UnsupportedStatementError
from zut_balance.persistence import DatabaseBusyError
from argon2 import PasswordHasher


FIXTURE_PDF = Path(__file__).parent.parent / "media" / "cartola_ejemplo_banco_chile.pdf"
V2_FIXTURE_PDF = Path(__file__).parent.parent / "media" / "cartola_v2_ejemplo_banco_chile.pdf"
API_KEY = "test-api-key"
AUTHORIZATION = {"Authorization": f"Bearer {API_KEY}"}


@pytest.fixture
def client(tmp_path: Path) -> TestClient:
    return TestClient(
        create_app(ServiceSettings(tmp_path / "statements.sqlite3", API_KEY))
    )


def _upload(client: TestClient, content: bytes, **kwargs: object):
    return client.post(
        "/v1/statements",
        files={"file": ("statement.pdf", content, "application/pdf")},
        headers=AUTHORIZATION,
        **kwargs,
    )


def _transaction_response(transaction):
    classification = classify_transaction(transaction, "")
    return {
        "date": transaction.date.isoformat(),
        "description": transaction.description,
        "document_number": transaction.document_number,
        "branch_or_channel": transaction.branch_or_channel,
        "amount": transaction.amount,
        "movement_type": transaction.movement_type.value,
        "reported_balance": transaction.reported_balance,
        "classification": {
            "category": classification.category.value,
            "merchant_name": classification.merchant_name,
            "rule_id": classification.rule_id,
            "ruleset_version": classification.ruleset_version,
        },
    }


def test_health_reports_service_availability_without_authentication(client: TestClient) -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_data_routes_require_a_valid_api_key(client: TestClient, monkeypatch) -> None:
    monkeypatch.setattr(
        api,
        "parse_banco_chile_cuenta_vista",
        lambda _: (_ for _ in ()).throw(AssertionError("parser should not run")),
    )

    response = client.post(
        "/v1/statements",
        files={"file": ("statement.pdf", FIXTURE_PDF.read_bytes(), "application/pdf")},
    )

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "unauthorized"
    for path, method in (
        ("/v1/statements", client.get),
        ("/v1/statements/missing", client.get),
        ("/v1/statements/missing", client.delete),
    ):
        assert method(path, headers={"Authorization": "Bearer wrong"}).status_code == 401
    for authorization in ("", "Basic ignored", "Bearer "):
        assert client.get(
            "/v1/statements", headers={"Authorization": authorization}
        ).status_code == 401


def test_data_routes_require_explicit_configuration(tmp_path: Path) -> None:
    for settings in (
        ServiceSettings(None, API_KEY),
        ServiceSettings(tmp_path / "configured.sqlite3", None),
    ):
        client = TestClient(create_app(settings))

        response = client.get("/v1/statements", headers=AUTHORIZATION)

        assert response.status_code == 500
        assert response.json()["error"]["code"] == "service_not_configured"


def test_cors_allows_only_configured_origins(tmp_path: Path) -> None:
    client = TestClient(
        create_app(
            ServiceSettings(
                tmp_path / "statements.sqlite3",
                API_KEY,
                ("http://localhost:5173",),
            )
        )
    )

    allowed = client.options(
        "/v1/statements",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "GET",
        },
    )
    denied = client.options(
        "/v1/statements",
        headers={
            "Origin": "http://untrusted.example",
            "Access-Control-Request-Method": "GET",
        },
    )

    assert allowed.headers["access-control-allow-origin"] == "http://localhost:5173"
    assert "*" not in allowed.headers["access-control-allow-origin"]
    assert "access-control-allow-origin" not in denied.headers


@pytest.fixture
def web_client(tmp_path: Path) -> TestClient:
    return TestClient(
        create_app(
            ServiceSettings(
                tmp_path / "statements.sqlite3",
                API_KEY,
                web_auth_enabled=True,
                admin_password_hash=PasswordHasher().hash("admin-password"),
                session_secret="s" * 32,
                trusted_origins=("https://zut.test",),
            )
        )
    )


def test_web_login_logout_and_bearer_precedence(web_client: TestClient) -> None:
    denied = web_client.post("/v1/auth/login", json={"password": "wrong"})
    login = web_client.post("/v1/auth/login", json={"password": "admin-password"})
    session_response = web_client.get("/v1/statements?limit=1&offset=0")
    invalid_bearer = web_client.get(
        "/v1/statements?limit=1&offset=0", headers={"Authorization": "Bearer wrong"}
    )
    logout = web_client.post("/v1/auth/logout")
    after_logout = web_client.get("/v1/statements?limit=1&offset=0")

    assert denied.status_code == 401
    assert login.status_code == 204
    assert "Max-Age=28800" in login.headers["set-cookie"]
    assert "httponly" in login.headers["set-cookie"]
    assert "samesite=strict" in login.headers["set-cookie"]
    assert session_response.status_code == 200
    assert invalid_bearer.status_code == 401
    assert logout.status_code == 204
    assert after_logout.status_code == 401


def test_session_mutations_require_a_trusted_origin(web_client: TestClient) -> None:
    web_client.post("/v1/auth/login", json={"password": "admin-password"})

    denied = web_client.delete("/v1/statements/missing")
    allowed = web_client.delete(
        "/v1/statements/missing", headers={"Origin": "https://zut.test"}
    )

    assert denied.status_code == 403
    assert allowed.status_code == 404


def test_statement_upload_requires_one_file_named_file(client: TestClient) -> None:
    response = client.post("/v1/statements", headers=AUTHORIZATION)

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "invalid_upload"


def test_statement_upload_rejects_multiple_files(client: TestClient) -> None:
    response = client.post(
        "/v1/statements",
        files=[
            ("file", ("first.pdf", b"%PDF-1.7", "application/pdf")),
            ("file", ("second.pdf", b"%PDF-1.7", "application/pdf")),
        ],
        headers=AUTHORIZATION,
    )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "invalid_upload"


def test_statement_upload_rejects_empty_or_non_pdf_files(client: TestClient) -> None:
    empty_response = _upload(client, b"")
    non_pdf_response = client.post(
        "/v1/statements",
        files={"file": ("statement.txt", b"not a PDF", "text/plain")},
        headers=AUTHORIZATION,
    )

    assert empty_response.status_code == 400
    assert empty_response.json()["error"]["code"] == "empty_file"
    assert non_pdf_response.status_code == 400
    assert non_pdf_response.json()["error"]["code"] == "invalid_file_type"


def test_statement_upload_returns_structured_error_for_malformed_multipart(client: TestClient) -> None:
    response = client.post(
        "/v1/statements",
        content=b"--missing-boundary\r\n",
        headers={
            **AUTHORIZATION,
            "content-type": "multipart/form-data; boundary=declared-boundary",
        },
    )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "invalid_request"


def test_statement_upload_rejects_file_larger_than_limit(client: TestClient) -> None:
    response = _upload(client, b"%PDF-" + b"0" * MAX_FILE_SIZE_BYTES)

    assert response.status_code == 413
    assert response.json()["error"]["code"] == "file_too_large"


def test_statement_upload_rejects_pdf_with_too_many_pages(client: TestClient, monkeypatch) -> None:
    class ReaderWithTooManyPages:
        pages = [object()] * 21

    monkeypatch.setattr(api, "PdfReader", lambda _: ReaderWithTooManyPages())

    response = _upload(client, b"%PDF-1.7")

    assert response.status_code == 413
    assert response.json()["error"]["code"] == "too_many_pages"


def test_statement_lifecycle_preserves_normalized_result(client: TestClient) -> None:
    content = FIXTURE_PDF.read_bytes()
    statement = parse_banco_chile_cuenta_vista(content)

    created_response = _upload(client, content)
    duplicate_response = _upload(client, content)

    assert created_response.status_code == 200
    statement_id = created_response.json()["statement_id"]
    assert duplicate_response.json()["statement_id"] == statement_id
    assert created_response.json()["metadata"]["masked_account_number"] == statement.masked_account_number
    assert created_response.json()["metadata"] == {
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
    assert created_response.json()["summary"] == {
        "opening_balance": statement.summary.opening_balance,
        "closing_balance": statement.summary.closing_balance,
        "one_day_retention": statement.summary.one_day_retention,
        "multi_day_retention": statement.summary.multi_day_retention,
        "available_balance": statement.summary.available_balance,
    }
    assert created_response.json()["transactions"] == [
        _transaction_response(transaction) for transaction in statement.transactions
    ]

    listing = client.get("/v1/statements?limit=1&offset=0", headers=AUTHORIZATION)
    fetched = client.get(f"/v1/statements/{statement_id}", headers=AUTHORIZATION)

    assert listing.json()["statements"] == [
        {
            "statement_id": statement_id,
            "bank": statement.bank,
            "product": statement.product,
            "masked_account_number": statement.masked_account_number,
            "currency": statement.currency,
            "period_start": statement.period_start.isoformat(),
            "period_end": statement.period_end.isoformat(),
            "statement_number": statement.statement_number,
            "page_number": statement.page_number,
            "total_pages": statement.total_pages,
            "created_at": ANY,
        }
    ]
    assert "transactions" not in listing.json()["statements"][0]
    assert fetched.json() == created_response.json()
    assert re.search(r"\d{5}", statement.masked_account_number or "") is None

    deleted = client.delete(f"/v1/statements/{statement_id}", headers=AUTHORIZATION)

    assert deleted.status_code == 204
    assert client.get(f"/v1/statements/{statement_id}", headers=AUTHORIZATION).status_code == 404


def test_concurrent_statement_uploads_reuse_the_same_record(client: TestClient) -> None:
    barrier = Barrier(2)
    content = FIXTURE_PDF.read_bytes()

    def upload() -> object:
        barrier.wait()
        return _upload(client, content)

    with ThreadPoolExecutor(max_workers=2) as executor:
        first, second = tuple(executor.map(lambda _: upload(), range(2)))

    assert first.status_code == second.status_code == 200
    assert first.json()["statement_id"] == second.json()["statement_id"]
    listing = client.get("/v1/statements", headers=AUTHORIZATION).json()["statements"]
    assert [item["statement_id"] for item in listing] == [first.json()["statement_id"]]


def test_statement_upload_persists_v2_without_personal_details(client: TestClient) -> None:
    content = V2_FIXTURE_PDF.read_bytes()
    expected = parse_banco_chile_cuenta_vista(content)

    created = _upload(client, content)
    duplicate = _upload(client, content)

    assert created.status_code == duplicate.status_code == 200
    assert created.json()["statement_id"] == duplicate.json()["statement_id"]
    assert created.json()["metadata"]["masked_account_number"] == expected.masked_account_number
    assert created.json()["transactions"] == [
        _transaction_response(transaction) for transaction in expected.transactions
    ]
    response_text = created.text
    assert "Juan Alfonso Perez Lopez" not in response_text
    assert "juanperez@gmail.com" not in response_text
    assert "123456789" not in response_text


def test_statement_list_rejects_invalid_pagination(client: TestClient) -> None:
    assert client.get("/v1/statements", headers=AUTHORIZATION).json()["limit"] == 50
    assert client.get("/v1/statements?limit=100", headers=AUTHORIZATION).json()["limit"] == 100
    assert client.get("/v1/statements?limit=0", headers=AUTHORIZATION).status_code == 400
    assert client.get("/v1/statements?limit=101", headers=AUTHORIZATION).status_code == 400
    assert client.get("/v1/statements?offset=-1", headers=AUTHORIZATION).status_code == 400
    assert client.get("/v1/statements?offset=invalid", headers=AUTHORIZATION).status_code == 400


def test_analysis_requires_authentication_and_returns_safe_aggregates(client: TestClient) -> None:
    content = FIXTURE_PDF.read_bytes()
    created = _upload(client, content).json()

    unauthorized = client.get("/v1/analysis")
    response = client.get(
        "/v1/analysis",
        params=[
            ("statement_id", created["statement_id"]),
            ("from", created["metadata"]["period_start"]),
            ("to", created["metadata"]["period_end"]),
        ],
        headers=AUTHORIZATION,
    )

    assert unauthorized.status_code == 401
    assert response.status_code == 200
    payload = response.json()
    assert set(payload) == {
        "scope",
        "coverage",
        "summary",
        "monthly",
        "top_merchants",
        "recurrence_candidates",
    }
    assert payload["scope"]["currency"] == "CLP"
    assert "private description" not in response.text


def test_analysis_rejects_invalid_parameters_and_missing_statements(client: TestClient) -> None:
    invalid = client.get("/v1/analysis", headers=AUTHORIZATION)
    missing = client.get(
        "/v1/analysis?statement_id=missing&from=2026-01-01&to=2026-01-31",
        headers=AUTHORIZATION,
    )

    assert invalid.status_code == 400
    assert invalid.json()["error"]["code"] == "invalid_analysis_query"
    assert missing.status_code == 404
    assert missing.json()["error"]["code"] == "statement_not_found"


def test_analysis_reflects_statement_deletion_immediately(client: TestClient) -> None:
    created = _upload(client, FIXTURE_PDF.read_bytes()).json()
    statement_id = created["statement_id"]
    client.delete(f"/v1/statements/{statement_id}", headers=AUTHORIZATION)

    response = client.get(
        "/v1/analysis",
        params=[
            ("statement_id", statement_id),
            ("from", created["metadata"]["period_start"]),
            ("to", created["metadata"]["period_end"]),
        ],
        headers=AUTHORIZATION,
    )

    assert response.status_code == 404


def test_analysis_does_not_modify_sqlite(tmp_path: Path) -> None:
    database_path = tmp_path / "statements.sqlite3"
    client = TestClient(create_app(ServiceSettings(database_path, API_KEY)))
    created = _upload(client, FIXTURE_PDF.read_bytes()).json()
    with sqlite3.connect(database_path) as connection:
        before = (
            connection.execute("PRAGMA user_version").fetchone(),
            connection.execute("SELECT COUNT(*) FROM statements").fetchone(),
            connection.execute("SELECT COUNT(*) FROM transactions").fetchone(),
            connection.execute("SELECT COUNT(*) FROM transaction_classifications").fetchone(),
        )

    response = client.get(
        "/v1/analysis",
        params=[
            ("statement_id", created["statement_id"]),
            ("from", created["metadata"]["period_start"]),
            ("to", created["metadata"]["period_end"]),
        ],
        headers=AUTHORIZATION,
    )

    with sqlite3.connect(database_path) as connection:
        after = (
            connection.execute("PRAGMA user_version").fetchone(),
            connection.execute("SELECT COUNT(*) FROM statements").fetchone(),
            connection.execute("SELECT COUNT(*) FROM transactions").fetchone(),
            connection.execute("SELECT COUNT(*) FROM transaction_classifications").fetchone(),
        )
    assert response.status_code == 200
    assert after == before


def test_statement_upload_rejects_invalid_pdf_without_parser_details(client: TestClient) -> None:
    response = _upload(client, b"%PDF-1.7")

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "invalid_pdf"


def test_statement_upload_maps_rejected_statement_to_safe_error(client: TestClient, monkeypatch) -> None:
    class ReaderWithOnePage:
        pages = [object()]

    monkeypatch.setattr(api, "PdfReader", lambda _: ReaderWithOnePage())
    monkeypatch.setattr(
        api,
        "parse_banco_chile_cuenta_vista",
        lambda _: (_ for _ in ()).throw(UnsupportedStatementError("Sensitive parser detail")),
    )

    response = _upload(client, b"%PDF-1.7")

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "statement_rejected"


def test_statement_upload_hides_unexpected_errors(client: TestClient, monkeypatch) -> None:
    class ReaderWithOnePage:
        pages = [object()]

    monkeypatch.setattr(api, "PdfReader", lambda _: ReaderWithOnePage())
    monkeypatch.setattr(
        api,
        "parse_banco_chile_cuenta_vista",
        lambda _: (_ for _ in ()).throw(RuntimeError("Sensitive stack detail")),
    )

    response = _upload(client, b"%PDF-1.7")

    assert response.status_code == 500
    assert response.json()["error"]["code"] == "internal_error"


def test_statement_upload_hides_database_lock_details(client: TestClient, monkeypatch) -> None:
    def busy(*_: object) -> object:
        raise DatabaseBusyError("database is locked for account 123456789")

    monkeypatch.setattr(api.StatementRepository, "save_or_get", busy)

    response = _upload(client, FIXTURE_PDF.read_bytes())

    assert response.status_code == 503
    assert response.json() == {
        "error": {
            "code": "database_busy",
            "message": "The data service is temporarily unavailable",
        }
    }
