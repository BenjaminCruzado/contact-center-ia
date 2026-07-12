from fastapi.testclient import TestClient

from app.main import app
from app.services.audit_service import AuditService
from tests.auth_helpers import make_auth_header

client = TestClient(app)


def test_auditoria_summary_endpoint_returns_metrics() -> None:
    response = client.get("/auditoria/resumen", headers=make_auth_header("admin"))

    assert response.status_code == 200
    payload = response.json()
    assert "total_records" in payload
    assert "average_latency_ms" in payload


def test_auditoria_records_endpoint_returns_list() -> None:
    response = client.get(
        "/auditoria/registros?limit=5",
        headers=make_auth_header("admin"),
    )

    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_auditoria_detail_returns_404_for_missing_record() -> None:
    response = client.get(
        "/auditoria/registros/999999",
        headers=make_auth_header("admin"),
    )

    assert response.status_code == 404


def test_auditoria_captures_orchestrator_request() -> None:
    service = AuditService()
    before_total = service.summarize()["total_records"]

    response = client.post(
        "/orquestador/responder",
        json={"query": "¿Qué hace el sistema?", "top_k": 3},
        headers=make_auth_header("user"),
    )

    assert response.status_code in {200, 400, 502, 503}
    after_total = service.summarize()["total_records"]
    assert after_total >= before_total + 1


def test_auditoria_requires_admin_role() -> None:
    response = client.get("/auditoria/resumen", headers=make_auth_header("user"))

    assert response.status_code == 403
