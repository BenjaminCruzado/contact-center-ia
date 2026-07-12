import logging
import re
from collections.abc import Sequence
from typing import Any

import chromadb

from app.config.settings import Settings, settings
from app.schemas.document import TextChunkResponse

logger = logging.getLogger("uvicorn.error")


def build_collection_name(prefix: str, provider: str, model: str) -> str:
    raw_name = f"{prefix}-{provider}-{model}".lower()
    safe_name = re.sub(r"[^a-z0-9._-]+", "-", raw_name).strip("-._")
    safe_name = re.sub(r"-{2,}", "-", safe_name)
    return safe_name[:512].rstrip("-._")


class VectorStoreError(RuntimeError):
    """Error controlado de la base vectorial."""


class VectorStoreUnavailableError(VectorStoreError):
    """ChromaDB no está disponible."""


class EmptyVectorStoreError(VectorStoreError):
    """La colección no contiene registros consultables."""


class VectorStoreService:
    def __init__(
        self,
        app_settings: Settings = settings,
        client: Any | None = None,
        collection_name: str | None = None,
    ) -> None:
        self.settings = app_settings
        self._client = client
        self._collection_name = collection_name

    @property
    def collection_name(self) -> str:
        return self._collection_name or self.settings.chroma_collection_prefix

    def _get_client(self) -> Any:
        if self._client is None:
            try:
                self._client = chromadb.HttpClient(
                    host=self.settings.chroma_host,
                    port=self.settings.chroma_port,
                )
            except Exception as exc:
                raise VectorStoreUnavailableError(
                    "No fue posible inicializar la conexión con ChromaDB."
                ) from exc
        return self._client

    def heartbeat(self) -> int:
        try:
            return int(self._get_client().heartbeat())
        except Exception as exc:
            raise VectorStoreUnavailableError(
                "ChromaDB no está disponible."
            ) from exc

    def get_collection(self) -> Any:
        try:
            return self._get_client().get_or_create_collection(
                name=self.collection_name,
                configuration={"hnsw": {"space": "cosine"}},
                embedding_function=None,
            )
        except Exception as exc:
            raise VectorStoreUnavailableError(
                "No fue posible obtener la colección vectorial."
            ) from exc

    def upsert_chunks(
        self,
        document: str,
        chunks: Sequence[TextChunkResponse],
        embeddings: Sequence[Sequence[float]],
    ) -> int:
        if len(chunks) != len(embeddings):
            raise ValueError("La cantidad de chunks y embeddings debe coincidir.")
        if not chunks:
            return 0

        metadatas = [
            {
                "document": document,
                "chunk_index": chunk.index,
                "character_count": chunk.character_count,
                "start_character": chunk.start_character,
                "end_character": chunk.end_character,
                "page_start": chunk.page_start,
                "page_end": chunk.page_end,
                "section_title": chunk.section_title or "",
            }
            for chunk in chunks
        ]

        try:
            self.get_collection().upsert(
                ids=[chunk.id for chunk in chunks],
                embeddings=[list(vector) for vector in embeddings],
                documents=[chunk.content for chunk in chunks],
                metadatas=metadatas,
            )
        except Exception as exc:
            raise VectorStoreUnavailableError(
                "No fue posible registrar los chunks en ChromaDB."
            ) from exc

        logger.info(
            "Chunks indexados: colección=%s documento=%s registros=%s",
            self.collection_name,
            document,
            len(chunks),
        )
        return len(chunks)

    def count(self) -> int:
        try:
            return int(self.get_collection().count())
        except VectorStoreUnavailableError:
            raise
        except Exception as exc:
            raise VectorStoreUnavailableError(
                "No fue posible contar los registros de ChromaDB."
            ) from exc

    def query(self, embedding: Sequence[float], top_k: int) -> dict[str, Any]:
        available_records = self.count()
        if available_records == 0:
            raise EmptyVectorStoreError(
                "La base vectorial no contiene documentos indexados."
            )

        try:
            return self.get_collection().query(
                query_embeddings=[list(embedding)],
                n_results=min(top_k, available_records),
                include=["documents", "metadatas", "distances"],
            )
        except Exception as exc:
            raise VectorStoreUnavailableError(
                "No fue posible ejecutar la búsqueda en ChromaDB."
            ) from exc
