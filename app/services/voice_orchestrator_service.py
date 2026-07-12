import logging
import time
from base64 import b64encode
from dataclasses import dataclass

from app.config.settings import Settings, settings
from app.schemas.audio import AudioInteractionDebugResponse
from app.services.alert_service import classify_confidence
from app.services.orchestrator_service import OrchestratorService
from app.services.stt_service import SttService, get_stt_service
from app.services.tts_service import TtsService, get_tts_service

logger = logging.getLogger("uvicorn.error")


@dataclass
class VoiceInteractionResult:
    transcript: str
    answer: str
    audio_bytes: bytes
    output_filename: str
    output_content_type: str
    status: str
    llm_provider: str
    llm_model: str
    total_sources: int
    confidence_label: str
    top_score: float | None
    latency_total_ms: float
    latency_stt_ms: float
    latency_rag_ms: float
    latency_llm_ms: float
    latency_tts_ms: float
    transcript_base64: str
    answer_base64: str


class VoiceOrchestratorService:
    def __init__(
        self,
        stt_service: SttService | None = None,
        tts_service: TtsService | None = None,
        orchestrator_service: OrchestratorService | None = None,
        app_settings: Settings = settings,
    ) -> None:
        self.settings = app_settings
        self.stt_service = stt_service or get_stt_service(app_settings)
        self.tts_service = tts_service or get_tts_service(app_settings)
        self.orchestrator_service = orchestrator_service or OrchestratorService(
            app_settings=app_settings
        )

    def interact(
        self,
        audio_bytes: bytes,
        filename: str,
        content_type: str,
        top_k: int = 3,
        transcript_hint: str | None = None,
    ) -> VoiceInteractionResult:
        total_started_at = time.perf_counter()
        stt_started_at = time.perf_counter()
        transcript = self.stt_service.transcribe(
            audio_bytes=audio_bytes,
            filename=filename,
            content_type=content_type,
            transcript_hint=transcript_hint,
        )
        latency_stt_ms = (time.perf_counter() - stt_started_at) * 1000
        orchestrated_trace = self.orchestrator_service.respond_with_trace(transcript, top_k)
        orchestrated = orchestrated_trace.response
        tts_started_at = time.perf_counter()
        response_audio = self.tts_service.synthesize(orchestrated.answer)
        latency_tts_ms = (time.perf_counter() - tts_started_at) * 1000
        latency_total_ms = (time.perf_counter() - total_started_at) * 1000
        confidence_label = classify_confidence(
            status=orchestrated.status,
            top_score=orchestrated_trace.top_score,
            app_settings=self.settings,
        )

        logger.info(
            "Flujo de voz completado: audio_entrada=%s texto=%s proveedor_stt=%s proveedor_tts=%s estado=%s",
            filename,
            transcript,
            self.stt_service.provider,
            self.tts_service.provider,
            orchestrated.status,
        )
        return VoiceInteractionResult(
            transcript=transcript,
            answer=orchestrated.answer,
            audio_bytes=response_audio,
            output_filename="respuesta-voz.wav",
            output_content_type=self.tts_service.output_content_type,
            status=orchestrated.status,
            llm_provider=orchestrated.llm_provider,
            llm_model=orchestrated.llm_model,
            total_sources=orchestrated.total_sources,
            confidence_label=confidence_label,
            top_score=orchestrated_trace.top_score,
            latency_total_ms=round(latency_total_ms, 2),
            latency_stt_ms=round(latency_stt_ms, 2),
            latency_rag_ms=orchestrated_trace.rag_latency_ms,
            latency_llm_ms=orchestrated_trace.llm_latency_ms,
            latency_tts_ms=round(latency_tts_ms, 2),
            transcript_base64=b64encode(transcript.encode("utf-8")).decode("ascii"),
            answer_base64=b64encode(orchestrated.answer.encode("utf-8")).decode("ascii"),
        )

    def build_debug_response(
        self,
        result: VoiceInteractionResult,
        filename: str,
        content_type: str,
    ) -> AudioInteractionDebugResponse:
        return AudioInteractionDebugResponse(
            input_filename=filename,
            input_content_type=content_type,
            output_filename=result.output_filename,
            output_content_type=result.output_content_type,
            transcript=result.transcript,
            answer=result.answer,
            stt_provider=self.stt_service.provider,
            tts_provider=self.tts_service.provider,
            llm_provider=result.llm_provider,
            llm_model=result.llm_model,
            status=result.status,
            audio_size_bytes=len(result.audio_bytes),
            transcript_base64=result.transcript_base64,
            answer_base64=result.answer_base64,
            total_sources=result.total_sources,
            confidence_label=result.confidence_label,
            top_score=result.top_score,
            latency_total_ms=result.latency_total_ms,
            latency_stt_ms=result.latency_stt_ms,
            latency_rag_ms=result.latency_rag_ms,
            latency_llm_ms=result.latency_llm_ms,
            latency_tts_ms=result.latency_tts_ms,
        )
