import logging
from dataclasses import dataclass

from app.config.settings import Settings, settings
from app.schemas.audio import AudioInteractionDebugResponse
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
        transcript = self.stt_service.transcribe(
            audio_bytes=audio_bytes,
            filename=filename,
            content_type=content_type,
            transcript_hint=transcript_hint,
        )
        orchestrated = self.orchestrator_service.respond(transcript, top_k)
        response_audio = self.tts_service.synthesize(orchestrated.answer)

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
            total_sources=result.total_sources,
        )
