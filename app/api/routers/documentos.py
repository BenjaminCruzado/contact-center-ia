from functools import lru_cache

from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    Query,
    UploadFile,
    status,
)

from app.api.deps import get_current_user, require_admin
from app.config.settings import settings
from app.schemas.document import (
    DocumentCatalogItem,
    DocumentDeleteResponse,
    DocumentProcessingResponse,
)
from app.schemas.search import (
    SemanticSearchRequest,
    SemanticSearchResponse,
    VectorStoreStatusResponse,
)
from app.services.document_service import process_document
from app.services.document_registry_service import DocumentRegistryService
from app.services.embedding_service import (
    EmbeddingConfigurationError,
    EmbeddingProviderError,
)
from app.services.parser import (
    EmptyDocumentError,
    InvalidPdfError,
    PdfExtractionError,
)
from app.services.rag_service import RagService
from app.services.vector_store_service import (
    EmptyVectorStoreError,
    VectorStoreUnavailableError,
)

router = APIRouter(prefix="/documentos", tags=["Documentos"])

PDF_CONTENT_TYPES = {"application/pdf", "application/x-pdf"}
MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024


@lru_cache(maxsize=1)
def get_rag_service() -> RagService:
    return RagService()


@lru_cache(maxsize=1)
def get_document_registry_service() -> DocumentRegistryService:
    return DocumentRegistryService()


@router.post(
    "/subir",
    response_model=DocumentProcessingResponse,
    status_code=status.HTTP_200_OK,
)
async def upload_document(
    file: UploadFile = File(..., description="Documento PDF que se procesará en memoria."),
    chunk_size: int = Query(default=settings.rag_default_chunk_size, ge=1, le=10_000),
    chunk_overlap: int = Query(default=settings.rag_default_chunk_overlap, ge=0, le=9_999),
    _: object = Depends(require_admin),
    rag_service: RagService = Depends(get_rag_service),
    registry_service: DocumentRegistryService = Depends(get_document_registry_service),
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
        document = process_document(
            pdf_bytes=pdf_bytes,
            filename=filename,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
        )
        indexed_document = rag_service.index_document(document)
        registry_service.register(indexed_document)
        return indexed_document
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
    except EmbeddingConfigurationError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    except EmbeddingProviderError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc
    except VectorStoreUnavailableError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc


@router.post(
    "/buscar",
    response_model=SemanticSearchResponse,
    status_code=status.HTTP_200_OK,
)
async def search_documents(
    request: SemanticSearchRequest,
    _: object = Depends(get_current_user),
    rag_service: RagService = Depends(get_rag_service),
) -> SemanticSearchResponse:
    try:
        return rag_service.search(request.query, request.top_k)
    except EmptyVectorStoreError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except EmbeddingConfigurationError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    except EmbeddingProviderError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc
    except VectorStoreUnavailableError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc


@router.get(
    "/vector-store/status",
    response_model=VectorStoreStatusResponse,
    status_code=status.HTTP_200_OK,
)
async def vector_store_status(
    _: object = Depends(require_admin),
    rag_service: RagService = Depends(get_rag_service),
) -> VectorStoreStatusResponse:
    try:
        return rag_service.status()
    except VectorStoreUnavailableError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc


@router.get(
    "",
    response_model=list[DocumentCatalogItem],
    status_code=status.HTTP_200_OK,
)
async def list_documents(
    _: object = Depends(require_admin),
    registry_service: DocumentRegistryService = Depends(get_document_registry_service),
) -> list[DocumentCatalogItem]:
    return registry_service.list_documents()


@router.delete(
    "/{document_id}",
    response_model=DocumentDeleteResponse,
    status_code=status.HTTP_200_OK,
)
async def delete_document(
    document_id: int,
    _: object = Depends(require_admin),
    rag_service: RagService = Depends(get_rag_service),
    registry_service: DocumentRegistryService = Depends(get_document_registry_service),
) -> DocumentDeleteResponse:
    document = registry_service.get_document(document_id)
    if document is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No se encontró el documento solicitado.",
        )

    try:
        rag_service.vector_store.delete_by_document(document.document_name)
    except VectorStoreUnavailableError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc

    deleted = registry_service.delete_document(document_id)
    if deleted is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No se encontró el documento solicitado.",
        )
    return deleted
