import logging
from collections.abc import Sequence
from typing import Any, Protocol

from openai import (
    APIConnectionError,
    APIStatusError,
    APITimeoutError,
    AuthenticationError,
    OpenAI,
    RateLimitError,
)

from app.config.settings import Settings, settings

logger = logging.getLogger("uvicorn.error")


class EmbeddingServiceError(RuntimeError):
    """Error controlado de un proveedor de embeddings."""


class EmbeddingConfigurationError(EmbeddingServiceError):
    """El proveedor seleccionado no tiene una configuración válida."""


class EmbeddingProviderError(EmbeddingServiceError):
    """El proveedor no pudo generar los embeddings."""


class EmbeddingService(Protocol):
    provider: str
    model: str

    def embed_texts(self, texts: Sequence[str]) -> list[list[float]]: ...

    def embed_text(self, text: str) -> list[float]: ...


def _clean_texts(texts: Sequence[str]) -> list[str]:
    clean_texts = [text.strip() for text in texts]
    if not clean_texts or any(not text for text in clean_texts):
        raise ValueError("Los textos para embeddings no pueden estar vacíos.")
    return clean_texts


class LocalEmbeddingService:
    provider = "local"

    def __init__(
        self,
        app_settings: Settings = settings,
        model_instance: Any | None = None,
    ) -> None:
        self.settings = app_settings
        self.model = app_settings.local_embedding_model
        self._model_instance = model_instance

    def _get_model(self) -> Any:
        if self._model_instance is None:
            try:
                from sentence_transformers import SentenceTransformer

                logger.info(
                    "Cargando modelo local de embeddings: modelo=%s dispositivo=%s",
                    self.model,
                    self.settings.local_embedding_device,
                )
                self._model_instance = SentenceTransformer(
                    self.model,
                    device=self.settings.local_embedding_device,
                    cache_folder=self.settings.sentence_transformers_home,
                )
            except Exception as exc:
                raise EmbeddingProviderError(
                    "No fue posible cargar el modelo local de embeddings."
                ) from exc
        return self._model_instance

    def embed_texts(self, texts: Sequence[str]) -> list[list[float]]:
        clean_texts = _clean_texts(texts)
        try:
            vectors = self._get_model().encode(
                clean_texts,
                batch_size=self.settings.local_embedding_batch_size,
                show_progress_bar=False,
                convert_to_numpy=True,
                normalize_embeddings=True,
            )
            embeddings = vectors.tolist()
        except EmbeddingProviderError:
            raise
        except Exception as exc:
            raise EmbeddingProviderError(
                "El modelo local no pudo generar los embeddings."
            ) from exc

        logger.info(
            "Embeddings locales generados: modelo=%s vectores=%s dimensiones=%s",
            self.model,
            len(embeddings),
            len(embeddings[0]) if embeddings else 0,
        )
        return embeddings

    def embed_text(self, text: str) -> list[float]:
        return self.embed_texts([text])[0]


class OpenAIEmbeddingService:
    provider = "openai"

    def __init__(
        self,
        app_settings: Settings = settings,
        client: OpenAI | None = None,
    ) -> None:
        self.settings = app_settings
        self.model = app_settings.openai_embedding_model
        self._client = client

    def _get_client(self) -> OpenAI:
        if self._client is not None:
            return self._client

        secret = self.settings.openai_api_key
        api_key = secret.get_secret_value().strip() if secret else ""
        if not api_key:
            raise EmbeddingConfigurationError(
                "OPENAI_API_KEY no está configurada en el entorno."
            )

        self._client = OpenAI(
            api_key=api_key,
            timeout=self.settings.openai_timeout_seconds,
            max_retries=self.settings.openai_max_retries,
        )
        return self._client

    def embed_texts(self, texts: Sequence[str]) -> list[list[float]]:
        clean_texts = _clean_texts(texts)
        logger.info(
            "Solicitando embeddings OpenAI: modelo=%s textos=%s",
            self.model,
            len(clean_texts),
        )

        try:
            response = self._get_client().embeddings.create(
                model=self.model,
                input=clean_texts,
                encoding_format="float",
            )
        except AuthenticationError as exc:
            raise EmbeddingConfigurationError(
                "OpenAI rechazó la credencial configurada."
            ) from exc
        except RateLimitError as exc:
            raise EmbeddingProviderError(
                "OpenAI alcanzó el límite de solicitudes o cuota disponible."
            ) from exc
        except (APITimeoutError, APIConnectionError) as exc:
            raise EmbeddingProviderError(
                "No fue posible conectar con el servicio de embeddings de OpenAI."
            ) from exc
        except APIStatusError as exc:
            raise EmbeddingProviderError(
                f"OpenAI respondió con un error HTTP {exc.status_code}."
            ) from exc

        ordered_data = sorted(response.data, key=lambda item: item.index)
        embeddings = [item.embedding for item in ordered_data]
        if len(embeddings) != len(clean_texts):
            raise EmbeddingProviderError(
                "OpenAI devolvió una cantidad inesperada de embeddings."
            )
        return embeddings

    def embed_text(self, text: str) -> list[float]:
        return self.embed_texts([text])[0]


def get_embedding_service(
    app_settings: Settings = settings,
) -> EmbeddingService:
    if app_settings.embedding_provider == "local":
        return LocalEmbeddingService(app_settings)
    if app_settings.embedding_provider == "openai":
        return OpenAIEmbeddingService(app_settings)
    raise EmbeddingConfigurationError(
        f"Proveedor de embeddings no soportado: {app_settings.embedding_provider}"
    )
