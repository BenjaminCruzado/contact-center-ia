from app.schemas.orchestrator import OrchestratorResponse, OrchestratorTrace
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
        return self.respond_with_trace(query, top_k).response

    def respond_with_trace(self, query: str, top_k: int) -> OrchestratorTrace:
        assert query
        assert top_k == 3
        return OrchestratorTrace(
            response=OrchestratorResponse(
                query=query,
                status="answered",
                answer="Respuesta textual",
                collection="test-collection",
                llm_provider="mock",
                llm_model="mock-rag-responder-v1",
                llm_invoked=True,
                total_sources=2,
                sources=[],
            ),
            rag_latency_ms=18.0,
            llm_latency_ms=32.0,
            total_latency_ms=50.0,
            top_score=0.88,
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
    assert result.confidence_label == "ok"
    assert result.top_score == 0.88
