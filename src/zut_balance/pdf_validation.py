"""Validation and text extraction for digital PDF statements."""

from io import BytesIO

from pypdf import PdfReader
from pypdf.errors import PdfReadError

from .errors import EncryptedPdfError, InvalidPdfError, TextExtractionError


def extract_pdf_text(pdf_content: bytes) -> tuple[str, ...]:
    """Return page text after validating a readable, digital PDF."""
    try:
        reader = PdfReader(BytesIO(pdf_content))
    except (OSError, PdfReadError, ValueError) as error:
        raise InvalidPdfError("The input is not a readable PDF") from error

    if reader.is_encrypted:
        raise EncryptedPdfError("Password-protected PDFs are not supported")

    try:
        pages = tuple(
            page.extract_text(extraction_mode="layout") or ""
            if "/Contents" in page
            else ""
            for page in reader.pages
        )
    except (OSError, PdfReadError, ValueError) as error:
        raise InvalidPdfError("The PDF could not be read") from error

    if not any(page.strip() for page in pages):
        raise TextExtractionError("The PDF does not contain extractable text")

    return pages
