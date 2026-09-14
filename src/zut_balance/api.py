from io import BytesIO

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from pypdf import PdfReader
from pypdf.errors import PdfReadError
from python_multipart.exceptions import MultipartParseError
from starlette.datastructures import UploadFile
from starlette.exceptions import HTTPException as StarletteHTTPException

from .banco_chile_cuenta_vista import parse_banco_chile_cuenta_vista
from .errors import StatementError
from .models import Statement


app = FastAPI(title="Zut Balance Processing Service", version="1.0.0")
MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024
MAX_PAGE_COUNT = 20


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


def _error_response(status_code: int, code: str, message: str) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={"error": {"code": code, "message": message}},
    )


@app.exception_handler(StarletteHTTPException)
async def handle_http_exception(_: Request, error: StarletteHTTPException) -> JSONResponse:
    return _error_response(error.status_code, "invalid_request", "The request could not be processed")


def _statement_response(statement: Statement) -> JSONResponse:
    return JSONResponse(
        status_code=200,
        content={
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
                }
                for transaction in statement.transactions
            ],
        },
    )


@app.post("/v1/statements")
async def process_statement_upload(request: Request) -> JSONResponse:
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

    try:
        statement = parse_banco_chile_cuenta_vista(content)
        return _statement_response(statement)
    except StatementError:
        return _error_response(400, "statement_rejected", "The statement could not be processed")
    except Exception:
        return _error_response(500, "internal_error", "The statement could not be processed")
