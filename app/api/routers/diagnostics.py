from fastapi import APIRouter, status

from app.config.settings import settings

router = APIRouter(tags=["Diagnóstico"])


@router.get("/health", status_code=status.HTTP_200_OK)
@router.get("/healthcheck", status_code=status.HTTP_200_OK, include_in_schema=False)
async def healthcheck() -> dict[str, str]:
    return {
        "status": "active",
        "service": settings.app_name,
        "environment": settings.app_env,
    }


@router.get("/version", status_code=status.HTTP_200_OK)
async def version() -> dict[str, str]:
    return {
        "service": settings.app_name,
        "version": settings.app_version,
    }

