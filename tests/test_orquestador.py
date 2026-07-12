import pytest
from fastapi.testclient import TestClient

from app.api.routers.orquestador import get_orchestrator_service
from app.main import app
from app.schemas.orchestrator import (
    OrchestratorResponse,
    OrchestratorSource,
    OrchestratorTrace,
)
from tests.auth_helpers import make_auth_header


class FakeOrchestratorService:
    def __init__(self, status: str = "answered") -> None:
        self.status = status

    def respond(self, query: str, top_k: int) -> OrchestratorResponse:
        return self.respond_with_trace(query, top_k).response

    def respond_with_trace(self, query: str, top_k: int) -> OrchestratorTrace:
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
            return OrchestratorTrace(
                response=OrchestratorResponse(
                    query=query,
                    status="out_of_scope",
                    answer="No encontré información suficiente en los documentos cargados para responder esa consulta.",
                    collection="test-collection",
                    llm_provider="mock",
                    llm_model="mock-rag-responder-v1",
                    llm_invoked=False,
                    total_sources=0,
                    sources=[],
                ),
                rag_latency_ms=12.0,
                llm_latency_ms=0.0,
                total_latency_ms=12.0,
                top_score=0.10,
            )

        return OrchestratorTrace(
            response=OrchestratorResponse(
                query=query,
                status="answered",
                answer=f"Respuesta para {query}",
                collection="test-collection",
                llm_provider="mock",
                llm_model="mock-rag-responder-v1",
                llm_invoked=True,
                total_sources=min(top_k, 1),
                sources=[source],
            ),
            rag_latency_ms=12.0,
            llm_latency_ms=25.0,
            total_latency_ms=37.0,
            top_score=0.90,
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
        headers=make_auth_header("user"),
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
        headers=make_auth_header("user"),
    )

    assert response.status_code == 200
    assert response.json()["status"] == "out_of_scope"
    assert response.json()["llm_invoked"] is False


def test_orchestrator_endpoint_rejects_blank_query() -> None:
    app.dependency_overrides[get_orchestrator_service] = FakeOrchestratorService

    response = client.post(
        "/orquestador/responder",
        json={"query": " ", "top_k": 3},
        headers=make_auth_header("user"),
    )

    assert response.status_code == 422


def test_orchestrator_endpoint_requires_user_role() -> None:
    app.dependency_overrides[get_orchestrator_service] = FakeOrchestratorService

    response = client.post(
        "/orquestador/responder",
        json={"query": "¿Qué hace el sistema?", "top_k": 3},
        headers=make_auth_header("admin"),
    )

    assert response.status_code == 403
