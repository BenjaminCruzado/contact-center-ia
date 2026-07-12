import pytest

from app.schemas.document import TextChunkResponse
from app.services.vector_store_service import (
    EmptyVectorStoreError,
    VectorStoreService,
    build_collection_name,
)


class FakeCollection:
    def __init__(self) -> None:
        self.records: dict[str, object] = {}

    def upsert(self, **kwargs: object) -> None:
        self.records = kwargs

    def count(self) -> int:
        ids = self.records.get("ids", [])
        return len(ids)  # type: ignore[arg-type]

    def query(self, **_: object) -> dict[str, object]:
        return {
            "ids": [["chunk-1"]],
            "documents": [["contenido"]],
            "metadatas": [[{"document": "manual.pdf", "chunk_index": 0, "page_start": 1, "page_end": 1, "section_title": "ARTÍCULO 1"}]],
            "distances": [[0.15]],
        }


class FakeChromaClient:
    def __init__(self) -> None:
        self.collection = FakeCollection()
        self.configuration: object = None

    def heartbeat(self) -> int:
        return 123

    def get_or_create_collection(self, **kwargs: object) -> FakeCollection:
        self.configuration = kwargs.get("configuration")
        return self.collection


def sample_chunk() -> TextChunkResponse:
    return TextChunkResponse(
        id="chunk-1",
        index=0,
        content="contenido",
        character_count=9,
        start_character=0,
        end_character=9,
        page_start=1,
        page_end=1,
        section_title="ARTÍCULO 1",
    )


def test_upserts_chunks_with_cosine_collection() -> None:
    client = FakeChromaClient()
    service = VectorStoreService(client=client)

    indexed = service.upsert_chunks("manual.pdf", [sample_chunk()], [[0.1, 0.2]])

    assert indexed == 1
    assert client.configuration == {"hnsw": {"space": "cosine"}}
    assert client.collection.records["ids"] == ["chunk-1"]
    assert client.collection.records["metadatas"][0]["page_start"] == 1


def test_empty_collection_cannot_be_queried() -> None:
    service = VectorStoreService(client=FakeChromaClient())

    with pytest.raises(EmptyVectorStoreError):
        service.query([0.1, 0.2], 3)


def test_collection_name_separates_provider_and_model() -> None:
    local = build_collection_name(
        "contact-center-documents",
        "local",
        "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
    )
    openai = build_collection_name(
        "contact-center-documents",
        "openai",
        "text-embedding-3-small",
    )

    assert local != openai
    assert "/" not in local
