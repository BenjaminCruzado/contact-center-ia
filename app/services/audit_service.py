from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

from fastapi import Request

from app.config.settings import Settings, settings
from app.db.audit_db import AuditDatabase
from app.services.alert_service import build_alerts

logger = logging.getLogger("uvicorn.error")


class AuditService:
    def __init__(
        self,
        database: AuditDatabase | None = None,
        app_settings: Settings = settings,
    ) -> None:
        self.settings = app_settings
        self.database = database or AuditDatabase(app_settings)

    def initialize(self) -> None:
        self.database.initialize()

    def enrich_request(self, request: Request, **values: Any) -> None:
        context = getattr(request.state, "audit_context", {})
        metadata = context.setdefault("metadata", {})

        for key, value in values.items():
            if key == "metadata" and isinstance(value, dict):
                metadata.update(value)
            else:
                context[key] = value

        request.state.audit_context = context

    def persist_request(
        self,
        request: Request,
        *,
        http_status: int,
        latency_total_ms: float,
        error_message: str | None = None,
    ) -> int:
        context = getattr(request.state, "audit_context", {})
        status = str(context.get("status", "received"))
        top_score = context.get("top_score")
        alerts = build_alerts(
            status=status,
            top_score=top_score,
            latency_total_ms=latency_total_ms,
            app_settings=self.settings,
        )
        metadata = dict(context.get("metadata", {}))
        metadata["alerts"] = alerts
        metadata["client"] = {
            "host": request.client.host if request.client else None,
            "port": request.client.port if request.client else None,
        }

        payload = {
            "created_at": datetime.now(UTC).isoformat(),
            "request_id": getattr(request.state, "request_id", "unknown"),
            "method": request.method,
            "endpoint": request.url.path,
            "interaction_type": str(context.get("interaction_type", "http")),
            "http_status": http_status,
            "status": status if status in {"answered", "out_of_scope", "failed", "processed", "received"} else "received",
            "confidence_label": alerts["confidence_label"],
            "user_query": context.get("user_query"),
            "transcript": context.get("transcript"),
            "response_text": context.get("response_text"),
            "top_score": top_score,
            "latency_total_ms": round(latency_total_ms, 2),
            "latency_stt_ms": self._round_optional(context.get("latency_stt_ms")),
            "latency_rag_ms": self._round_optional(context.get("latency_rag_ms")),
            "latency_llm_ms": self._round_optional(context.get("latency_llm_ms")),
            "latency_tts_ms": self._round_optional(context.get("latency_tts_ms")),
            "total_sources": int(context.get("total_sources", 0)),
            "error_message": error_message or context.get("error_message"),
            "metadata": metadata,
        }
        record_id = self.database.insert_log(payload)

        if alerts["messages"]:
            logger.warning(
                "Auditoría con alertas: request_id=%s endpoint=%s alertas=%s",
                payload["request_id"],
                payload["endpoint"],
                " | ".join(alerts["messages"]),
            )
        logger.info(
            "Auditoría registrada: request_id=%s endpoint=%s estado=%s latencia_total_ms=%.2f",
            payload["request_id"],
            payload["endpoint"],
            payload["status"],
            payload["latency_total_ms"],
        )
        return record_id

    def list_logs(self, limit: int | None = None) -> list[dict[str, Any]]:
        return self.database.list_logs(limit or self.settings.audit_history_limit)

    def get_log(self, log_id: int) -> dict[str, Any] | None:
        return self.database.get_log(log_id)

    def summarize(self) -> dict[str, Any]:
        return self.database.summarize()

    @staticmethod
    def _round_optional(value: Any) -> float | None:
        if value is None:
            return None
        return round(float(value), 2)
