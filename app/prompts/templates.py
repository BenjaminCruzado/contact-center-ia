from collections.abc import Sequence

from app.schemas.search import SemanticSearchResult

OUT_OF_SCOPE_RESPONSE = (
    "No encontré información suficiente en los documentos cargados para responder "
    "esa consulta."
)


def _collapse_whitespace(value: str) -> str:
    return " ".join(value.split())


def build_system_prompt() -> str:
    return (
        "Eres el orquestador del Contact Center interno. "
        "Responde únicamente con información presente en el contexto documental "
        "entregado. No inventes datos, no completes vacíos con conocimiento "
        "externo y no cites fuentes que no estén en el contexto. "
        "Si el contexto no permite responder con claridad, debes indicarlo "
        "explícitamente."
    )


def format_context_blocks(results: Sequence[SemanticSearchResult]) -> str:
    if not results:
        return "Sin contexto recuperado."

    blocks: list[str] = []
    for result in results:
        content = _collapse_whitespace(result.content)
        blocks.append(
            (
                f"[Fuente {result.position}] documento={result.document} "
                f"chunk={result.chunk_id} similitud={result.similarity_percentage:.2f}%\n"
                f"{content}"
            )
        )
    return "\n\n".join(blocks)


def build_user_prompt(query: str, results: Sequence[SemanticSearchResult]) -> str:
    context = format_context_blocks(results)
    return (
        "Consulta del usuario:\n"
        f"{query.strip()}\n\n"
        "Contexto recuperado:\n"
        f"{context}\n\n"
        "Instrucciones de respuesta:\n"
        "1. Responde en español.\n"
        "2. Fundamenta la respuesta solo en el contexto recuperado.\n"
        "3. Si falta información, dilo de forma explícita.\n"
        "4. Mantén la respuesta clara y breve."
    )


def build_messages(
    query: str,
    results: Sequence[SemanticSearchResult],
) -> list[dict[str, str]]:
    return [
        {"role": "system", "content": build_system_prompt()},
        {"role": "user", "content": build_user_prompt(query, results)},
    ]
