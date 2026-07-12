import logging
import re
import unicodedata
from pathlib import Path

from app.schemas.document import DocumentProcessingResponse, TextChunkResponse
from app.services.parser import ParsedPage, extract_pdf_text
from app.utils.text_splitter import TextChunk, split_text

logger = logging.getLogger("uvicorn.error")


def _document_slug(filename: str) -> str:
    stem = Path(filename).stem
    ascii_name = unicodedata.normalize("NFKD", stem).encode("ascii", "ignore").decode()
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", ascii_name).strip("-").lower()
    return slug or "documento"


def _resolve_page_range(chunk: TextChunk, pages: tuple[ParsedPage, ...]) -> tuple[int | None, int | None]:
    chunk_start = chunk.start
    chunk_end = max(chunk.end - 1, chunk.start)
    page_start: int | None = None
    page_end: int | None = None

    for page in pages:
        if page.end_character <= chunk_start:
            continue
        if page.start_character > chunk_end:
            break
        page_start = page_start or page.page_number
        page_end = page.page_number

    return page_start, page_end


def process_document(
    pdf_bytes: bytes,
    filename: str,
    chunk_size: int = 500,
    chunk_overlap: int = 50,
) -> DocumentProcessingResponse:
    parsed = extract_pdf_text(pdf_bytes, document_name=filename)
    chunks = split_text(
        parsed.text,
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
    )
    slug = _document_slug(filename)

    response_chunks: list[TextChunkResponse] = []
    for chunk in chunks:
        page_start, page_end = _resolve_page_range(chunk, parsed.pages)
        response_chunks.append(
            TextChunkResponse(
                id=f"{slug}-{chunk.index + 1:04d}",
                index=chunk.index,
                content=chunk.content,
                character_count=len(chunk.content),
                start_character=chunk.start,
                end_character=chunk.end,
                page_start=page_start,
                page_end=page_end,
                section_title=chunk.section_title,
            )
        )

    logger.info(
        "Documento procesado en memoria: documento=%s chunks=%s chunk_size=%s overlap=%s",
        filename,
        len(response_chunks),
        chunk_size,
        chunk_overlap,
    )
    for chunk in response_chunks:
        logger.info(
            "Chunk registrado: id=%s índice=%s páginas=%s-%s caracteres=%s rango=%s-%s sección=%s",
            chunk.id,
            chunk.index,
            chunk.page_start,
            chunk.page_end,
            chunk.character_count,
            chunk.start_character,
            chunk.end_character,
            chunk.section_title or "N/A",
        )

    return DocumentProcessingResponse(
        document=filename,
        pages=parsed.page_count,
        extracted_characters=parsed.character_count,
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        total_chunks=len(response_chunks),
        chunks=response_chunks,
    )
