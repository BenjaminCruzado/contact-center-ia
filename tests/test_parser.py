from io import BytesIO

import pytest
from pypdf import PdfWriter

from app.services.parser import EmptyDocumentError, InvalidPdfError, extract_pdf_text
from tests.pdf_factory import create_text_pdf


def test_extract_pdf_text_normalizes_content() -> None:
    pdf_bytes = create_text_pdf("Contact Center con texto extraible para pruebas.")

    result = extract_pdf_text(pdf_bytes, "prueba.pdf")

    assert result.page_count == 1
    assert result.pages_with_text == 1
    assert "Contact Center" in result.text
    assert result.character_count == len(result.text)


def test_rejects_invalid_pdf() -> None:
    with pytest.raises(InvalidPdfError):
        extract_pdf_text(b"contenido que no es PDF")


def test_rejects_pdf_without_extractable_text() -> None:
    writer = PdfWriter()
    writer.add_blank_page(width=612, height=792)
    output = BytesIO()
    writer.write(output)

    with pytest.raises(EmptyDocumentError):
        extract_pdf_text(output.getvalue())
