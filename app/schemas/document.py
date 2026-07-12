from pydantic import BaseModel, Field


class TextChunkResponse(BaseModel):
    id: str
    index: int = Field(ge=0)
    content: str = Field(min_length=1)
    character_count: int = Field(ge=1)
    start_character: int = Field(ge=0)
    end_character: int = Field(ge=1)
    page_start: int | None = Field(default=None, ge=1)
    page_end: int | None = Field(default=None, ge=1)
    section_title: str | None = None


class DocumentProcessingResponse(BaseModel):
    document: str
    pages: int = Field(ge=1)
    extracted_characters: int = Field(ge=1)
    chunk_size: int = Field(ge=1)
    chunk_overlap: int = Field(ge=0)
    total_chunks: int = Field(ge=1)
    indexed_chunks: int = Field(default=0, ge=0)
    collection: str | None = None
    embedding_provider: str | None = None
    embedding_model: str | None = None
    chunks: list[TextChunkResponse]


class DocumentCatalogItem(BaseModel):
    id: int = Field(ge=1)
    created_at: str
    document_name: str
    slug: str
    collection: str
    pages: int = Field(ge=1)
    total_chunks: int = Field(ge=0)
    indexed_chunks: int = Field(ge=0)
    embedding_provider: str | None = None
    embedding_model: str | None = None


class DocumentDeleteResponse(BaseModel):
    id: int = Field(ge=1)
    document_name: str
    collection: str
    deleted: bool = True

