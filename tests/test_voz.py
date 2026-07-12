import io
import wave

import pytest
from fastapi.testclient import TestClient

from app.api.routers.voz import get_voice_orchestrator_service
from app.main import app
from app.services.voice_orchestrator_service import VoiceInteractionResult


def build_wav_bytes() -> bytes:
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(16000)
        wav_file.writeframes(b"\x00\x00" * 8000)
    return buffer.getvalue()


class FakeVoiceOrchestratorService:
    def interact(
        self,
        audio_bytes: bytes,
        filename: str,
        content_type: str,
        top_k: int = 3,
        transcript_hint: str | None = None,
    ) -> VoiceInteractionResult:
        assert audio_bytes
        assert filename == "entrada.wav"
        assert content_type == "audio/wav"
        assert top_k == 3
        return VoiceInteractionResult(
            transcript=transcript_hint or "consulta de audio",
            answer="Respuesta desde voz",
            audio_bytes=b"RIFFmock-audio",
            output_filename="respuesta-voz.wav",
            output_content_type="audio/wav",
            status="answered",
            llm_provider="mock",
            llm_model="mock-rag-responder-v1",
            total_sources=1,
        )

    def build_debug_response(
        self,
        result: VoiceInteractionResult,
        filename: str,
        content_type: str,
    ):
        from app.schemas.audio import AudioInteractionDebugResponse

        return AudioInteractionDebugResponse(
            input_filename=filename,
            input_content_type=content_type,
            output_filename=result.output_filename,
            output_content_type=result.output_content_type,
            transcript=result.transcript,
            answer=result.answer,
            stt_provider="mock",
            tts_provider="mock",
            llm_provider=result.llm_provider,
            llm_model=result.llm_model,
            status=result.status,
            audio_size_bytes=len(result.audio_bytes),
            total_sources=result.total_sources,
        )


client = TestClient(app)


@pytest.fixture(autouse=True)
def override_voice_service() -> None:
    app.dependency_overrides[get_voice_orchestrator_service] = FakeVoiceOrchestratorService
    yield
    app.dependency_overrides.pop(get_voice_orchestrator_service, None)


def test_voice_debug_endpoint_returns_metadata() -> None:
    response = client.post(
        "/voz/interactuar-debug?top_k=3",
        files={"file": ("entrada.wav", build_wav_bytes(), "audio/wav")},
        data={"transcript_hint": "consulta de audio"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["transcript"] == "consulta de audio"
    assert payload["answer"] == "Respuesta desde voz"


def test_voice_audio_endpoint_returns_wav() -> None:
    response = client.post(
        "/voz/interactuar?top_k=3",
        files={"file": ("entrada.wav", build_wav_bytes(), "audio/wav")},
        data={"transcript_hint": "consulta de audio"},
    )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("audio/wav")
    assert response.content == b"RIFFmock-audio"


def test_voice_endpoint_rejects_invalid_content_type() -> None:
    response = client.post(
        "/voz/interactuar-debug?top_k=3",
        files={"file": ("entrada.txt", b"texto", "text/plain")},
    )

    assert response.status_code == 415
