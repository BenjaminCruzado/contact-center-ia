import logging
import re
import tempfile
from collections.abc import Sequence
from functools import lru_cache
from pathlib import Path
from typing import Any, Protocol

from app.config.settings import Settings, settings

logger = logging.getLogger("uvicorn.error")


class SttServiceError(RuntimeError):
    """Error controlado del proveedor STT."""


class SttConfigurationError(SttServiceError):
    """El proveedor STT no posee configuración válida."""


class SttProviderError(SttServiceError):
    """El proveedor STT no pudo transcribir el audio."""


class SttService(Protocol):
    provider: str

    def transcribe(
        self,
        audio_bytes: bytes,
        filename: str,
        content_type: str,
        transcript_hint: str | None = None,
    ) -> str: ...


def _normalize_transcript(value: str) -> str:
    clean_value = " ".join(value.split())
    return clean_value.strip(" .")


class MockSttService:
    provider = "mock"

    def transcribe(
        self,
        audio_bytes: bytes,
        filename: str,
        content_type: str,
        transcript_hint: str | None = None,
    ) -> str:
        del audio_bytes, content_type

        if transcript_hint:
            transcript = _normalize_transcript(transcript_hint)
        else:
            stem = Path(filename).stem
            transcript = _normalize_transcript(
                re.sub(r"[_\-]+", " ", stem)
            )

        if not transcript:
            raise SttProviderError(
                "El proveedor mock requiere transcript_hint o un nombre de archivo interpretable."
            )

        logger.info("Transcripción mock generada: texto=%s", transcript)
        return transcript


class LocalWhisperSttService:
    provider = "local"

    def __init__(
        self,
        app_settings: Settings = settings,
        model_instance: Any | None = None,
    ) -> None:
        self.settings = app_settings
        self._model_instance = model_instance

    def _get_model(self) -> Any:
        if self._model_instance is None:
            try:
                import whisper

                logger.info(
                    "Cargando modelo Whisper local: modelo=%s idioma=%s",
                    self.settings.whisper_model,
                    self.settings.whisper_language,
                )
                self._model_instance = whisper.load_model(
                    self.settings.whisper_model,
                    download_root=self.settings.whisper_cache_dir,
                )
            except Exception as exc:
                raise SttProviderError(
                    "No fue posible cargar el modelo local de transcripción."
                ) from exc
        return self._model_instance

    def transcribe(
        self,
        audio_bytes: bytes,
        filename: str,
        content_type: str,
        transcript_hint: str | None = None,
    ) -> str:
        del transcript_hint, content_type

        suffix = Path(filename).suffix or ".wav"
        temp_path = ""
        try:
            with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as temp_file:
                temp_file.write(audio_bytes)
                temp_path = temp_file.name

            result = self._get_model().transcribe(
                temp_path,
                language=self.settings.whisper_language,
                fp16=False,
                verbose=False,
            )
            transcript = _normalize_transcript(str(result.get("text", "")))
        except Exception as exc:
            raise SttProviderError(
                "El modelo local no pudo transcribir el audio."
            ) from exc
        finally:
            try:
                Path(temp_path).unlink(missing_ok=True)
            except Exception:
                pass

        if not transcript:
            raise SttProviderError("La transcripción resultó vacía.")

        logger.info("Audio transcrito: proveedor=%s texto=%s", self.provider, transcript)
        return transcript


def get_stt_service(app_settings: Settings = settings) -> SttService:
    if app_settings is settings:
        if app_settings.stt_provider == "mock":
            return _get_cached_mock_stt_service()
        if app_settings.stt_provider == "local":
            return _get_cached_local_whisper_stt_service()
    else:
        if app_settings.stt_provider == "mock":
            return MockSttService()
        if app_settings.stt_provider == "local":
            return LocalWhisperSttService(app_settings)
    raise SttConfigurationError(
        f"Proveedor STT no soportado: {app_settings.stt_provider}"
    )


@lru_cache(maxsize=1)
def _get_cached_mock_stt_service() -> MockSttService:
    return MockSttService()


@lru_cache(maxsize=1)
def _get_cached_local_whisper_stt_service() -> LocalWhisperSttService:
    return LocalWhisperSttService(settings)
