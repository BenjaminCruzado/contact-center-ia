from __future__ import annotations

from typing import Any

from app.config.settings import Settings, settings


def classify_confidence(
    *,
    status: str,
    top_score: float | None,
    app_settings: Settings = settings,
) -> str:
    if status == "failed":
        return "failed"
    if status == "out_of_scope":
        return "out_of_scope"
    if top_score is None:
        return "ok"
    if top_score < app_settings.audit_confidence_threshold:
        return "low_confidence"
    return "ok"


def build_alerts(
    *,
    status: str,
    top_score: float | None,
    latency_total_ms: float,
    app_settings: Settings = settings,
) -> dict[str, Any]:
    confidence_label = classify_confidence(
        status=status,
        top_score=top_score,
        app_settings=app_settings,
    )
    messages: list[str] = []
    if confidence_label == "low_confidence":
        messages.append("La respuesta quedó bajo el umbral de confianza configurado.")
    if confidence_label == "out_of_scope":
        messages.append("La consulta quedó fuera del contexto documental disponible.")
    if confidence_label == "failed":
        messages.append("La interacción terminó con error.")
    if latency_total_ms > app_settings.audit_high_latency_ms:
        messages.append("La latencia total superó el umbral configurado.")

    return {
        "confidence_label": confidence_label,
        "high_latency": latency_total_ms > app_settings.audit_high_latency_ms,
        "messages": messages,
    }
