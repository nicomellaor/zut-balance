from io import BytesIO
from pathlib import Path

import pytest
from pypdf import PdfWriter

from zut_balance import EncryptedPdfError, InvalidPdfError, TextExtractionError
from zut_balance.pdf_validation import extract_pdf_text


SAMPLE_PDF = Path(__file__).parents[1] / "media" / "cartola_ejemplo_banco_chile.pdf"


def test_extract_pdf_text_returns_text_from_supported_sample() -> None:
    pages = extract_pdf_text(SAMPLE_PDF.read_bytes())

    assert len(pages) == 1
    assert "Banco de Chile" in pages[0]
    assert "CUENTA VISTA" in pages[0]


def test_extract_pdf_text_rejects_invalid_content() -> None:
    with pytest.raises(InvalidPdfError, match="readable PDF"):
        extract_pdf_text(b"not a PDF")


def test_extract_pdf_text_rejects_encrypted_pdf() -> None:
    writer = PdfWriter()
    writer.add_blank_page(width=100, height=100)
    writer.encrypt("secret")
    content = BytesIO()
    writer.write(content)

    with pytest.raises(EncryptedPdfError, match="Password-protected"):
        extract_pdf_text(content.getvalue())


def test_extract_pdf_text_rejects_pdf_without_text() -> None:
    writer = PdfWriter()
    writer.add_blank_page(width=100, height=100)
    content = BytesIO()
    writer.write(content)

    with pytest.raises(TextExtractionError, match="extractable text"):
        extract_pdf_text(content.getvalue())
