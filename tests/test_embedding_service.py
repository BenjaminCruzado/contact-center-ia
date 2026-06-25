from types import SimpleNamespace

import pytest

from app.config.settings import Settings
from app.services.embedding_service import (
    EmbeddingConfigurationError,
    EmbeddingService,
)


class FakeEmbeddingsResource:
    def create(self, **_: object) -> SimpleNamespace:
        return SimpleNamespace(
            data=[
                SimpleNamespace(index=1, embedding=[0.3, 0.4]),
                SimpleNamespace(index=0, embedding=[0.1, 0.2]),
            ]
        )


class FakeOpenAI:
    embeddings = FakeEmbeddingsResource()


def test_embeddings_preserve_input_order() -> None:
    service = EmbeddingService(client=FakeOpenAI())

    result = service.embed_texts(["primero", "segundo"])

    assert result == [[0.1, 0.2], [0.3, 0.4]]


def test_rejects_empty_embedding_text() -> None:
    service = EmbeddingService(client=FakeOpenAI())

    with pytest.raises(ValueError):
        service.embed_texts(["texto", " "])


def test_requires_api_key_without_injected_client() -> None:
    service = EmbeddingService(
        app_settings=Settings(openai_api_key=None),
    )

    with pytest.raises(EmbeddingConfigurationError):
        service.embed_text("consulta")
