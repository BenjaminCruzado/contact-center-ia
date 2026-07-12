import logging
import re
from collections.abc import Sequence
from typing import Protocol

import httpx
from openai import (
    APIConnectionError,
    APIStatusError,
    APITimeoutError,
    AuthenticationError,
    OpenAI,
    RateLimitError,
)

from app.config.settings import Settings, settings
from app.schemas.search import SemanticSearchResult

logger = logging.getLogger("uvicorn.error")


class LlmServiceError(RuntimeError):
    """Error controlado del servicio LLM."""


class LlmConfigurationError(LlmServiceError):
    """El proveedor LLM no posee configuración válida."""


class LlmProviderError(LlmServiceError):
    """El proveedor LLM no pudo generar una respuesta."""


class LlmService(Protocol):
    provider: str
    model: str

    def generate_answer(
        self,
        query: str,
        context_results: Sequence[SemanticSearchResult],
        system_prompt: str,
        user_prompt: str,
    ) -> str: ...


def _collapse_whitespace(value: str) -> str:
    return " ".join(value.split())


def _trim_snippet(value: str, max_length: int = 220) -> str:
    clean_value = _collapse_whitespace(value)
    sentence_match = re.match(r"(.+?[.!?])(?:\s|$)", clean_value)
    if sentence_match:
        sentence = sentence_match.group(1).strip()
        if len(sentence) <= max_length:
            return sentence.rstrip(" .,:;")
    if len(clean_value) <= max_length:
        return clean_value.rstrip(" .,:;")
    return clean_value[:max_length].rsplit(" ", 1)[0].rstrip(" .,:;") + "..."


def _normalize_ollama_base_url(value: str) -> str:
    normalized = value.strip().rstrip("/")
    if not normalized:
        raise LlmConfigurationError("OLLAMA_BASE_URL no está configurada.")
    if normalized.endswith("/api"):
        return normalized
    return f"{normalized}/api"


class MockLlmService:
    provider = "mock"
    model = "mock-rag-responder-v1"

    def generate_answer(
        self,
        query: str,
        context_results: Sequence[SemanticSearchResult],
        system_prompt: str,
        user_prompt: str,
    ) -> str:
        del system_prompt, user_prompt

        unique_snippets: list[str] = []
        seen_snippets: set[str] = set()
        for result in context_results:
            snippet = _trim_snippet(result.content)
            if snippet and snippet not in seen_snippets:
                unique_snippets.append(snippet)
                seen_snippets.add(snippet)
            if len(unique_snippets) == 1:
                break

        if not unique_snippets:
            raise LlmProviderError(
                "El proveedor mock no recibió contexto para construir la respuesta."
            )

        answer = (
            "Según la documentación cargada, "
            + ". ".join(unique_snippets)
            + "."
        )
        logger.info(
            "Respuesta mock generada: consulta=%s fragmentos=%s",
            query,
            len(unique_snippets),
        )
        return answer


class OpenAiLlmService:
    provider = "openai"

    def __init__(
        self,
        app_settings: Settings = settings,
        client: OpenAI | None = None,
    ) -> None:
        self.settings = app_settings
        self.model = app_settings.openai_chat_model
        self._client = client

    def _get_client(self) -> OpenAI:
        if self._client is not None:
            return self._client

        secret = self.settings.openai_api_key
        api_key = secret.get_secret_value().strip() if secret else ""
        if not api_key:
            raise LlmConfigurationError(
                "OPENAI_API_KEY no está configurada en el entorno."
            )

        self._client = OpenAI(
            api_key=api_key,
            timeout=self.settings.llm_timeout_seconds,
            max_retries=self.settings.llm_max_retries,
        )
        return self._client

    def generate_answer(
        self,
        query: str,
        context_results: Sequence[SemanticSearchResult],
        system_prompt: str,
        user_prompt: str,
    ) -> str:
        del query, context_results

        try:
            response = self._get_client().chat.completions.create(
                model=self.model,
                temperature=0,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
            )
        except AuthenticationError as exc:
            raise LlmConfigurationError(
                "OpenAI rechazó la credencial configurada para el LLM."
            ) from exc
        except RateLimitError as exc:
            raise LlmProviderError(
                "OpenAI alcanzó el límite de solicitudes o cuota disponible para el LLM."
            ) from exc
        except (APITimeoutError, APIConnectionError) as exc:
            raise LlmProviderError(
                "No fue posible conectar con el servicio LLM de OpenAI."
            ) from exc
        except APIStatusError as exc:
            raise LlmProviderError(
                f"OpenAI respondió con un error HTTP {exc.status_code}."
            ) from exc

        answer = (response.choices[0].message.content or "").strip()
        if not answer:
            raise LlmProviderError("OpenAI devolvió una respuesta vacía.")

        logger.info("Respuesta OpenAI generada: modelo=%s", self.model)
        return answer


class OllamaLlmService:
    provider = "ollama"

    def __init__(
        self,
        app_settings: Settings = settings,
        client: httpx.Client | None = None,
    ) -> None:
        self.settings = app_settings
        self.model = app_settings.ollama_model
        self.base_url = _normalize_ollama_base_url(app_settings.ollama_base_url)
        self._client = client

    def _get_client(self) -> httpx.Client:
        if self._client is None:
            self._client = httpx.Client(timeout=self.settings.llm_timeout_seconds)
        return self._client

    def generate_answer(
        self,
        query: str,
        context_results: Sequence[SemanticSearchResult],
        system_prompt: str,
        user_prompt: str,
    ) -> str:
        del query, context_results

        if not self.model.strip():
            raise LlmConfigurationError("OLLAMA_MODEL no está configurado.")

        try:
            response = self._get_client().post(
                f"{self.base_url}/chat",
                json={
                    "model": self.model,
                    "stream": False,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                },
            )
            response.raise_for_status()
        except httpx.ConnectError as exc:
            raise LlmProviderError(
                "No fue posible conectar con Ollama. Verifica que esté iniciado y accesible."
            ) from exc
        except httpx.TimeoutException as exc:
            raise LlmProviderError(
                "Ollama tardó demasiado en responder."
            ) from exc
        except httpx.HTTPStatusError as exc:
            status_code = exc.response.status_code
            detail = exc.response.text.strip()
            if status_code == 404:
                raise LlmProviderError(
                    f"Ollama no encontró el modelo '{self.model}'. Descárgalo antes de usarlo."
                ) from exc
            raise LlmProviderError(
                f"Ollama respondió con un error HTTP {status_code}: {detail or 'sin detalle'}"
            ) from exc
        except httpx.HTTPError as exc:
            raise LlmProviderError(
                "Ocurrió un error inesperado al consultar Ollama."
            ) from exc

        payload = response.json()
        message = payload.get("message") or {}
        answer = str(message.get("content") or "").strip()
        if not answer:
            raise LlmProviderError("Ollama devolvió una respuesta vacía.")

        logger.info("Respuesta Ollama generada: modelo=%s", self.model)
        return answer


def get_llm_service(app_settings: Settings = settings) -> LlmService:
    if app_settings.llm_provider == "mock":
        return MockLlmService()
    if app_settings.llm_provider == "ollama":
        return OllamaLlmService(app_settings)
    if app_settings.llm_provider == "openai":
        return OpenAiLlmService(app_settings)
    raise LlmConfigurationError(
        f"Proveedor LLM no soportado: {app_settings.llm_provider}"
    )
