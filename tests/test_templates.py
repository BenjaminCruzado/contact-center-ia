from app.prompts.templates import (
    OUT_OF_SCOPE_RESPONSE,
    build_messages,
    build_system_prompt,
    build_user_prompt,
    format_context_blocks,
)
from app.schemas.search import SemanticSearchResult


def sample_result(position: int = 1, chunk_index: int = 0, content: str | None = None) -> SemanticSearchResult:
    return SemanticSearchResult(
        position=position,
        chunk_id=f"chunk-{position}",
        document="manual.pdf",
        content=content or "El sistema procesa documentos PDF y conserva contexto.",
        similarity=0.82,
        similarity_percentage=82.0,
        chunk_index=chunk_index,
        page_start=1,
        page_end=1,
        section_title="ARTÍCULO 3",
    )


def test_build_system_prompt_mentions_restrictions() -> None:
    prompt = build_system_prompt()

    assert "No inventes datos" in prompt
    assert "contexto documental" in prompt


def test_format_context_blocks_contains_metadata() -> None:
    context = format_context_blocks([sample_result()])

    assert "documento=manual.pdf" in context
    assert "similitud_max=82.00%" in context
    assert "paginas=1-1" in context


def test_format_context_blocks_groups_adjacent_chunks() -> None:
    context = format_context_blocks(
        [
            sample_result(position=1, chunk_index=10, content="Definición parte 1."),
            sample_result(position=2, chunk_index=11, content="Definición parte 2."),
        ]
    )

    assert context.count("[Fuente") == 1
    assert "Definición parte 1." in context
    assert "Definición parte 2." in context


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
