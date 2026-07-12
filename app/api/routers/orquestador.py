from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.api.deps import require_user
from app.schemas.orchestrator import OrchestratorRequest, OrchestratorResponse
from app.services.audit_service import AuditService
from app.services.embedding_service import (
    EmbeddingConfigurationError,
    EmbeddingProviderError,
)
from app.services.llm_service import LlmConfigurationError, LlmProviderError
from app.services.orchestrator_service import OrchestratorService
from app.services.vector_store_service import (
    EmptyVectorStoreError,
    VectorStoreUnavailableError,
)

router = APIRouter(prefix="/orquestador", tags=["Orquestador"])


def get_orchestrator_service() -> OrchestratorService:
    return OrchestratorService()


@router.post(
    "/responder",
    response_model=OrchestratorResponse,
    status_code=status.HTTP_200_OK,
)
async def answer_query(
    request_context: Request,
    request: OrchestratorRequest,
    _: object = Depends(require_user),
    orchestrator_service: OrchestratorService = Depends(get_orchestrator_service),
) -> OrchestratorResponse:
    audit_service = AuditService()

    try:
        trace = orchestrator_service.respond_with_trace(request.query, request.top_k)
        audit_service.enrich_request(
            request_context,
            interaction_type="orchestrator",
            user_query=request.query,
            response_text=trace.response.answer,
            status=trace.response.status,
            total_sources=trace.response.total_sources,
            top_score=trace.top_score,
            latency_rag_ms=trace.rag_latency_ms,
            latency_llm_ms=trace.llm_latency_ms,
            metadata={
                "collection": trace.response.collection,
                "llm_provider": trace.response.llm_provider,
                "llm_model": trace.response.llm_model,
            },
        )
        return trace.response
    except EmptyVectorStoreError as exc:
        audit_service.enrich_request(
            request_context,
            interaction_type="orchestrator",
            user_query=request.query,
            status="failed",
            error_message=str(exc),
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except (EmbeddingConfigurationError, LlmConfigurationError) as exc:
        audit_service.enrich_request(
            request_context,
            interaction_type="orchestrator",
            user_query=request.query,
            status="failed",
            error_message=str(exc),
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    except (EmbeddingProviderError, LlmProviderError) as exc:
        audit_service.enrich_request(
            request_context,
            interaction_type="orchestrator",
            user_query=request.query,
            status="failed",
            error_message=str(exc),
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc
    except VectorStoreUnavailableError as exc:
        audit_service.enrich_request(
            request_context,
            interaction_type="orchestrator",
            user_query=request.query,
            status="failed",
            error_message=str(exc),
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
