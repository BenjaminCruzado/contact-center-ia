from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from threading import Lock
from typing import Any

from app.config.settings import Settings, settings

_DB_LOCK = Lock()


class AuditDatabase:
    def __init__(self, app_settings: Settings = settings) -> None:
        self.settings = app_settings
        self.db_path = Path(app_settings.audit_db_path)
        if not self.db_path.is_absolute():
            self.db_path = Path.cwd() / self.db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

    def _connect(self) -> sqlite3.Connection:
        try:
            connection = sqlite3.connect(self.db_path, check_same_thread=False)
        except sqlite3.OperationalError:
            fallback_path = Path("/tmp/contact-center-audit.db")
            fallback_path.parent.mkdir(parents=True, exist_ok=True)
            self.db_path = fallback_path
            connection = sqlite3.connect(self.db_path, check_same_thread=False)
        connection.row_factory = sqlite3.Row
        return connection

    def initialize(self) -> None:
        with _DB_LOCK, self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS audit_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    created_at TEXT NOT NULL,
                    request_id TEXT NOT NULL,
                    method TEXT NOT NULL,
                    endpoint TEXT NOT NULL,
                    interaction_type TEXT NOT NULL,
                    http_status INTEGER NOT NULL,
                    status TEXT NOT NULL,
                    confidence_label TEXT NOT NULL,
                    user_query TEXT,
                    transcript TEXT,
                    response_text TEXT,
                    top_score REAL,
                    latency_total_ms REAL NOT NULL,
                    latency_stt_ms REAL,
                    latency_rag_ms REAL,
                    latency_llm_ms REAL,
                    latency_tts_ms REAL,
                    total_sources INTEGER NOT NULL DEFAULT 0,
                    error_message TEXT,
                    metadata_json TEXT NOT NULL DEFAULT '{}'
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS document_registry (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    created_at TEXT NOT NULL,
                    document_name TEXT NOT NULL UNIQUE,
                    slug TEXT NOT NULL,
                    collection TEXT NOT NULL,
                    pages INTEGER NOT NULL,
                    total_chunks INTEGER NOT NULL,
                    indexed_chunks INTEGER NOT NULL,
                    embedding_provider TEXT,
                    embedding_model TEXT
                )
                """
            )
            connection.commit()

    def insert_log(self, payload: dict[str, Any]) -> int:
        metadata_json = json.dumps(
            payload.get("metadata", {}),
            ensure_ascii=False,
            sort_keys=True,
        )
        with _DB_LOCK, self._connect() as connection:
            cursor = connection.execute(
                """
                INSERT INTO audit_logs (
                    created_at,
                    request_id,
                    method,
                    endpoint,
                    interaction_type,
                    http_status,
                    status,
                    confidence_label,
                    user_query,
                    transcript,
                    response_text,
                    top_score,
                    latency_total_ms,
                    latency_stt_ms,
                    latency_rag_ms,
                    latency_llm_ms,
                    latency_tts_ms,
                    total_sources,
                    error_message,
                    metadata_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    payload["created_at"],
                    payload["request_id"],
                    payload["method"],
                    payload["endpoint"],
                    payload["interaction_type"],
                    payload["http_status"],
                    payload["status"],
                    payload["confidence_label"],
                    payload.get("user_query"),
                    payload.get("transcript"),
                    payload.get("response_text"),
                    payload.get("top_score"),
                    payload["latency_total_ms"],
                    payload.get("latency_stt_ms"),
                    payload.get("latency_rag_ms"),
                    payload.get("latency_llm_ms"),
                    payload.get("latency_tts_ms"),
                    payload.get("total_sources", 0),
                    payload.get("error_message"),
                    metadata_json,
                ),
            )
            connection.commit()
            return int(cursor.lastrowid)

    def list_logs(
        self,
        limit: int,
        *,
        interaction_type: str | None = None,
        endpoint: str | None = None,
    ) -> list[dict[str, Any]]:
        where_clauses: list[str] = []
        parameters: list[Any] = []
        if interaction_type:
            where_clauses.append("interaction_type = ?")
            parameters.append(interaction_type)
        if endpoint:
            where_clauses.append("endpoint = ?")
            parameters.append(endpoint)
        where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""
        with _DB_LOCK, self._connect() as connection:
            rows = connection.execute(
                f"""
                SELECT *
                FROM audit_logs
                {where_sql}
                ORDER BY id DESC
                LIMIT ?
                """,
                (*parameters, limit),
            ).fetchall()
        return [self._row_to_dict(row) for row in rows]

    def get_log(self, log_id: int) -> dict[str, Any] | None:
        with _DB_LOCK, self._connect() as connection:
            row = connection.execute(
                """
                SELECT *
                FROM audit_logs
                WHERE id = ?
                """,
                (log_id,),
            ).fetchone()
        if row is None:
            return None
        return self._row_to_dict(row)

    def summarize(self) -> dict[str, Any]:
        with _DB_LOCK, self._connect() as connection:
            row = connection.execute(
                """
                SELECT
                    COUNT(*) AS total_records,
                    ROUND(COALESCE(AVG(latency_total_ms), 0), 2) AS average_latency_ms,
                    SUM(CASE WHEN confidence_label = 'low_confidence' THEN 1 ELSE 0 END) AS low_confidence_count,
                    SUM(CASE WHEN status = 'out_of_scope' THEN 1 ELSE 0 END) AS out_of_scope_count,
                    SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) AS failed_count,
                    SUM(CASE WHEN json_extract(metadata_json, '$.alerts.high_latency') = 1 THEN 1 ELSE 0 END) AS high_latency_count
                FROM audit_logs
                """
            ).fetchone()
        if row is None:
            return {
                "total_records": 0,
                "average_latency_ms": 0.0,
                "low_confidence_count": 0,
                "out_of_scope_count": 0,
                "failed_count": 0,
                "high_latency_count": 0,
            }
        return {
            "total_records": int(row["total_records"] or 0),
            "average_latency_ms": float(row["average_latency_ms"] or 0.0),
            "low_confidence_count": int(row["low_confidence_count"] or 0),
            "out_of_scope_count": int(row["out_of_scope_count"] or 0),
            "failed_count": int(row["failed_count"] or 0),
            "high_latency_count": int(row["high_latency_count"] or 0),
        }

    def _row_to_dict(self, row: sqlite3.Row) -> dict[str, Any]:
        payload = dict(row)
        payload["metadata"] = json.loads(payload.pop("metadata_json") or "{}")
        return payload

    def upsert_document(self, payload: dict[str, Any]) -> int:
        with _DB_LOCK, self._connect() as connection:
            cursor = connection.execute(
                """
                INSERT INTO document_registry (
                    created_at,
                    document_name,
                    slug,
                    collection,
                    pages,
                    total_chunks,
                    indexed_chunks,
                    embedding_provider,
                    embedding_model
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(document_name) DO UPDATE SET
                    created_at=excluded.created_at,
                    slug=excluded.slug,
                    collection=excluded.collection,
                    pages=excluded.pages,
                    total_chunks=excluded.total_chunks,
                    indexed_chunks=excluded.indexed_chunks,
                    embedding_provider=excluded.embedding_provider,
                    embedding_model=excluded.embedding_model
                """,
                (
                    payload["created_at"],
                    payload["document_name"],
                    payload["slug"],
                    payload["collection"],
                    payload["pages"],
                    payload["total_chunks"],
                    payload["indexed_chunks"],
                    payload.get("embedding_provider"),
                    payload.get("embedding_model"),
                ),
            )
            connection.commit()
            if cursor.lastrowid:
                return int(cursor.lastrowid)
            row = connection.execute(
                "SELECT id FROM document_registry WHERE document_name = ?",
                (payload["document_name"],),
            ).fetchone()
            return int(row["id"])

    def list_documents(self) -> list[dict[str, Any]]:
        with _DB_LOCK, self._connect() as connection:
            rows = connection.execute(
                """
                SELECT *
                FROM document_registry
                ORDER BY id DESC
                """
            ).fetchall()
        return [dict(row) for row in rows]

    def get_document(self, document_id: int) -> dict[str, Any] | None:
        with _DB_LOCK, self._connect() as connection:
            row = connection.execute(
                """
                SELECT *
                FROM document_registry
                WHERE id = ?
                """,
                (document_id,),
            ).fetchone()
        return dict(row) if row else None

    def delete_document(self, document_id: int) -> dict[str, Any] | None:
        with _DB_LOCK, self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM document_registry WHERE id = ?",
                (document_id,),
            ).fetchone()
            if row is None:
                return None
            connection.execute(
                "DELETE FROM document_registry WHERE id = ?",
                (document_id,),
            )
            connection.commit()
        return dict(row)
