import logging

from app.config.settings import Settings, settings
from app.schemas.document import DocumentProcessingResponse
from app.schemas.search import (
    SemanticSearchResponse,
    SemanticSearchResult,
    VectorStoreStatusResponse,
)
from app.services.embedding_service import EmbeddingService, get_embedding_service
from app.services.vector_store_service import (
    VectorStoreService,
    build_collection_name,
)

logger = logging.getLogger("uvicorn.error")


def distance_to_similarity(distance: float) -> float:
    return max(0.0, min(1.0, 1.0 - float(distance)))


class RagService:
    def __init__(
        self,
        embedding_service: EmbeddingService | None = None,
        vector_store: VectorStoreService | None = None,
        app_settings: Settings = settings,
    ) -> None:
        self.settings = app_settings
        self.embedding_service = embedding_service or get_embedding_service(app_settings)
        self.vector_store = vector_store or VectorStoreService(
            app_settings,
            collection_name=build_collection_name(
                app_settings.chroma_collection_prefix,
                self.embedding_service.provider,
                self.embedding_service.model,
            ),
        )

    def index_document(
        self,
        document: DocumentProcessingResponse,
    ) -> DocumentProcessingResponse:
        embeddings = self.embedding_service.embed_texts(
            [chunk.content for chunk in document.chunks]
        )
        indexed_chunks = self.vector_store.upsert_chunks(
            document=document.document,
            chunks=document.chunks,
            embeddings=embeddings,
        )
        return document.model_copy(
            update={
                "indexed_chunks": indexed_chunks,
                "collection": self.vector_store.collection_name,
                "embedding_provider": self.embedding_service.provider,
                "embedding_model": self.embedding_service.model,
            }
        )

    def search(self, query: str, top_k: int = 3) -> SemanticSearchResponse:
        query_embedding = self.embedding_service.embed_text(query)
        raw_results = self.vector_store.query(query_embedding, top_k)

        ids = (raw_results.get("ids") or [[]])[0]
        documents = (raw_results.get("documents") or [[]])[0]
        metadatas = (raw_results.get("metadatas") or [[]])[0]
        distances = (raw_results.get("distances") or [[]])[0]

        results: list[SemanticSearchResult] = []
        for position, (chunk_id, content, metadata, distance) in enumerate(
            zip(ids, documents, metadatas, distances, strict=True),
            start=1,
        ):
            similarity = distance_to_similarity(distance)
            result = SemanticSearchResult(
                position=position,
                chunk_id=chunk_id,
                document=str(metadata.get("document", "")),
                content=content,
                similarity=round(similarity, 6),
                similarity_percentage=round(similarity * 100, 2),
                chunk_index=int(metadata.get("chunk_index", 0)),
            )
            results.append(result)
            logger.info(
                "Resultado semántico: posición=%s chunk=%s score=%.2f%% documento=%s",
                position,
                chunk_id,
                result.similarity_percentage,
                result.document,
            )

        return SemanticSearchResponse(
            query=query,
            total_results=len(results),
            collection=self.vector_store.collection_name,
            embedding_provider=self.embedding_service.provider,
            embedding_model=self.embedding_service.model,
            results=results,
        )

    def status(self) -> VectorStoreStatusResponse:
        self.vector_store.heartbeat()
        return VectorStoreStatusResponse(
            status="active",
            collection=self.vector_store.collection_name,
            records=self.vector_store.count(),
            embedding_provider=self.embedding_service.provider,
            embedding_model=self.embedding_service.model,
        )
