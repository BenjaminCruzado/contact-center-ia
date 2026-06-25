from dataclasses import dataclass


@dataclass(frozen=True)
class TextChunk:
    index: int
    content: str
    start: int
    end: int


def split_text(
    text: str,
    chunk_size: int = 500,
    chunk_overlap: int = 50,
) -> list[TextChunk]:
    """Divide texto por caracteres, conservando contexto mediante solapamiento."""
    if chunk_size <= 0:
        raise ValueError("chunk_size debe ser mayor que cero.")
    if chunk_overlap < 0:
        raise ValueError("chunk_overlap no puede ser negativo.")
    if chunk_overlap >= chunk_size:
        raise ValueError("chunk_overlap debe ser menor que chunk_size.")

    clean_text = text.strip()
    if not clean_text:
        return []

    chunks: list[TextChunk] = []
    start = 0
    text_length = len(clean_text)

    while start < text_length:
        maximum_end = min(start + chunk_size, text_length)
        end = maximum_end

        if maximum_end < text_length:
            search_start = start + max(1, chunk_size // 2)
            paragraph_break = clean_text.rfind("\n\n", search_start, maximum_end)
            word_break = clean_text.rfind(" ", search_start, maximum_end)
            preferred_break = max(paragraph_break, word_break)
            if preferred_break > start:
                end = preferred_break

        content_start = start
        while content_start < end and clean_text[content_start].isspace():
            content_start += 1

        content_end = end
        while content_end > content_start and clean_text[content_end - 1].isspace():
            content_end -= 1

        content = clean_text[content_start:content_end]
        if content:
            chunks.append(
                TextChunk(
                    index=len(chunks),
                    content=content,
                    start=content_start,
                    end=content_end,
                )
            )

        if end >= text_length:
            break

        next_start = end - chunk_overlap
        if next_start > start:
            boundary_search_start = max(start + 1, next_start - 50)
            word_boundary = max(
                clean_text.rfind(" ", boundary_search_start, next_start + 1),
                clean_text.rfind("\n", boundary_search_start, next_start + 1),
            )
            if word_boundary >= boundary_search_start:
                next_start = word_boundary + 1

        start = next_start if next_start > start else end

    return chunks
