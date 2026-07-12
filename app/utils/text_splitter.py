from dataclasses import dataclass
import re


ARTICLE_PATTERN = re.compile(
    r"^(art[íi]culo|art\.|cap[íi]tulo|t[íi]tulo|secci[óo]n|inciso|p[aá]rrafo)\b",
    re.IGNORECASE,
)
LIST_ITEM_PATTERN = re.compile(r"^(?:\d+[\)\.\-:]|[ivxlcdm]+[\)\.\-:]|[a-z][\)\.\-:])\s+", re.IGNORECASE)


@dataclass(frozen=True)
class TextChunk:
    index: int
    content: str
    start: int
    end: int
    section_title: str | None = None


@dataclass(frozen=True)
class _TextBlock:
    text: str
    start: int
    end: int
    section_title: str | None


def _normalize_inline_whitespace(value: str) -> str:
    return re.sub(r"[^\S\r\n]+", " ", value).strip()


def _extract_section_title(block_text: str) -> str | None:
    lines = [line.strip() for line in block_text.splitlines() if line.strip()]
    if not lines:
        return None

    first_line = _normalize_inline_whitespace(lines[0])
    if ARTICLE_PATTERN.match(first_line) or LIST_ITEM_PATTERN.match(first_line):
        return first_line[:140]

    if (
        len(first_line) <= 140
        and len(lines) == 1
        and first_line == first_line.upper()
        and any(char.isalpha() for char in first_line)
    ):
        return first_line

    return None


def _build_blocks(clean_text: str) -> list[_TextBlock]:
    blocks: list[_TextBlock] = []

    for match in re.finditer(r"\S[\s\S]*?(?=(?:\n\s*\n)+|\Z)", clean_text):
        start = match.start()
        end = match.end()
        raw_block = clean_text[start:end]
        text = raw_block.strip()
        if not text:
            continue
        normalized_text = re.sub(r"\n{3,}", "\n\n", text)
        blocks.append(
            _TextBlock(
                text=normalized_text,
                start=start,
                end=end,
                section_title=_extract_section_title(normalized_text),
            )
        )

    if not blocks:
        blocks.append(
            _TextBlock(
                text=clean_text,
                start=0,
                end=len(clean_text),
                section_title=_extract_section_title(clean_text),
            )
        )

    return blocks


def _fallback_split_large_block(
    text: str,
    block_start: int,
    chunk_size: int,
    chunk_overlap: int,
    index_start: int,
    section_title: str | None,
) -> list[TextChunk]:
    chunks: list[TextChunk] = []
    local_start = 0

    while local_start < len(text):
        maximum_end = min(local_start + chunk_size, len(text))
        local_end = maximum_end

        if maximum_end < len(text):
            search_start = local_start + max(1, chunk_size // 2)
            paragraph_break = text.rfind("\n\n", search_start, maximum_end)
            line_break = text.rfind("\n", search_start, maximum_end)
            word_break = text.rfind(" ", search_start, maximum_end)
            preferred_break = max(paragraph_break, line_break, word_break)
            if preferred_break > local_start:
                local_end = preferred_break

        content = text[local_start:local_end].strip()
        if content:
            start = block_start + local_start
            end = block_start + local_end
            chunks.append(
                TextChunk(
                    index=index_start + len(chunks),
                    content=content,
                    start=start,
                    end=end,
                    section_title=section_title,
                )
            )

        if local_end >= len(text):
            break

        next_start = max(local_end - chunk_overlap, local_start + 1)
        boundary = max(
            text.rfind(" ", max(local_start + 1, next_start - 40), next_start + 1),
            text.rfind("\n", max(local_start + 1, next_start - 40), next_start + 1),
        )
        local_start = boundary + 1 if boundary >= 0 else next_start

    return chunks


def split_text(
    text: str,
    chunk_size: int = 500,
    chunk_overlap: int = 50,
) -> list[TextChunk]:
    """Divide texto con estrategia híbrida: bloques semánticos + fallback por caracteres."""
    if chunk_size <= 0:
        raise ValueError("chunk_size debe ser mayor que cero.")
    if chunk_overlap < 0:
        raise ValueError("chunk_overlap no puede ser negativo.")
    if chunk_overlap >= chunk_size:
        raise ValueError("chunk_overlap debe ser menor que chunk_size.")

    clean_text = text.strip()
    if not clean_text:
        return []

    blocks = _build_blocks(clean_text)
    chunks: list[TextChunk] = []
    start_block_index = 0

    while start_block_index < len(blocks):
        current_length = 0
        selected_indices: list[int] = []
        section_title: str | None = None
        block_index = start_block_index

        while block_index < len(blocks):
            block = blocks[block_index]
            block_length = len(block.text)
            separator_length = 2 if selected_indices else 0

            if not selected_indices and block_length > chunk_size:
                chunks.extend(
                    _fallback_split_large_block(
                        text=block.text,
                        block_start=block.start,
                        chunk_size=chunk_size,
                        chunk_overlap=chunk_overlap,
                        index_start=len(chunks),
                        section_title=block.section_title,
                    )
                )
                start_block_index = block_index + 1
                break

            if selected_indices and current_length + separator_length + block_length > chunk_size:
                if (
                    len(selected_indices) == 1
                    and section_title
                    and len(blocks[selected_indices[0]].text) <= min(160, chunk_size // 2)
                ):
                    combined_text = (
                        blocks[selected_indices[0]].text.strip()
                        + "\n\n"
                        + block.text.strip()
                    )
                    chunks.extend(
                        _fallback_split_large_block(
                            text=combined_text,
                            block_start=blocks[selected_indices[0]].start,
                            chunk_size=chunk_size,
                            chunk_overlap=chunk_overlap,
                            index_start=len(chunks),
                            section_title=section_title,
                        )
                    )
                    start_block_index = block_index + 1
                    selected_indices = []
                break

            selected_indices.append(block_index)
            current_length += separator_length + block_length
            section_title = section_title or block.section_title
            block_index += 1
        else:
            start_block_index = len(blocks)

        if not selected_indices:
            continue

        chunk_blocks = [blocks[index] for index in selected_indices]
        chunk_text = "\n\n".join(block.text for block in chunk_blocks).strip()
        start = chunk_blocks[0].start
        end = chunk_blocks[-1].end

        chunks.append(
            TextChunk(
                index=len(chunks),
                content=chunk_text,
                start=start,
                end=end,
                section_title=section_title,
            )
        )

        if start_block_index == len(blocks):
            break

        overlap_length = 0
        next_start_block_index = selected_indices[-1] + 1
        for previous_index in reversed(selected_indices):
            overlap_length += len(blocks[previous_index].text)
            next_start_block_index = previous_index
            if overlap_length >= chunk_overlap:
                break

        if next_start_block_index <= selected_indices[0]:
            next_start_block_index = selected_indices[-1]

        start_block_index = min(next_start_block_index + 1, len(blocks))

    return chunks
