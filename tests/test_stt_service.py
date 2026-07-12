import pytest

from app.services.stt_service import (
    MockSttService,
    SttProviderError,
    get_stt_service,
)
from app.config.settings import settings


def test_mock_stt_uses_transcript_hint() -> None:
    service = MockSttService()

    transcript = service.transcribe(
        audio_bytes=b"audio",
        filename="grabacion.wav",
        content_type="audio/wav",
        transcript_hint="  como procesa el sistema los pdf  ",
    )

    assert transcript == "como procesa el sistema los pdf"


def test_mock_stt_uses_filename_when_hint_missing() -> None:
    service = MockSttService()

    transcript = service.transcribe(
        audio_bytes=b"audio",
        filename="consulta_sobre_documentos-pdf.wav",
        content_type="audio/wav",
    )

    assert transcript == "consulta sobre documentos pdf"


def test_mock_stt_rejects_unreadable_input() -> None:
    service = MockSttService()

    with pytest.raises(SttProviderError):
        service.transcribe(
            audio_bytes=b"audio",
            filename="---.wav",
            content_type="audio/wav",
        )


def test_factory_caches_default_stt_service() -> None:
    first = get_stt_service(settings)
    second = get_stt_service(settings)

    assert first is second
