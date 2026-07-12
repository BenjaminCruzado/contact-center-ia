from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.config.settings import Settings
from app.db.audit_db import AuditDatabase
from app.middleware.audit_middleware import AuditMiddleware
from app.services.audit_service import AuditService


def test_audit_middleware_adds_headers_and_persists(tmp_path) -> None:
    local_settings = Settings(audit_db_path=str(tmp_path / "audit.db"))
    audit_service = AuditService(AuditDatabase(local_settings), local_settings)
    audit_service.initialize()

    test_app = FastAPI()
    test_app.add_middleware(AuditMiddleware, audit_service=audit_service)

    @test_app.get("/ping")
    async def ping():
        return {"status": "ok"}

    client = TestClient(test_app)

    response = client.get("/ping")

    assert response.status_code == 200
    assert "X-Request-Id" in response.headers
    assert "X-Process-Time-Ms" in response.headers
    summary = audit_service.summarize()
    assert summary["total_records"] == 1
