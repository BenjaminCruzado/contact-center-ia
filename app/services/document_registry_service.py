from __future__ import annotations

from datetime import UTC, datetime

from app.config.settings import Settings, settings
from app.db.audit_db import AuditDatabase
from app.schemas.document import (
    DocumentCatalogItem,
    DocumentDeleteResponse,
    DocumentProcessingResponse,
)


class DocumentRegistryService:
    def __init__(
        self,
        database: AuditDatabase | None = None,
        app_settings: Settings = settings,
    ) -> None:
        self.settings = app_settings
        self.database = database or AuditDatabase(app_settings)

    def initialize(self) -> None:
        self.database.initialize()

    def register(self, document: DocumentProcessingResponse) -> DocumentCatalogItem:
        payload = {
            "created_at": datetime.now(UTC).isoformat(),
            "document_name": document.document,
            "slug": self._slug_from_document(document),
            "collection": document.collection or self.settings.chroma_collection_prefix,
            "pages": document.pages,
            "total_chunks": document.total_chunks,
            "indexed_chunks": document.indexed_chunks,
            "embedding_provider": document.embedding_provider,
            "embedding_model": document.embedding_model,
        }
        document_id = self.database.upsert_document(payload)
        return DocumentCatalogItem(id=document_id, **payload)

    def list_documents(self) -> list[DocumentCatalogItem]:
        return [DocumentCatalogItem.model_validate(item) for item in self.database.list_documents()]

    def get_document(self, document_id: int) -> DocumentCatalogItem | None:
        item = self.database.get_document(document_id)
        return DocumentCatalogItem.model_validate(item) if item else None

    def delete_document(self, document_id: int) -> DocumentDeleteResponse | None:
        item = self.database.delete_document(document_id)
        if item is None:
            return None
        return DocumentDeleteResponse(
            id=int(item["id"]),
            document_name=str(item["document_name"]),
            collection=str(item["collection"]),
            deleted=True,
        )

    @staticmethod
    def _slug_from_document(document: DocumentProcessingResponse) -> str:
        if not document.chunks:
            return document.document
        first_id = document.chunks[0].id
        return first_id.rsplit("-", 1)[0] if "-" in first_id else first_id
