import pytest

from app.utils.text_splitter import split_text


def test_splits_text_with_overlap() -> None:
    text = " ".join(f"palabra-{index:02d}" for index in range(80))
    chunks = split_text(text, chunk_size=120, chunk_overlap=20)

    assert len(chunks) > 1
    assert all(chunk.content for chunk in chunks)
    assert all(len(chunk.content) <= 120 for chunk in chunks)
    assert chunks[0].end - chunks[1].start >= 20
    assert chunks[1].content[0] != " "
    assert text[chunks[1].start : chunks[0].end] == (
        chunks[0].content[chunks[1].start - chunks[0].start :]
    )


@pytest.mark.parametrize(
    ("chunk_size", "chunk_overlap"),
    [(0, 0), (100, -1), (100, 100), (100, 101)],
)
def test_rejects_invalid_configuration(chunk_size: int, chunk_overlap: int) -> None:
    with pytest.raises(ValueError):
        split_text("texto de prueba", chunk_size, chunk_overlap)


def test_empty_text_returns_no_chunks() -> None:
    assert split_text("   \n  ") == []
