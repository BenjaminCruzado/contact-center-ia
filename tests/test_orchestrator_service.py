from app.config.settings import Settings
from app.schemas.search import (
    SemanticSearchResponse,
    SemanticSearchResult,
)
from app.services.orchestrator_service import OrchestratorService


class FakeRagService:
    def __init__(self, similarity: float = 0.82) -> None:
        self.similarity = similarity

    def search(self, query: str, top_k: int) -> SemanticSearchResponse:
        result = SemanticSearchResult(
            position=1,
            chunk_id="chunk-1",
            document="manual.pdf",
            content=(
                "El sistema recibe documentos PDF, extrae texto plano y divide "
                "el contenido en fragmentos solapados."
            ),
            similarity=self.similarity,
            similarity_percentage=round(self.similarity * 100, 2),
            chunk_index=0,
        )
        return SemanticSearchResponse(
            query=query,
            total_results=min(top_k, 1),
            collection="test-collection",
            embedding_provider="local",
            embedding_model="test-embedding",
            results=[result],
        )


class FakeLlmService:
    provider = "mock"
    model = "mock-rag-responder-v1"

    def generate_answer(
        self,
        query: str,
        context_results: list[SemanticSearchResult],
        system_prompt: str,
        user_prompt: str,
    ) -> str:
        assert query
        assert context_results
        assert "No inventes datos" in system_prompt
        assert "Consulta del usuario" in user_prompt
        return "Respuesta fundamentada."


def test_orchestrator_returns_answer_when_context_is_sufficient() -> None:
    service = OrchestratorService(
        rag_service=FakeRagService(similarity=0.82),
        llm_service=FakeLlmService(),
        app_settings=Settings(rag_min_similarity=0.45, rag_min_results=1),
    )

    response = service.respond("¿Qué hace el sistema?", top_k=3)

    assert response.status == "answered"
    assert response.llm_invoked is True
    assert response.total_sources == 1
    assert response.answer == "Respuesta fundamentada."


def test_orchestrator_returns_out_of_scope_when_context_is_insufficient() -> None:
    service = OrchestratorService(
        rag_service=FakeRagService(similarity=0.10),
        llm_service=FakeLlmService(),
        app_settings=Settings(rag_min_similarity=0.45, rag_min_results=1),
    )

    response = service.respond("Consulta fuera de alcance", top_k=3)

    assert response.status == "out_of_scope"
    assert response.llm_invoked is False
    assert response.total_sources == 0
    assert "No encontré información suficiente" in response.answer
