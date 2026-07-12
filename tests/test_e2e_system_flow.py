import io
import wave

import pytest
from fastapi.testclient import TestClient

from app.api.routers.documentos import get_rag_service
from app.api.routers.orquestador import get_orchestrator_service
from app.api.routers.voz import get_voice_orchestrator_service
from app.main import app
from app.schemas.document import DocumentProcessingResponse
from app.schemas.orchestrator import (
    OrchestratorResponse,
    OrchestratorSource,
    OrchestratorTrace,
)
from app.schemas.search import (
    SemanticSearchResponse,
    SemanticSearchResult,
    VectorStoreStatusResponse,
)
from app.services.audit_service import AuditService
from app.services.voice_orchestrator_service import VoiceInteractionResult
from tests.pdf_factory import create_text_pdf


def build_wav_bytes() -> bytes:
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(16000)
        wav_file.writeframes(b"\x00\x00" * 8000)
    return buffer.getvalue()


class FakeEndToEndRagService:
    def index_document(
        self,
        document: DocumentProcessingResponse,
    ) -> DocumentProcessingResponse:
        return document.model_copy(
            update={
                "indexed_chunks": document.total_chunks,
                "collection": "e2e-collection",
                "embedding_provider": "test",
                "embedding_model": "test-embedding",
            }
        )

    def search(self, query: str, top_k: int) -> SemanticSearchResponse:
        results = [
            SemanticSearchResult(
                position=index + 1,
                chunk_id=f"chunk-{index + 1}",
                document="manual-e2e.pdf",
                content=f"Fragmento relevante {index + 1} para {query}",
                similarity=0.93 - index * 0.08,
                similarity_percentage=93 - index * 8,
                chunk_index=index,
            )
            for index in range(min(top_k, 3))
        ]
        return SemanticSearchResponse(
            query=query,
            total_results=len(results),
            collection="e2e-collection",
            embedding_provider="test",
            embedding_model="test-embedding",
            results=results,
        )

    def status(self) -> VectorStoreStatusResponse:
        return VectorStoreStatusResponse(
            status="active",
            collection="e2e-collection",
            records=3,
            embedding_provider="test",
            embedding_model="test-embedding",
        )


class FakeEndToEndOrchestratorService:
    def respond_with_trace(self, query: str, top_k: int) -> OrchestratorTrace:
        if "fuera" in query.lower():
            return OrchestratorTrace(
                response=OrchestratorResponse(
                    query=query,
                    status="out_of_scope",
                    answer="No encontré suficiente contexto en los documentos cargados.",
                    collection="e2e-collection",
                    llm_provider="mock",
                    llm_model="mock-rag-responder-v1",
                    llm_invoked=False,
                    total_sources=0,
                    sources=[],
                ),
                rag_latency_ms=11.0,
                llm_latency_ms=0.0,
                total_latency_ms=11.0,
                top_score=0.12,
            )

        source = OrchestratorSource(
            position=1,
            chunk_id="chunk-1",
            document="manual-e2e.pdf",
            content="El sistema consulta documentos PDF y responde con base en ellos.",
            similarity=0.93,
            similarity_percentage=93.0,
            chunk_index=0,
        )
        return OrchestratorTrace(
            response=OrchestratorResponse(
                query=query,
                status="answered",
                answer=f"Respuesta validada para: {query}",
                collection="e2e-collection",
                llm_provider="mock",
                llm_model="mock-rag-responder-v1",
                llm_invoked=True,
                total_sources=min(top_k, 1),
                sources=[source],
            ),
            rag_latency_ms=14.0,
            llm_latency_ms=22.0,
            total_latency_ms=36.0,
            top_score=0.93,
        )


class FakeEndToEndVoiceService:
    class _Provider:
        def __init__(self, provider: str) -> None:
            self.provider = provider

    def __init__(self) -> None:
        self.stt_service = self._Provider("mock")
        self.tts_service = self._Provider("mock")

    def interact(
        self,
        audio_bytes: bytes,
        filename: str,
        content_type: str,
        top_k: int = 3,
        transcript_hint: str | None = None,
    ) -> VoiceInteractionResult:
        assert audio_bytes
        assert filename == "entrada.wav"
        assert content_type == "audio/wav"
        transcript = transcript_hint or "consulta por voz"
        answer = f"Respuesta de voz para: {transcript}"
        return VoiceInteractionResult(
            transcript=transcript,
            answer=answer,
            audio_bytes=b"RIFFe2e-audio",
            output_filename="respuesta-voz.wav",
            output_content_type="audio/wav",
            status="answered",
            llm_provider="mock",
            llm_model="mock-rag-responder-v1",
            total_sources=min(top_k, 1),
            confidence_label="ok",
            top_score=0.91,
            latency_total_ms=145.0,
            latency_stt_ms=20.0,
            latency_rag_ms=35.0,
            latency_llm_ms=40.0,
            latency_tts_ms=50.0,
            transcript_base64="Y29uc3VsdGEgcG9yIHZveg==",
            answer_base64="UmVzcHVlc3RhIGRlIHZveiBwYXJhOiBjb25zdWx0YSBwb3Igdmoz",
        )


client = TestClient(app)


@pytest.fixture(autouse=True)
def override_dependencies() -> None:
    app.dependency_overrides[get_rag_service] = FakeEndToEndRagService
    app.dependency_overrides[get_orchestrator_service] = FakeEndToEndOrchestratorService
    app.dependency_overrides[get_voice_orchestrator_service] = FakeEndToEndVoiceService
    yield
    app.dependency_overrides.pop(get_rag_service, None)
    app.dependency_overrides.pop(get_orchestrator_service, None)
    app.dependency_overrides.pop(get_voice_orchestrator_service, None)


def login(username: str, password: str) -> dict[str, str]:
    response = client.post(
        "/auth/login",
        json={"username": username, "password": password},
    )
    assert response.status_code == 200
    payload = response.json()
    return {"Authorization": f"Bearer {payload['access_token']}"}


def test_e2e_black_box_flow_covers_auth_documents_rag_voice_and_audit() -> None:
    audit_service = AuditService()
    before_total = audit_service.summarize()["total_records"]

    admin_headers = login("admin", "admin123")
    user_headers = login("usuario", "user123")

    upload_response = client.post(
        "/documentos/subir?chunk_size=180&chunk_overlap=30",
        files={
            "file": (
                "manual-e2e.pdf",
                create_text_pdf(
                    "El Contact Center procesa documentos PDF y responde con RAG. "
                    * 20
                ),
                "application/pdf",
            )
        },
        headers=admin_headers,
    )
    assert upload_response.status_code == 200
    upload_payload = upload_response.json()
    assert upload_payload["document"] == "manual-e2e.pdf"
    assert upload_payload["collection"] == "e2e-collection"
    assert upload_payload["indexed_chunks"] == upload_payload["total_chunks"]

    search_response = client.post(
        "/documentos/buscar",
        json={"query": "¿Cómo responde el sistema?", "top_k": 3},
        headers=user_headers,
    )
    assert search_response.status_code == 200
    search_payload = search_response.json()
    assert search_payload["total_results"] == 3
    assert search_payload["results"][0]["document"] == "manual-e2e.pdf"

    orchestrator_response = client.post(
        "/orquestador/responder",
        json={"query": "¿Qué hace el sistema con los PDFs?", "top_k": 3},
        headers=user_headers,
    )
    assert orchestrator_response.status_code == 200
    orchestrator_payload = orchestrator_response.json()
    assert orchestrator_payload["status"] == "answered"
    assert orchestrator_payload["llm_invoked"] is True
    assert orchestrator_payload["sources"][0]["document"] == "manual-e2e.pdf"

    voice_response = client.post(
        "/voz/interactuar?top_k=3",
        files={"file": ("entrada.wav", build_wav_bytes(), "audio/wav")},
        data={"transcript_hint": "consulta por voz"},
        headers=user_headers,
    )
    assert voice_response.status_code == 200
    assert voice_response.headers["content-type"].startswith("audio/wav")
    assert voice_response.content == b"RIFFe2e-audio"
    assert voice_response.headers["X-Voice-Status"] == "answered"
    assert voice_response.headers["X-Transcript-B64"] == "Y29uc3VsdGEgcG9yIHZveg=="

    summary_response = client.get("/auditoria/resumen", headers=admin_headers)
    assert summary_response.status_code == 200
    summary_payload = summary_response.json()
    assert summary_payload["total_records"] >= before_total + 5

    records_response = client.get("/auditoria/registros?limit=20", headers=admin_headers)
    assert records_response.status_code == 200
    endpoints = {item["endpoint"] for item in records_response.json()}
    assert "/documentos/subir" in endpoints
    assert "/documentos/buscar" in endpoints
    assert "/orquestador/responder" in endpoints
    assert "/voz/interactuar" in endpoints


def test_e2e_black_box_roles_block_cross_access() -> None:
    admin_headers = login("admin", "admin123")
    user_headers = login("usuario", "user123")

    forbidden_audit = client.get("/auditoria/resumen", headers=user_headers)
    assert forbidden_audit.status_code == 403

    forbidden_voice = client.post(
        "/voz/interactuar?top_k=3",
        files={"file": ("entrada.wav", build_wav_bytes(), "audio/wav")},
        headers=admin_headers,
    )
    assert forbidden_voice.status_code == 403
