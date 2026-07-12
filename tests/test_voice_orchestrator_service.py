from app.schemas.orchestrator import OrchestratorResponse
from app.services.voice_orchestrator_service import VoiceOrchestratorService


class FakeSttService:
    provider = "mock"

    def transcribe(
        self,
        audio_bytes: bytes,
        filename: str,
        content_type: str,
        transcript_hint: str | None = None,
    ) -> str:
        assert audio_bytes
        assert filename
        assert content_type
        return transcript_hint or "consulta de audio"


class FakeTtsService:
    provider = "mock"
    output_content_type = "audio/wav"

    def synthesize(self, text: str) -> bytes:
        assert text
        return b"RIFFmock-audio"


class FakeTextOrchestratorService:
    def respond(self, query: str, top_k: int) -> OrchestratorResponse:
        assert query
        assert top_k == 3
        return OrchestratorResponse(
            query=query,
            status="answered",
            answer="Respuesta textual",
            collection="test-collection",
            llm_provider="mock",
            llm_model="mock-rag-responder-v1",
            llm_invoked=True,
            total_sources=2,
            sources=[],
        )


def test_voice_orchestrator_returns_audio_and_metadata() -> None:
    service = VoiceOrchestratorService(
        stt_service=FakeSttService(),
        tts_service=FakeTtsService(),
        orchestrator_service=FakeTextOrchestratorService(),
    )

    result = service.interact(
        audio_bytes=b"audio",
        filename="entrada.wav",
        content_type="audio/wav",
        transcript_hint="consulta de audio",
    )

    assert result.transcript == "consulta de audio"
    assert result.answer == "Respuesta textual"
    assert result.audio_bytes == b"RIFFmock-audio"
    assert result.total_sources == 2
