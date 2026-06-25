from fastapi import APIRouter, File, HTTPException, Query, UploadFile, status

from app.schemas.document import DocumentProcessingResponse
from app.services.document_service import process_document
from app.services.parser import (
    EmptyDocumentError,
    InvalidPdfError,
    PdfExtractionError,
)

router = APIRouter(prefix="/documentos", tags=["Documentos"])

PDF_CONTENT_TYPES = {"application/pdf", "application/x-pdf"}
MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024


@router.post(
    "/subir",
    response_model=DocumentProcessingResponse,
    status_code=status.HTTP_200_OK,
)
async def upload_document(
    file: UploadFile = File(..., description="Documento PDF que se procesará en memoria."),
    chunk_size: int = Query(default=500, ge=1, le=10_000),
    chunk_overlap: int = Query(default=50, ge=0, le=9_999),
) -> DocumentProcessingResponse:
    filename = file.filename or "documento.pdf"
    content_type = (file.content_type or "").lower()

    if not filename.lower().endswith(".pdf") or content_type not in PDF_CONTENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="El archivo debe tener extensión .pdf y tipo de contenido application/pdf.",
        )

    if chunk_overlap >= chunk_size:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="chunk_overlap debe ser menor que chunk_size.",
        )

    pdf_bytes = await file.read(MAX_FILE_SIZE_BYTES + 1)
    await file.close()

    if not pdf_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El archivo PDF está vacío.",
        )

    if len(pdf_bytes) > MAX_FILE_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="El archivo PDF supera el límite de 10 MB.",
        )

    try:
        return process_document(
            pdf_bytes=pdf_bytes,
            filename=filename,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
        )
    except (InvalidPdfError, EmptyDocumentError) as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except PdfExtractionError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

