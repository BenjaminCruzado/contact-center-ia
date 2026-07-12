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
        "Si el contexto contiene una definición o regla explícita, debes priorizarla. "
        "Si el contexto no permite responder con claridad, debes indicarlo "
        "explícitamente."
    )


def _group_adjacent_results(
    results: Sequence[SemanticSearchResult],
) -> list[list[SemanticSearchResult]]:
    grouped: list[list[SemanticSearchResult]] = []
    for result in sorted(results, key=lambda item: (item.document, item.chunk_index, item.position)):
        if not grouped:
            grouped.append([result])
            continue

        previous = grouped[-1][-1]
        if (
            previous.document == result.document
            and result.chunk_index - previous.chunk_index <= 1
        ):
            grouped[-1].append(result)
            continue

        grouped.append([result])

    return grouped


def format_context_blocks(results: Sequence[SemanticSearchResult]) -> str:
    if not results:
        return "Sin contexto recuperado."

    blocks: list[str] = []
    grouped_results = _group_adjacent_results(results)

    for block_position, group in enumerate(grouped_results, start=1):
        first = group[0]
        last = group[-1]
        content = "\n\n".join(_collapse_whitespace(item.content) for item in group)
        metadata = [
            f"documento={first.document}",
            f"chunks={first.chunk_index}-{last.chunk_index}",
            f"similitud_max={max(item.similarity_percentage for item in group):.2f}%",
        ]
        if first.page_start is not None:
            metadata.append(f"paginas={first.page_start}-{last.page_end or first.page_start}")
        if first.section_title:
            metadata.append(f"seccion={first.section_title}")

        blocks.append(
            f"[Fuente {block_position}] {' '.join(metadata)}\n{content}"
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
        "3. Si existe una definición explícita, úsala textualmente o parafrasea con fidelidad.\n"
        "4. Menciona el documento y, si aparece, la sección o páginas relevantes.\n"
        "5. Si falta información, dilo de forma explícita.\n"
        "6. Mantén la respuesta clara y breve."
    )


def build_messages(
    query: str,
    results: Sequence[SemanticSearchResult],
) -> list[dict[str, str]]:
    return [
        {"role": "system", "content": build_system_prompt()},
        {"role": "user", "content": build_user_prompt(query, results)},
    ]
