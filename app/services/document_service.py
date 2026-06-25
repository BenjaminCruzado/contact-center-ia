import logging
import re
import unicodedata
from pathlib import Path

from app.schemas.document import DocumentProcessingResponse, TextChunkResponse
from app.services.parser import extract_pdf_text
from app.utils.text_splitter import split_text

logger = logging.getLogger("uvicorn.error")


def _document_slug(filename: str) -> str:
    stem = Path(filename).stem
    ascii_name = unicodedata.normalize("NFKD", stem).encode("ascii", "ignore").decode()
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", ascii_name).strip("-").lower()
    return slug or "documento"


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

    response_chunks = [
        TextChunkResponse(
            id=f"{slug}-{chunk.index + 1:04d}",
            index=chunk.index,
            content=chunk.content,
            character_count=len(chunk.content),
            start_character=chunk.start,
            end_character=chunk.end,
        )
        for chunk in chunks
    ]

    logger.info(
        "Documento procesado en memoria: documento=%s chunks=%s chunk_size=%s overlap=%s",
        filename,
        len(response_chunks),
        chunk_size,
        chunk_overlap,
    )
    for chunk in response_chunks:
        logger.info(
            "Chunk registrado: id=%s índice=%s caracteres=%s rango=%s-%s",
            chunk.id,
            chunk.index,
            chunk.character_count,
            chunk.start_character,
            chunk.end_character,
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
