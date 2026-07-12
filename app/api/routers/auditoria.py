from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.deps import require_admin
from app.schemas.audit import AuditLogResponse, AuditSummaryResponse
from app.services.audit_service import AuditService

router = APIRouter(prefix="/auditoria", tags=["Auditoría"])


@router.get(
    "/registros",
    response_model=list[AuditLogResponse],
    status_code=status.HTTP_200_OK,
)
async def list_audit_logs(
    limit: int = Query(default=20, ge=1, le=200),
    interaction_type: str | None = Query(default=None),
    endpoint: str | None = Query(default=None),
    _: object = Depends(require_admin),
) -> list[AuditLogResponse]:
    return [
        AuditLogResponse.model_validate(item)
        for item in AuditService().list_logs(
            limit,
            interaction_type=interaction_type,
            endpoint=endpoint,
        )
    ]


@router.get(
    "/registros/{log_id}",
    response_model=AuditLogResponse,
    status_code=status.HTTP_200_OK,
)
async def get_audit_log(
    log_id: int,
    _: object = Depends(require_admin),
) -> AuditLogResponse:
    log_item = AuditService().get_log(log_id)
    if log_item is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No se encontró el registro de auditoría solicitado.",
        )
    return AuditLogResponse.model_validate(log_item)


@router.get(
    "/resumen",
    response_model=AuditSummaryResponse,
    status_code=status.HTTP_200_OK,
)
async def get_audit_summary(
    _: object = Depends(require_admin),
) -> AuditSummaryResponse:
    return AuditSummaryResponse.model_validate(AuditService().summarize())
