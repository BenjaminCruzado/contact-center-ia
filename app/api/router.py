from fastapi import APIRouter

from app.api.routers import diagnostics, documentos

api_router = APIRouter()
api_router.include_router(diagnostics.router)
api_router.include_router(documentos.router)

