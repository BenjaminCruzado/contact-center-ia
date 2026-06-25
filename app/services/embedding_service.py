import logging
from collections.abc import Sequence

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
    """Error controlado del proveedor de embeddings."""


class EmbeddingConfigurationError(EmbeddingServiceError):
    """La integración no cuenta con una credencial válida."""


class EmbeddingProviderError(EmbeddingServiceError):
    """OpenAI no pudo generar los embeddings."""


class EmbeddingService:
    def __init__(
        self,
        app_settings: Settings = settings,
        client: OpenAI | None = None,
    ) -> None:
        self.settings = app_settings
        self._client = client

    @property
    def model(self) -> str:
        return self.settings.openai_embedding_model

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
        clean_texts = [text.strip() for text in texts]
        if not clean_texts or any(not text for text in clean_texts):
            raise ValueError("Los textos para embeddings no pueden estar vacíos.")

        logger.info(
            "Solicitando embeddings: modelo=%s textos=%s",
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

        dimensions = len(embeddings[0]) if embeddings else 0
        logger.info(
            "Embeddings generados: modelo=%s vectores=%s dimensiones=%s",
            self.model,
            len(embeddings),
            dimensions,
        )
        return embeddings

    def embed_text(self, text: str) -> list[float]:
        return self.embed_texts([text])[0]
