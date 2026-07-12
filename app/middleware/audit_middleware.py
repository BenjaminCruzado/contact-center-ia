from __future__ import annotations

import time
import uuid

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from app.services.audit_service import AuditService


class AuditMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, audit_service: AuditService | None = None) -> None:
        super().__init__(app)
        self.audit_service = audit_service or AuditService()

    async def dispatch(self, request: Request, call_next) -> Response:
        request.state.request_id = str(uuid.uuid4())
        request.state.audit_context = {
            "interaction_type": "http",
            "status": "received",
            "metadata": {},
        }
        started_at = time.perf_counter()

        try:
            response = await call_next(request)
        except Exception as exc:
            latency_total_ms = (time.perf_counter() - started_at) * 1000
            self.audit_service.enrich_request(
                request,
                status="failed",
                error_message=str(exc),
            )
            self.audit_service.persist_request(
                request,
                http_status=500,
                latency_total_ms=latency_total_ms,
                error_message=str(exc),
            )
            raise

        latency_total_ms = (time.perf_counter() - started_at) * 1000
        response.headers["X-Request-Id"] = request.state.request_id
        response.headers["X-Process-Time-Ms"] = f"{latency_total_ms:.2f}"
        self.audit_service.persist_request(
            request,
            http_status=response.status_code,
            latency_total_ms=latency_total_ms,
        )
        return response
