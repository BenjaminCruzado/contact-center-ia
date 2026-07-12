from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class AuditLogResponse(BaseModel):
    id: int = Field(ge=1)
    created_at: str
    request_id: str
    method: str
    endpoint: str
    interaction_type: str
    http_status: int = Field(ge=100, le=599)
    status: Literal["answered", "out_of_scope", "failed", "processed", "received"]
    confidence_label: Literal["ok", "low_confidence", "out_of_scope", "failed"]
    user_query: str | None = None
    transcript: str | None = None
    response_text: str | None = None
    top_score: float | None = Field(default=None, ge=0, le=1)
    latency_total_ms: float = Field(ge=0)
    latency_stt_ms: float | None = Field(default=None, ge=0)
    latency_rag_ms: float | None = Field(default=None, ge=0)
    latency_llm_ms: float | None = Field(default=None, ge=0)
    latency_tts_ms: float | None = Field(default=None, ge=0)
    total_sources: int = Field(ge=0)
    error_message: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class AuditSummaryResponse(BaseModel):
    total_records: int = Field(ge=0)
    average_latency_ms: float = Field(ge=0)
    low_confidence_count: int = Field(ge=0)
    out_of_scope_count: int = Field(ge=0)
    failed_count: int = Field(ge=0)
    high_latency_count: int = Field(ge=0)
