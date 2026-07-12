from typing import Literal

from pydantic import BaseModel, Field, field_validator


class OrchestratorRequest(BaseModel):
    query: str = Field(min_length=1, max_length=2_000)
    top_k: int = Field(default=3, ge=1, le=10)

    @field_validator("query")
    @classmethod
    def validate_query(cls, value: str) -> str:
        clean_value = value.strip()
        if not clean_value:
            raise ValueError("La consulta no puede estar vacía.")
        return clean_value


class OrchestratorSource(BaseModel):
    position: int = Field(ge=1)
    chunk_id: str
    document: str
    content: str
    similarity: float = Field(ge=0, le=1)
    similarity_percentage: float = Field(ge=0, le=100)
    chunk_index: int = Field(ge=0)


class OrchestratorResponse(BaseModel):
    query: str
    status: Literal["answered", "out_of_scope"]
    answer: str
    collection: str
    llm_provider: str
    llm_model: str
    llm_invoked: bool
    total_sources: int = Field(ge=0)
    sources: list[OrchestratorSource]


class OrchestratorTrace(BaseModel):
    response: OrchestratorResponse
    rag_latency_ms: float = Field(ge=0)
    llm_latency_ms: float = Field(ge=0)
    total_latency_ms: float = Field(ge=0)
    top_score: float | None = Field(default=None, ge=0, le=1)
