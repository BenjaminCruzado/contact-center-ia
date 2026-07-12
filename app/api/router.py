from fastapi import APIRouter

from app.api.routers import auth, auditoria, diagnostics, documentos, orquestador, voz

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(diagnostics.router)
api_router.include_router(documentos.router)
api_router.include_router(orquestador.router)
api_router.include_router(voz.router)
api_router.include_router(auditoria.router)
