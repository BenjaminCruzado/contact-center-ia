from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.config.settings import settings
from app.middleware.audit_middleware import AuditMiddleware
from app.services.audit_service import AuditService


def create_application() -> FastAPI:
    application = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        debug=settings.app_debug,
        description="Core API del prototipo de Contact Center automatizado.",
    )
    AuditService().initialize()
    application.add_middleware(
        CORSMiddleware,
        allow_origins=[settings.frontend_url],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=[
            "X-Request-Id",
            "X-Process-Time-Ms",
            "X-Transcript",
            "X-Voice-Status",
            "X-LLM-Provider",
            "X-Voice-Latency-Ms",
            "X-Transcript-B64",
            "X-Answer-B64",
        ],
    )
    application.add_middleware(AuditMiddleware)
    application.include_router(api_router)
    return application


app = create_application()
