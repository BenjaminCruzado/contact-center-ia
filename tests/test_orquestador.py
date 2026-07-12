import pytest
from fastapi.testclient import TestClient

from app.api.routers.orquestador import get_orchestrator_service
from app.main import app
from app.schemas.orchestrator import OrchestratorResponse, OrchestratorSource


class FakeOrchestratorService:
    def __init__(self, status: str = "answered") -> None:
        self.status = status

    def respond(self, query: str, top_k: int) -> OrchestratorResponse:
        source = OrchestratorSource(
            position=1,
            chunk_id="chunk-1",
            document="manual.pdf",
            content="Contenido recuperado",
            similarity=0.9,
            similarity_percentage=90.0,
            chunk_index=0,
        )
        if self.status == "out_of_scope":
            return OrchestratorResponse(
                query=query,
                status="out_of_scope",
                answer="No encontré información suficiente en los documentos cargados para responder esa consulta.",
                collection="test-collection",
                llm_provider="mock",
                llm_model="mock-rag-responder-v1",
                llm_invoked=False,
                total_sources=0,
                sources=[],
            )

        return OrchestratorResponse(
            query=query,
            status="answered",
            answer=f"Respuesta para {query}",
            collection="test-collection",
            llm_provider="mock",
            llm_model="mock-rag-responder-v1",
            llm_invoked=True,
            total_sources=min(top_k, 1),
            sources=[source],
        )


client = TestClient(app)


@pytest.fixture(autouse=True)
def clear_override() -> None:
    yield
    app.dependency_overrides.pop(get_orchestrator_service, None)


def test_orchestrator_endpoint_returns_answer() -> None:
    app.dependency_overrides[get_orchestrator_service] = FakeOrchestratorService

    response = client.post(
        "/orquestador/responder",
        json={"query": "¿Qué hace el sistema?", "top_k": 3},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "answered"
    assert response.json()["llm_invoked"] is True


def test_orchestrator_endpoint_returns_out_of_scope() -> None:
    app.dependency_overrides[get_orchestrator_service] = (
        lambda: FakeOrchestratorService(status="out_of_scope")
    )

    response = client.post(
        "/orquestador/responder",
        json={"query": "Tema ajeno al manual", "top_k": 3},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "out_of_scope"
    assert response.json()["llm_invoked"] is False


def test_orchestrator_endpoint_rejects_blank_query() -> None:
    app.dependency_overrides[get_orchestrator_service] = FakeOrchestratorService

    response = client.post(
        "/orquestador/responder",
        json={"query": " ", "top_k": 3},
    )

    assert response.status_code == 422
