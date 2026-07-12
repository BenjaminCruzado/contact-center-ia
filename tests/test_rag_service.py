from app.schemas.document import DocumentProcessingResponse, TextChunkResponse
from app.services.rag_service import RagService, distance_to_similarity


class FakeEmbeddingService:
    provider = "test"
    model = "test-embedding"

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        return [[float(index), 1.0] for index, _ in enumerate(texts)]

    def embed_text(self, _: str) -> list[float]:
        return [0.5, 1.0]


class FakeVectorStore:
    collection_name = "test-collection"

    def upsert_chunks(self, **kwargs: object) -> int:
        return len(kwargs["chunks"])  # type: ignore[arg-type]

    def query(self, _: list[float], top_k: int) -> dict[str, object]:
        assert top_k == 3
        return {
            "ids": [["chunk-a", "chunk-b", "chunk-c"]],
            "documents": [["A", "B", "C"]],
            "metadatas": [[
                {"document": "manual.pdf", "chunk_index": 0},
                {"document": "manual.pdf", "chunk_index": 1},
                {"document": "manual.pdf", "chunk_index": 2},
            ]],
            "distances": [[0.08, 0.22, 0.41]],
        }

    def heartbeat(self) -> int:
        return 1

    def count(self) -> int:
        return 3


def sample_document() -> DocumentProcessingResponse:
    chunks = [
        TextChunkResponse(
            id=f"chunk-{index}",
            index=index,
            content=f"Contenido {index}",
            character_count=11,
            start_character=index * 10,
            end_character=index * 10 + 11,
        )
        for index in range(3)
    ]
    return DocumentProcessingResponse(
        document="manual.pdf",
        pages=1,
        extracted_characters=33,
        chunk_size=500,
        chunk_overlap=50,
        total_chunks=3,
        chunks=chunks,
    )


def test_indexes_document_and_returns_metadata() -> None:
    service = RagService(FakeEmbeddingService(), FakeVectorStore())

    result = service.index_document(sample_document())

    assert result.indexed_chunks == 3
    assert result.collection == "test-collection"
    assert result.embedding_model == "test-embedding"


def test_search_returns_top_three_ordered_scores() -> None:
    service = RagService(FakeEmbeddingService(), FakeVectorStore())

    result = service.search("consulta", top_k=3)

    assert result.total_results == 3
    assert [item.chunk_id for item in result.results] == [
        "chunk-a",
        "chunk-b",
        "chunk-c",
    ]
    assert [item.similarity_percentage for item in result.results] == [
        92.0,
        78.0,
        59.0,
    ]


def test_distance_is_clamped_to_similarity_range() -> None:
    assert distance_to_similarity(-0.2) == 1.0
    assert distance_to_similarity(0.25) == 0.75
    assert distance_to_similarity(1.5) == 0.0
