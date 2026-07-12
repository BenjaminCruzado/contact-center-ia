from functools import lru_cache

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    Request,
    UploadFile,
    status,
)
from fastapi.responses import StreamingResponse

from app.api.deps import require_user
from app.config.settings import settings
from app.schemas.audio import AudioInteractionDebugResponse
from app.services.audit_service import AuditService
from app.services.embedding_service import (
    EmbeddingConfigurationError,
    EmbeddingProviderError,
)
from app.services.llm_service import LlmConfigurationError, LlmProviderError
from app.services.stt_service import (
    SttConfigurationError,
    SttProviderError,
)
from app.services.tts_service import (
    TtsConfigurationError,
    TtsProviderError,
)
from app.services.vector_store_service import (
    EmptyVectorStoreError,
    VectorStoreUnavailableError,
)
from app.services.voice_orchestrator_service import VoiceOrchestratorService

router = APIRouter(prefix="/voz", tags=["Voz"])

AUDIO_CONTENT_TYPES = {
    "audio/wav",
    "audio/x-wav",
    "audio/mpeg",
    "audio/mp3",
    "audio/mp4",
    "audio/m4a",
    "audio/webm",
    "audio/ogg",
}


@lru_cache(maxsize=1)
def get_voice_orchestrator_service() -> VoiceOrchestratorService:
    return VoiceOrchestratorService()


def _handle_voice_error(exc: Exception) -> HTTPException:
    if isinstance(exc, EmptyVectorStoreError):
        return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    if isinstance(
        exc,
        (
            EmbeddingConfigurationError,
            LlmConfigurationError,
            SttConfigurationError,
            TtsConfigurationError,
        ),
    ):
        return HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        )
    if isinstance(
        exc,
        (
            EmbeddingProviderError,
            LlmProviderError,
            SttProviderError,
            TtsProviderError,
        ),
    ):
        return HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        )
    if isinstance(exc, VectorStoreUnavailableError):
        return HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        )
    raise exc


async def _read_audio_upload(file: UploadFile) -> tuple[str, str, bytes]:
    filename = file.filename or "audio.wav"
    content_type = (file.content_type or "").lower()
    audio_bytes = await file.read(settings.audio_max_file_size_bytes + 1)
    await file.close()

    if not audio_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El archivo de audio está vacío.",
        )
    if len(audio_bytes) > settings.audio_max_file_size_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="El archivo de audio supera el límite configurado.",
        )
    if content_type not in AUDIO_CONTENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="El archivo de audio no posee un tipo MIME soportado.",
        )
    return filename, content_type, audio_bytes


@router.post("/interactuar", status_code=status.HTTP_200_OK)
async def interact_with_voice(
    request_context: Request,
    file: UploadFile = File(..., description="Audio grabado por el usuario."),
    top_k: int = Query(default=3, ge=1, le=10),
    transcript_hint: str | None = Form(default=None),
    _: object = Depends(require_user),
    voice_service: VoiceOrchestratorService = Depends(get_voice_orchestrator_service),
) -> StreamingResponse:
    audit_service = AuditService()
    filename, content_type, audio_bytes = await _read_audio_upload(file)

    try:
        result = voice_service.interact(
            audio_bytes=audio_bytes,
            filename=filename,
            content_type=content_type,
            top_k=top_k,
            transcript_hint=transcript_hint,
        )
    except Exception as exc:
        audit_service.enrich_request(
            request_context,
            interaction_type="voice",
            status="failed",
            error_message=str(exc),
            metadata={"input_filename": filename, "input_content_type": content_type},
        )
        raise _handle_voice_error(exc) from exc

    stt_provider = getattr(getattr(voice_service, "stt_service", None), "provider", "unknown")
    tts_provider = getattr(getattr(voice_service, "tts_service", None), "provider", "unknown")

    audit_service.enrich_request(
        request_context,
        interaction_type="voice",
        user_query=result.transcript,
        transcript=result.transcript,
        response_text=result.answer,
        status=result.status,
        top_score=result.top_score,
        total_sources=result.total_sources,
        latency_stt_ms=result.latency_stt_ms,
        latency_rag_ms=result.latency_rag_ms,
        latency_llm_ms=result.latency_llm_ms,
        latency_tts_ms=result.latency_tts_ms,
        metadata={
            "input_filename": filename,
            "input_content_type": content_type,
            "output_filename": result.output_filename,
            "output_content_type": result.output_content_type,
            "stt_provider": stt_provider,
            "tts_provider": tts_provider,
            "llm_provider": result.llm_provider,
            "llm_model": result.llm_model,
        },
    )

    headers = {
        "X-Transcript": result.transcript,
        "X-Voice-Status": result.status,
        "X-LLM-Provider": result.llm_provider,
        "X-Voice-Latency-Ms": f"{result.latency_total_ms:.2f}",
        "X-Transcript-B64": result.transcript_base64,
        "X-Answer-B64": result.answer_base64,
    }
    return StreamingResponse(
        iter([result.audio_bytes]),
        media_type=result.output_content_type,
        headers=headers,
    )


@router.post(
    "/interactuar-debug",
    response_model=AudioInteractionDebugResponse,
    status_code=status.HTTP_200_OK,
)
async def interact_with_voice_debug(
    request_context: Request,
    file: UploadFile = File(..., description="Audio grabado por el usuario."),
    top_k: int = Query(default=3, ge=1, le=10),
    transcript_hint: str | None = Form(default=None),
    _: object = Depends(require_user),
    voice_service: VoiceOrchestratorService = Depends(get_voice_orchestrator_service),
) -> AudioInteractionDebugResponse:
    audit_service = AuditService()
    filename, content_type, audio_bytes = await _read_audio_upload(file)

    try:
        result = voice_service.interact(
            audio_bytes=audio_bytes,
            filename=filename,
            content_type=content_type,
            top_k=top_k,
            transcript_hint=transcript_hint,
        )
        stt_provider = getattr(getattr(voice_service, "stt_service", None), "provider", "unknown")
        tts_provider = getattr(getattr(voice_service, "tts_service", None), "provider", "unknown")
        audit_service.enrich_request(
            request_context,
            interaction_type="voice",
            user_query=result.transcript,
            transcript=result.transcript,
            response_text=result.answer,
            status=result.status,
            top_score=result.top_score,
            total_sources=result.total_sources,
            latency_stt_ms=result.latency_stt_ms,
            latency_rag_ms=result.latency_rag_ms,
            latency_llm_ms=result.latency_llm_ms,
            latency_tts_ms=result.latency_tts_ms,
            metadata={
                "input_filename": filename,
                "input_content_type": content_type,
                "output_filename": result.output_filename,
                "output_content_type": result.output_content_type,
                "stt_provider": stt_provider,
                "tts_provider": tts_provider,
                "llm_provider": result.llm_provider,
                "llm_model": result.llm_model,
            },
        )
        return voice_service.build_debug_response(result, filename, content_type)
    except Exception as exc:
        audit_service.enrich_request(
            request_context,
            interaction_type="voice",
            status="failed",
            error_message=str(exc),
            metadata={"input_filename": filename, "input_content_type": content_type},
        )
        raise _handle_voice_error(exc) from exc
