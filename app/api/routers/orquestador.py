from fastapi import APIRouter, Depends, HTTPException, status

from app.schemas.orchestrator import OrchestratorRequest, OrchestratorResponse
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
    request: OrchestratorRequest,
    orchestrator_service: OrchestratorService = Depends(get_orchestrator_service),
) -> OrchestratorResponse:
    try:
        return orchestrator_service.respond(request.query, request.top_k)
    except EmptyVectorStoreError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except (EmbeddingConfigurationError, LlmConfigurationError) as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    except (EmbeddingProviderError, LlmProviderError) as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc
    except VectorStoreUnavailableError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
