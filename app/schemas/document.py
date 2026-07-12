from pydantic import BaseModel, Field


class TextChunkResponse(BaseModel):
    id: str
    index: int = Field(ge=0)
    content: str = Field(min_length=1)
    character_count: int = Field(ge=1)
    start_character: int = Field(ge=0)
    end_character: int = Field(ge=1)


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

