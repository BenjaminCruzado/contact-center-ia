import logging
import re
import unicodedata
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from typing import BinaryIO

from pypdf import PdfReader
from pypdf.errors import PdfReadError

logger = logging.getLogger("uvicorn.error")


class PdfExtractionError(ValueError):
    """Error base del proceso de extracción de PDF."""


class InvalidPdfError(PdfExtractionError):
    """El contenido recibido no corresponde a un PDF legible."""


class EmptyDocumentError(PdfExtractionError):
    """El PDF no contiene texto extraíble."""


@dataclass(frozen=True)
class ParsedDocument:
    text: str
    page_count: int
    pages_with_text: int
    character_count: int


PdfSource = bytes | bytearray | str | Path | BinaryIO


def _normalize_text(text: str) -> str:
    normalized = unicodedata.normalize("NFKC", text)
    normalized = normalized.replace("\x00", "").replace("\ufffd", "")
    normalized = re.sub(r"-\s*\n\s*(?=\w)", "", normalized)
    normalized = re.sub(r"[^\S\r\n]+", " ", normalized)
    normalized = re.sub(r"\r\n?", "\n", normalized)
    normalized = re.sub(r"\n[ \t]+", "\n", normalized)
    normalized = re.sub(r"\n{3,}", "\n\n", normalized)
    return normalized.strip()


def _prepare_source(source: PdfSource) -> str | Path | BinaryIO:
    if isinstance(source, (bytes, bytearray)):
        if not source:
            raise InvalidPdfError("El archivo PDF está vacío.")
        return BytesIO(source)
    return source


def extract_pdf_text(source: PdfSource, document_name: str = "documento.pdf") -> ParsedDocument:
    """Extrae y normaliza el texto de un PDF recibido como bytes, ruta o stream."""
    logger.info("Iniciando extracción PDF: %s", document_name)

    try:
        reader = PdfReader(_prepare_source(source), strict=False)
    except (PdfReadError, OSError, TypeError, ValueError) as exc:
        raise InvalidPdfError("El archivo no es un PDF válido o está corrupto.") from exc

    if reader.is_encrypted:
        try:
            unlocked = reader.decrypt("")
        except Exception as exc:  # pypdf puede propagar excepciones criptográficas.
            raise PdfExtractionError("El PDF está cifrado y no puede procesarse.") from exc
        if not unlocked:
            raise PdfExtractionError("El PDF está cifrado y requiere contraseña.")

    page_texts: list[str] = []
    pages_with_text = 0
    page_count = len(reader.pages)

    for page_number, page in enumerate(reader.pages, start=1):
        try:
            raw_text = page.extract_text() or ""
        except Exception as exc:
            logger.warning(
                "No fue posible extraer la página %s de %s: %s",
                page_number,
                document_name,
                exc,
            )
            continue

        clean_text = _normalize_text(raw_text)
        if clean_text:
            pages_with_text += 1
            page_texts.append(clean_text)
            logger.info(
                "Página %s/%s extraída: %s caracteres",
                page_number,
                page_count,
                len(clean_text),
            )
        else:
            logger.warning(
                "Página %s/%s sin texto extraíble",
                page_number,
                page_count,
            )

    complete_text = "\n\n".join(page_texts).strip()
    if not complete_text:
        raise EmptyDocumentError(
            "El PDF no contiene texto extraíble. Puede ser un documento escaneado que requiera OCR."
        )

    logger.info(
        "Extracción completada: documento=%s páginas=%s páginas_con_texto=%s caracteres=%s",
        document_name,
        page_count,
        pages_with_text,
        len(complete_text),
    )

    return ParsedDocument(
        text=complete_text,
        page_count=page_count,
        pages_with_text=pages_with_text,
        character_count=len(complete_text),
    )
