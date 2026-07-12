from fastapi import FastAPI

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
    application.add_middleware(AuditMiddleware)
    application.include_router(api_router)
    return application


app = create_application()
