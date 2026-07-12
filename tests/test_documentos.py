import pytest
from fastapi.testclient import TestClient

from app.api.routers.documentos import (
    get_document_registry_service,
    get_rag_service,
)
from app.main import app
from app.schemas.document import (
    DocumentCatalogItem,
    DocumentDeleteResponse,
    DocumentProcessingResponse,
)
from tests.auth_helpers import make_auth_header
from tests.pdf_factory import create_text_pdf


class FakeVectorStore:
    def __init__(self) -> None:
        self.deleted_documents: list[str] = []

    def delete_by_document(self, document: str) -> int:
        self.deleted_documents.append(document)
        return 3


class FakeRagService:
    def __init__(self) -> None:
        self.vector_store = FakeVectorStore()

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


class FakeDocumentRegistryService:
    def __init__(self) -> None:
        self.documents: list[DocumentCatalogItem] = [
            DocumentCatalogItem(
                id=1,
                created_at="2026-07-12T00:00:00+00:00",
                document_name="manual.pdf",
                slug="manual",
                collection="test-collection",
                pages=1,
                total_chunks=3,
                indexed_chunks=3,
                embedding_provider="test",
                embedding_model="test-embedding",
            )
        ]
        self.registered: list[str] = []

    def register(self, document: DocumentProcessingResponse) -> DocumentCatalogItem:
        self.registered.append(document.document)
        return self.documents[0]

    def list_documents(self) -> list[DocumentCatalogItem]:
        return list(self.documents)

    def get_document(self, document_id: int) -> DocumentCatalogItem | None:
        for item in self.documents:
            if item.id == document_id:
                return item
        return None

    def delete_document(self, document_id: int) -> DocumentDeleteResponse | None:
        item = self.get_document(document_id)
        if item is None:
            return None
        self.documents = [document for document in self.documents if document.id != document_id]
        return DocumentDeleteResponse(
            id=item.id,
            document_name=item.document_name,
            collection=item.collection,
            deleted=True,
        )


client = TestClient(app)
fake_rag_service = FakeRagService()
fake_registry_service = FakeDocumentRegistryService()


@pytest.fixture(autouse=True)
def override_services() -> None:
    fake_rag_service.vector_store.deleted_documents.clear()
    fake_registry_service.documents = [
        DocumentCatalogItem(
            id=1,
            created_at="2026-07-12T00:00:00+00:00",
            document_name="manual.pdf",
            slug="manual",
            collection="test-collection",
            pages=1,
            total_chunks=3,
            indexed_chunks=3,
            embedding_provider="test",
            embedding_model="test-embedding",
        )
    ]
    fake_registry_service.registered.clear()
    app.dependency_overrides[get_rag_service] = lambda: fake_rag_service
    app.dependency_overrides[get_document_registry_service] = lambda: fake_registry_service
    yield
    app.dependency_overrides.pop(get_rag_service, None)
    app.dependency_overrides.pop(get_document_registry_service, None)


def test_upload_pdf_returns_structured_chunks() -> None:
    text = " ".join(
        "El Contact Center procesa documentos y conserva el contexto."
        for _ in range(20)
    )
    response = client.post(
        "/documentos/subir?chunk_size=180&chunk_overlap=30",
        files={"file": ("manual.pdf", create_text_pdf(text), "application/pdf")},
        headers=make_auth_header("admin"),
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
    assert fake_registry_service.registered == ["manual.pdf"]


def test_list_documents_returns_registered_documents() -> None:
    response = client.get("/documentos", headers=make_auth_header("admin"))

    assert response.status_code == 200
    payload = response.json()
    assert len(payload) == 1
    assert payload[0]["document_name"] == "manual.pdf"


def test_delete_document_removes_catalog_and_vector_chunks() -> None:
    response = client.delete("/documentos/1", headers=make_auth_header("admin"))

    assert response.status_code == 200
    assert response.json()["deleted"] is True
    assert fake_rag_service.vector_store.deleted_documents == ["manual.pdf"]
    assert fake_registry_service.documents == []


def test_delete_document_returns_404_when_missing() -> None:
    response = client.delete("/documentos/999", headers=make_auth_header("admin"))

    assert response.status_code == 404


def test_rejects_non_pdf_upload() -> None:
    response = client.post(
        "/documentos/subir",
        files={"file": ("notas.txt", b"texto", "text/plain")},
        headers=make_auth_header("admin"),
    )

    assert response.status_code == 415


def test_rejects_overlap_equal_to_chunk_size() -> None:
    response = client.post(
        "/documentos/subir?chunk_size=100&chunk_overlap=100",
        files={"file": ("manual.pdf", create_text_pdf("Texto"), "application/pdf")},
        headers=make_auth_header("admin"),
    )

    assert response.status_code == 422


def test_upload_requires_admin_role() -> None:
    response = client.post(
        "/documentos/subir",
        files={"file": ("manual.pdf", create_text_pdf("Texto"), "application/pdf")},
        headers=make_auth_header("user"),
    )

    assert response.status_code == 403
