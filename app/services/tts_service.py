import io
import logging
import math
import struct
import subprocess
import tempfile
import wave
from pathlib import Path
from typing import Protocol

from app.config.settings import Settings, settings

logger = logging.getLogger("uvicorn.error")


class TtsServiceError(RuntimeError):
    """Error controlado del proveedor TTS."""


class TtsConfigurationError(TtsServiceError):
    """El proveedor TTS no posee configuración válida."""


class TtsProviderError(TtsServiceError):
    """El proveedor TTS no pudo generar audio."""


class TtsService(Protocol):
    provider: str
    output_content_type: str

    def synthesize(self, text: str) -> bytes: ...


def _generate_tone_wav(duration_seconds: float = 0.8) -> bytes:
    sample_rate = 16_000
    total_samples = int(sample_rate * duration_seconds)
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        for index in range(total_samples):
            amplitude = int(
                12_000 * math.sin(2 * math.pi * 440 * (index / sample_rate))
            )
            wav_file.writeframesraw(struct.pack("<h", amplitude))
    return buffer.getvalue()


class MockTtsService:
    provider = "mock"
    output_content_type = "audio/wav"

    def synthesize(self, text: str) -> bytes:
        if not text.strip():
            raise TtsProviderError("El texto a sintetizar no puede estar vacío.")
        logger.info("Audio mock generado: caracteres=%s", len(text.strip()))
        return _generate_tone_wav()


class LocalEspeakTtsService:
    provider = "local"
    output_content_type = "audio/wav"

    def __init__(self, app_settings: Settings = settings) -> None:
        self.settings = app_settings

    def synthesize(self, text: str) -> bytes:
        clean_text = " ".join(text.split()).strip()
        if not clean_text:
            raise TtsProviderError("El texto a sintetizar no puede estar vacío.")

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
            output_path = temp_file.name

        try:
            result = subprocess.run(
                [
                    "espeak-ng",
                    "-v",
                    self.settings.tts_voice,
                    "-w",
                    output_path,
                    clean_text,
                ],
                check=False,
                capture_output=True,
                text=True,
            )
            if result.returncode != 0:
                raise TtsProviderError(
                    "espeak-ng no pudo sintetizar el audio solicitado."
                )
            audio_bytes = Path(output_path).read_bytes()
        except TtsProviderError:
            raise
        except Exception as exc:
            raise TtsProviderError(
                "No fue posible generar audio local con espeak-ng."
            ) from exc
        finally:
            Path(output_path).unlink(missing_ok=True)

        logger.info(
            "Audio sintetizado: proveedor=%s voz=%s bytes=%s",
            self.provider,
            self.settings.tts_voice,
            len(audio_bytes),
        )
        return audio_bytes


def get_tts_service(app_settings: Settings = settings) -> TtsService:
    if app_settings.tts_provider == "mock":
        return MockTtsService()
    if app_settings.tts_provider == "local":
        return LocalEspeakTtsService(app_settings)
    raise TtsConfigurationError(
        f"Proveedor TTS no soportado: {app_settings.tts_provider}"
    )
