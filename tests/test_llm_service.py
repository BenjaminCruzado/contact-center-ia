import pytest

from app.config.settings import Settings
from app.schemas.search import SemanticSearchResult
from app.services.llm_service import (
    LlmConfigurationError,
    MockLlmService,
    OpenAiLlmService,
    get_llm_service,
)


def sample_result() -> SemanticSearchResult:
    return SemanticSearchResult(
        position=1,
        chunk_id="chunk-1",
        document="manual.pdf",
        content=(
            "El sistema recibe documentos PDF, extrae texto plano y conserva "
            "contexto mediante fragmentos solapados."
        ),
        similarity=0.83,
        similarity_percentage=83.0,
        chunk_index=0,
    )


def test_mock_llm_generates_grounded_answer() -> None:
    service = MockLlmService()

    answer = service.generate_answer(
        query="¿Qué hace el sistema?",
        context_results=[sample_result()],
        system_prompt="sistema",
        user_prompt="usuario",
    )

    assert "Según la documentación cargada" in answer
    assert "documentos PDF" in answer


def test_openai_llm_requires_api_key_without_client() -> None:
    service = OpenAiLlmService(app_settings=Settings(openai_api_key=None))

    with pytest.raises(LlmConfigurationError):
        service.generate_answer(
            query="consulta",
            context_results=[sample_result()],
            system_prompt="sistema",
            user_prompt="usuario",
        )


def test_llm_factory_selects_provider() -> None:
    assert isinstance(get_llm_service(Settings(llm_provider="mock")), MockLlmService)
    assert isinstance(
        get_llm_service(Settings(llm_provider="openai")),
        OpenAiLlmService,
    )
