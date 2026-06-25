from fastapi import APIRouter

from app.api.routers import diagnostics

api_router = APIRouter()
api_router.include_router(diagnostics.router)

