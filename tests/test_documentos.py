import pytest
from fastapi.testclient import TestClient

from app.api.routers.documentos import get_rag_service
from app.main import app
from app.schemas.document import DocumentProcessingResponse
from tests.pdf_factory import create_text_pdf


class FakeRagService:
    def index_document(
        self,
        document: DocumentProcessingResponse,
    ) -> DocumentProcessingResponse:
        return document.model_copy(
            update={
                "indexed_chunks": document.total_chunks,
                "collection": "test-collection",
                "embedding_provider": "test",
                "embedding_model": "test-embedding",
            }
        )


client = TestClient(app)


@pytest.fixture(autouse=True)
def override_rag_service() -> None:
    app.dependency_overrides[get_rag_service] = FakeRagService
    yield
    app.dependency_overrides.pop(get_rag_service, None)


def test_upload_pdf_returns_structured_chunks() -> None:
    text = " ".join(
        "El Contact Center procesa documentos y conserva el contexto."
        for _ in range(20)
    )
    response = client.post(
        "/documentos/subir?chunk_size=180&chunk_overlap=30",
        files={"file": ("manual.pdf", create_text_pdf(text), "application/pdf")},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["document"] == "manual.pdf"
    assert payload["pages"] == 1
    assert payload["total_chunks"] > 1
    assert payload["chunk_size"] == 180
    assert payload["chunk_overlap"] == 30
    assert payload["chunks"][0]["id"] == "manual-0001"
    assert payload["indexed_chunks"] == payload["total_chunks"]
    assert payload["collection"] == "test-collection"


def test_rejects_non_pdf_upload() -> None:
    response = client.post(
        "/documentos/subir",
        files={"file": ("notas.txt", b"texto", "text/plain")},
    )

    assert response.status_code == 415


def test_rejects_overlap_equal_to_chunk_size() -> None:
    response = client.post(
        "/documentos/subir?chunk_size=100&chunk_overlap=100",
        files={"file": ("manual.pdf", create_text_pdf("Texto"), "application/pdf")},
    )

    assert response.status_code == 422

