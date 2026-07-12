from app.prompts.templates import (
    OUT_OF_SCOPE_RESPONSE,
    build_messages,
    build_system_prompt,
    build_user_prompt,
    format_context_blocks,
)
from app.schemas.search import SemanticSearchResult


def sample_result() -> SemanticSearchResult:
    return SemanticSearchResult(
        position=1,
        chunk_id="chunk-1",
        document="manual.pdf",
        content="El sistema procesa documentos PDF y conserva contexto.",
        similarity=0.82,
        similarity_percentage=82.0,
        chunk_index=0,
    )


def test_build_system_prompt_mentions_restrictions() -> None:
    prompt = build_system_prompt()

    assert "No inventes datos" in prompt
    assert "contexto documental" in prompt


def test_format_context_blocks_contains_metadata() -> None:
    context = format_context_blocks([sample_result()])

    assert "documento=manual.pdf" in context
    assert "similitud=82.00%" in context


def test_build_user_prompt_injects_query_and_context() -> None:
    prompt = build_user_prompt(
        "¿Qué hace el sistema?",
        [sample_result()],
    )

    assert "¿Qué hace el sistema?" in prompt
    assert "Contexto recuperado" in prompt
    assert "manual.pdf" in prompt


def test_build_messages_returns_system_and_user_roles() -> None:
    messages = build_messages("consulta", [sample_result()])

    assert len(messages) == 2
    assert messages[0]["role"] == "system"
    assert messages[1]["role"] == "user"


def test_out_of_scope_response_is_not_empty() -> None:
    assert OUT_OF_SCOPE_RESPONSE.endswith("consulta.")
