import pytest
from fastapi.testclient import TestClient

from app.api.routers.documentos import get_rag_service
from app.main import app
from app.schemas.search import (
    SemanticSearchResponse,
    SemanticSearchResult,
    VectorStoreStatusResponse,
)


class FakeSearchRagService:
    def search(self, query: str, top_k: int) -> SemanticSearchResponse:
        results = [
            SemanticSearchResult(
                position=index + 1,
                chunk_id=f"chunk-{index + 1}",
                document="manual.pdf",
                content=f"Contenido relevante {index + 1}",
                similarity=0.9 - index * 0.1,
                similarity_percentage=90 - index * 10,
                chunk_index=index,
            )
            for index in range(min(top_k, 3))
        ]
        return SemanticSearchResponse(
            query=query,
            total_results=len(results),
            collection="test-collection",
            results=results,
        )

    def status(self) -> VectorStoreStatusResponse:
        return VectorStoreStatusResponse(
            status="active",
            collection="test-collection",
            records=6,
        )


client = TestClient(app)


@pytest.fixture(autouse=True)
def override_rag_service() -> None:
    app.dependency_overrides[get_rag_service] = FakeSearchRagService
    yield
    app.dependency_overrides.pop(get_rag_service, None)


def test_search_endpoint_returns_three_results() -> None:
    response = client.post(
        "/documentos/buscar",
        json={"query": "¿Cómo conserva contexto?", "top_k": 3},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["total_results"] == 3
    assert payload["results"][0]["similarity_percentage"] == 90.0


def test_vector_store_status_endpoint() -> None:
    response = client.get("/documentos/vector-store/status")

    assert response.status_code == 200
    assert response.json()["records"] == 6


def test_search_rejects_blank_query() -> None:
    response = client.post(
        "/documentos/buscar",
        json={"query": " ", "top_k": 3},
    )

    assert response.status_code == 422
