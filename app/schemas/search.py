from pydantic import BaseModel, Field, field_validator


class SemanticSearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=2_000)
    top_k: int = Field(default=3, ge=1, le=10)

    @field_validator("query")
    @classmethod
    def validate_query(cls, value: str) -> str:
        clean_value = value.strip()
        if not clean_value:
            raise ValueError("La consulta no puede estar vacía.")
        return clean_value


class SemanticSearchResult(BaseModel):
    position: int = Field(ge=1)
    chunk_id: str
    document: str
    content: str
    similarity: float = Field(ge=0, le=1)
    similarity_percentage: float = Field(ge=0, le=100)
    chunk_index: int = Field(ge=0)
    page_start: int | None = Field(default=None, ge=1)
    page_end: int | None = Field(default=None, ge=1)
    section_title: str | None = None


class SemanticSearchResponse(BaseModel):
    query: str
    total_results: int = Field(ge=0)
    collection: str
    embedding_provider: str
    embedding_model: str
    results: list[SemanticSearchResult]


class VectorStoreStatusResponse(BaseModel):
    status: str
    collection: str
    records: int = Field(ge=0)
    embedding_provider: str
    embedding_model: str
