from dataclasses import dataclass
from datetime import UTC, date, datetime
from hashlib import sha256
from io import BytesIO
import os
from pathlib import Path
import secrets

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, Response
from pypdf import PdfReader
from pypdf.errors import PdfReadError
from python_multipart.exceptions import MultipartParseError
from starlette.datastructures import UploadFile
from starlette.exceptions import HTTPException as StarletteHTTPException

from .analysis import AnalysisScopeError, AnalysisStatement, AnalysisValidationError, analyze_statements
from .banco_chile_cuenta_vista import parse_banco_chile_cuenta_vista
from .errors import StatementError
from .models import Statement
from .persistence import DatabaseBusyError, StatementRepository, StoredStatementMetadata


MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024
MAX_PAGE_COUNT = 20
DEFAULT_LIST_LIMIT = 50
MAX_LIST_LIMIT = 100


@dataclass(frozen=True, slots=True)
class ServiceSettings:
    database_path: Path | None
    api_key: str | None


def _environment_settings() -> ServiceSettings:
    database_path = os.environ.get("ZUT_BALANCE_DATABASE_PATH")
    return ServiceSettings(
        database_path=Path(database_path) if database_path else None,
        api_key=os.environ.get("ZUT_BALANCE_API_KEY"),
    )


def _error_response(status_code: int, code: str, message: str) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={"error": {"code": code, "message": message}},
    )


def _statement_response(statement: Statement, statement_id: str) -> JSONResponse:
    return JSONResponse(
        status_code=200,
        content={
            "statement_id": statement_id,
            "metadata": {
                "bank": statement.bank,
                "product": statement.product,
                "masked_account_number": statement.masked_account_number,
                "currency": statement.currency,
                "period_start": statement.period_start.isoformat(),
                "period_end": statement.period_end.isoformat(),
                "statement_number": statement.statement_number,
                "page_number": statement.page_number,
                "total_pages": statement.total_pages,
            },
            "summary": {
                "opening_balance": statement.summary.opening_balance,
                "closing_balance": statement.summary.closing_balance,
                "one_day_retention": statement.summary.one_day_retention,
                "multi_day_retention": statement.summary.multi_day_retention,
                "available_balance": statement.summary.available_balance,
            },
            "transactions": [
                {
                    "date": transaction.date.isoformat(),
                    "description": transaction.description,
                    "document_number": transaction.document_number,
                    "branch_or_channel": transaction.branch_or_channel,
                    "amount": transaction.amount,
                    "movement_type": transaction.movement_type.value,
                    "reported_balance": transaction.reported_balance,
                    "classification": (
                        {
                            "category": transaction.classification.category.value,
                            "merchant_name": transaction.classification.merchant_name,
                            "rule_id": transaction.classification.rule_id,
                            "ruleset_version": transaction.classification.ruleset_version,
                        }
                        if transaction.classification is not None
                        else None
                    ),
                }
                for transaction in statement.transactions
            ],
        },
    )


def _metadata_response(metadata: StoredStatementMetadata) -> dict[str, object]:
    return {
        "statement_id": metadata.id,
        "bank": metadata.bank,
        "product": metadata.product,
        "masked_account_number": metadata.masked_account_number,
        "currency": metadata.currency,
        "period_start": metadata.period_start.isoformat(),
        "period_end": metadata.period_end.isoformat(),
        "statement_number": metadata.statement_number,
        "page_number": metadata.page_number,
        "total_pages": metadata.total_pages,
        "created_at": metadata.created_at,
    }


def _analysis_response(result) -> JSONResponse:
    return JSONResponse(
        status_code=200,
        content={
            "scope": {
                "statement_ids": list(result.scope.statement_ids),
                "from": result.scope.from_date.isoformat(),
                "to": result.scope.to_date.isoformat(),
                "currency": result.scope.currency,
                "ruleset_versions": list(result.scope.ruleset_versions),
            },
            "coverage": {
                "covered_ranges": [
                    {"from": start.isoformat(), "to": end.isoformat()}
                    for start, end in result.coverage.covered_ranges
                ],
                "gaps": [
                    {"from": start.isoformat(), "to": end.isoformat()}
                    for start, end in result.coverage.gaps
                ],
                "partial_months": list(result.coverage.partial_months),
            },
            "summary": {
                "spending_amount": result.spending.amount,
                "transaction_count": result.spending.count,
                "credits_amount": result.credits.amount,
                "credits_count": result.credits.count,
                "excluded_debits_amount": result.excluded_debits.amount,
                "excluded_debits_count": result.excluded_debits.count,
                "uncategorized_amount": result.uncategorized.amount,
                "uncategorized_count": result.uncategorized.count,
                "merchant_coverage": {
                    "identified_amount": result.merchant_coverage[0].amount,
                    "identified_count": result.merchant_coverage[0].count,
                    "unidentified_amount": result.merchant_coverage[1].amount,
                    "unidentified_count": result.merchant_coverage[1].count,
                },
                "by_category": [
                    {"category": item.category.value, "amount": item.amount, "count": item.count}
                    for item in result.categories
                ],
            },
            "monthly": [
                {
                    "month": month.month,
                    "amount": month.amount,
                    "count": month.count,
                    "by_category": [
                        {"category": item.category.value, "amount": item.amount, "count": item.count}
                        for item in month.categories
                    ],
                    "absolute_change": month.absolute_change,
                    "percentage_change": month.percentage_change,
                }
                for month in result.monthly
            ],
            "top_merchants": [
                {"merchant_name": item.merchant_name, "amount": item.amount, "count": item.count}
                for item in result.top_merchants
            ],
            "recurrence_candidates": [
                {
                    "merchant_name": item.merchant_name,
                    "cadence": item.cadence.value,
                    "dates": [value.isoformat() for value in item.dates],
                    "amounts": list(item.amounts),
                    "count": item.count,
                    "minimum_amount": item.minimum_amount,
                    "average_amount": item.average_amount,
                    "maximum_amount": item.maximum_amount,
                }
                for item in result.recurrence_candidates
            ],
        },
    )


def create_app(settings: ServiceSettings | None = None) -> FastAPI:
    settings = settings or _environment_settings()
    repository = (
        StatementRepository(settings.database_path) if settings.database_path is not None else None
    )
    if repository is not None:
        repository.initialize()

    app = FastAPI(title="Zut Balance Processing Service", version="1.0.0")

    @app.exception_handler(StarletteHTTPException)
    async def handle_http_exception(_: Request, error: StarletteHTTPException) -> JSONResponse:
        return _error_response(error.status_code, "invalid_request", "The request could not be processed")

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    def require_data_access(request: Request) -> JSONResponse | None:
        if repository is None or not settings.api_key:
            return _error_response(
                500,
                "service_not_configured",
                "The data service is not configured",
            )
        authorization = request.headers.get("Authorization")
        if authorization is None or not authorization.startswith("Bearer "):
            return _error_response(401, "unauthorized", "Authentication is required")
        provided_key = authorization.removeprefix("Bearer ")
        if not provided_key or not secrets.compare_digest(provided_key, settings.api_key):
            return _error_response(401, "unauthorized", "Authentication is required")
        return None

    @app.post("/v1/statements")
    async def process_statement_upload(request: Request) -> JSONResponse:
        access_error = require_data_access(request)
        if access_error is not None:
            return access_error
        assert repository is not None
        try:
            form = await request.form()
        except MultipartParseError:
            return _error_response(400, "invalid_request", "The request could not be processed")
        items = list(form.multi_items())
        files = [(name, value) for name, value in items if isinstance(value, UploadFile)]
        if len(items) != 1 or len(files) != 1 or files[0][0] != "file":
            return _error_response(400, "invalid_upload", "Provide exactly one PDF file named file")

        upload = files[0][1]
        if upload.content_type != "application/pdf":
            return _error_response(400, "invalid_file_type", "The uploaded file must be a PDF")

        content = await upload.read()
        if not content:
            return _error_response(400, "empty_file", "The uploaded file is empty")
        if not content.startswith(b"%PDF-"):
            return _error_response(400, "invalid_pdf", "The uploaded file is not a valid PDF")
        if len(content) > MAX_FILE_SIZE_BYTES:
            return _error_response(413, "file_too_large", "The uploaded file exceeds the 10 MiB limit")
        try:
            page_count = len(PdfReader(BytesIO(content)).pages)
        except PdfReadError:
            return _error_response(400, "invalid_pdf", "The uploaded file is not a valid PDF")
        if page_count > MAX_PAGE_COUNT:
            return _error_response(413, "too_many_pages", "The uploaded PDF exceeds the 20 page limit")

        source_sha256 = sha256(content).hexdigest()
        try:
            statement = parse_banco_chile_cuenta_vista(content)
            stored, _ = repository.save_or_get(
                statement,
                source_sha256,
                datetime.now(UTC).isoformat(),
            )
            return _statement_response(stored.statement, stored.id)
        except StatementError:
            return _error_response(400, "statement_rejected", "The statement could not be processed")
        except DatabaseBusyError:
            return _error_response(
                503,
                "database_busy",
                "The data service is temporarily unavailable",
            )
        except Exception:
            return _error_response(500, "internal_error", "The statement could not be processed")

    @app.get("/v1/statements/{statement_id}")
    def get_statement(statement_id: str, request: Request) -> JSONResponse:
        access_error = require_data_access(request)
        if access_error is not None:
            return access_error
        assert repository is not None
        stored = repository.get(statement_id)
        if stored is None:
            return _error_response(404, "statement_not_found", "The statement was not found")
        return _statement_response(stored.statement, stored.id)

    @app.get("/v1/statements")
    def list_statements(request: Request) -> JSONResponse:
        access_error = require_data_access(request)
        if access_error is not None:
            return access_error
        assert repository is not None
        try:
            limit = int(request.query_params.get("limit", DEFAULT_LIST_LIMIT))
            offset = int(request.query_params.get("offset", 0))
        except ValueError:
            return _error_response(400, "invalid_pagination", "Pagination values must be integers")
        if not 1 <= limit <= MAX_LIST_LIMIT or offset < 0:
            return _error_response(400, "invalid_pagination", "Pagination values are out of range")
        return JSONResponse(
            status_code=200,
            content={
                "limit": limit,
                "offset": offset,
                "statements": [
                    _metadata_response(metadata)
                    for metadata in repository.list_metadata(limit, offset)
                ],
            },
        )

    @app.get("/v1/analysis")
    def get_analysis(request: Request) -> JSONResponse:
        access_error = require_data_access(request)
        if access_error is not None:
            return access_error
        assert repository is not None
        statement_ids = tuple(request.query_params.getlist("statement_id"))
        if not statement_ids or len(statement_ids) > 100 or len(set(statement_ids)) != len(statement_ids):
            return _error_response(400, "invalid_analysis_query", "Analysis parameters are invalid")
        try:
            from_date = date.fromisoformat(request.query_params["from"])
            to_date = date.fromisoformat(request.query_params["to"])
        except (KeyError, ValueError):
            return _error_response(400, "invalid_analysis_query", "Analysis parameters are invalid")
        stored = repository.get_many(statement_ids)
        if len(stored) != len(statement_ids):
            return _error_response(404, "statement_not_found", "A requested statement was not found")
        try:
            result = analyze_statements(
                tuple(AnalysisStatement(item.id, item.statement) for item in stored), from_date, to_date
            )
        except AnalysisValidationError:
            return _error_response(400, "invalid_analysis_query", "Analysis parameters are invalid")
        except AnalysisScopeError:
            return _error_response(409, "invalid_analysis_scope", "The selected statements cannot be analyzed together")
        return _analysis_response(result)

    @app.delete(
        "/v1/statements/{statement_id}",
        status_code=204,
        response_class=Response,
        response_model=None,
    )
    def delete_statement(statement_id: str, request: Request) -> Response | JSONResponse:
        access_error = require_data_access(request)
        if access_error is not None:
            return access_error
        assert repository is not None
        if not repository.delete(statement_id):
            return _error_response(404, "statement_not_found", "The statement was not found")
        return Response(status_code=204)

    return app


app = create_app()
