import pytest

from app.utils.text_splitter import split_text


def test_splits_text_with_overlap() -> None:
    text = (
        "ARTÍCULO 1. Definición general.\n\n"
        + " ".join(f"palabra-{index:02d}" for index in range(80))
        + "\n\nARTÍCULO 2. Continuidad.\n\n"
        + " ".join(f"termino-{index:02d}" for index in range(80))
    )
    chunks = split_text(text, chunk_size=220, chunk_overlap=60)

    assert len(chunks) > 1
    assert all(chunk.content for chunk in chunks)
    assert all(len(chunk.content) <= 220 for chunk in chunks)
    assert chunks[0].end > chunks[1].start


def test_preserves_article_section_title_when_detected() -> None:
    text = (
        "ARTÍCULO 3: Violencia de género.\n\n"
        "Cualquier acción o conducta basada en el sexo o género de una persona.\n\n"
        "Incluye daño físico, sexual o psicológico."
    )

    chunks = split_text(text, chunk_size=160, chunk_overlap=30)

    assert chunks[0].section_title == "ARTÍCULO 3: Violencia de género."
    assert "Cualquier acción o conducta" in chunks[0].content


@pytest.mark.parametrize(
    ("chunk_size", "chunk_overlap"),
    [(0, 0), (100, -1), (100, 100), (100, 101)],
)
def test_rejects_invalid_configuration(chunk_size: int, chunk_overlap: int) -> None:
    with pytest.raises(ValueError):
        split_text("texto de prueba", chunk_size, chunk_overlap)


def test_empty_text_returns_no_chunks() -> None:
    assert split_text("   \n  ") == []
