from types import SimpleNamespace

import pytest

from app.config.settings import Settings
from app.services.embedding_service import (
    EmbeddingConfigurationError,
    LocalEmbeddingService,
    OpenAIEmbeddingService,
    get_embedding_service,
)
from app.config.settings import settings


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
    service = OpenAIEmbeddingService(client=FakeOpenAI())

    result = service.embed_texts(["primero", "segundo"])

    assert result == [[0.1, 0.2], [0.3, 0.4]]


def test_rejects_empty_embedding_text() -> None:
    service = OpenAIEmbeddingService(client=FakeOpenAI())

    with pytest.raises(ValueError):
        service.embed_texts(["texto", " "])


def test_requires_api_key_without_injected_client() -> None:
    service = OpenAIEmbeddingService(
        app_settings=Settings(openai_api_key=None),
    )

    with pytest.raises(EmbeddingConfigurationError):
        service.embed_text("consulta")


class FakeLocalModel:
    def encode(self, texts: list[str], **_: object) -> object:
        import numpy as np

        return np.array([[float(index), 1.0] for index, _ in enumerate(texts)])


def test_local_provider_generates_embeddings_without_api_key() -> None:
    service = LocalEmbeddingService(
        app_settings=Settings(embedding_provider="local"),
        model_instance=FakeLocalModel(),
    )

    assert service.embed_texts(["uno", "dos"]) == [[0.0, 1.0], [1.0, 1.0]]
    assert service.provider == "local"


def test_factory_selects_provider() -> None:
    assert isinstance(
        get_embedding_service(Settings(embedding_provider="local")),
        LocalEmbeddingService,
    )
    assert isinstance(
        get_embedding_service(Settings(embedding_provider="openai")),
        OpenAIEmbeddingService,
    )


def test_factory_caches_default_embedding_service() -> None:
    first = get_embedding_service(settings)
    second = get_embedding_service(settings)

    assert first is second
