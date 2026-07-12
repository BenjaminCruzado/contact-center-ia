from fastapi import Request

from app.config.settings import Settings
from app.db.audit_db import AuditDatabase
from app.services.audit_service import AuditService


def build_request() -> Request:
    scope = {
        "type": "http",
        "method": "POST",
        "path": "/voz/interactuar-debug",
        "headers": [],
        "client": ("127.0.0.1", 12345),
        "server": ("testserver", 80),
        "scheme": "http",
    }
    request = Request(scope)
    request.state.request_id = "req-123"
    request.state.audit_context = {}
    return request


def test_audit_service_persists_voice_interaction(tmp_path) -> None:
    local_settings = Settings(audit_db_path=str(tmp_path / "audit.db"))
    service = AuditService(AuditDatabase(local_settings), local_settings)
    service.initialize()
    request = build_request()

    service.enrich_request(
        request,
        interaction_type="voice",
        user_query="consulta",
        transcript="consulta",
        response_text="respuesta",
        status="answered",
        top_score=0.82,
        latency_stt_ms=10,
        latency_rag_ms=20,
        latency_llm_ms=30,
        latency_tts_ms=40,
        total_sources=2,
        metadata={"llm_provider": "mock"},
    )
    record_id = service.persist_request(
        request,
        http_status=200,
        latency_total_ms=120,
    )

    record = service.get_log(record_id)

    assert record is not None
    assert record["interaction_type"] == "voice"
    assert record["confidence_label"] == "ok"
    assert record["latency_total_ms"] == 120.0
    assert record["metadata"]["llm_provider"] == "mock"


def test_audit_summary_counts_low_confidence(tmp_path) -> None:
    local_settings = Settings(
        audit_db_path=str(tmp_path / "audit.db"),
        audit_confidence_threshold=0.60,
    )
    service = AuditService(AuditDatabase(local_settings), local_settings)
    service.initialize()
    request = build_request()

    service.enrich_request(
        request,
        interaction_type="orchestrator",
        user_query="consulta",
        status="answered",
        top_score=0.40,
    )
    service.persist_request(request, http_status=200, latency_total_ms=500)

    summary = service.summarize()

    assert summary["total_records"] == 1
    assert summary["low_confidence_count"] == 1
