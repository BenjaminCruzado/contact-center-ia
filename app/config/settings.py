from functools import lru_cache
from typing import Literal

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = Field(default="Contact Center API", min_length=1)
    app_version: str = Field(default="0.5.0", min_length=1)
    app_env: Literal["development", "testing", "production"] = "development"
    app_debug: bool = False
    app_host: str = "0.0.0.0"
    app_port: int = Field(default=8000, ge=1, le=65535)
    embedding_provider: Literal["local", "openai"] = "local"
    llm_provider: Literal["mock", "openai"] = "mock"
    stt_provider: Literal["mock", "local"] = "local"
    tts_provider: Literal["mock", "local"] = "local"
    local_embedding_model: str = Field(
        default="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
        min_length=1,
    )
    local_embedding_device: str = Field(default="cpu", min_length=1)
    local_embedding_batch_size: int = Field(default=16, ge=1, le=128)
    sentence_transformers_home: str = Field(
        default="/models/sentence-transformers",
        min_length=1,
    )
    openai_api_key: SecretStr | None = None
    openai_embedding_model: str = Field(
        default="text-embedding-3-small",
        min_length=1,
    )
    openai_chat_model: str = Field(default="gpt-4o-mini", min_length=1)
    openai_timeout_seconds: float = Field(default=30.0, gt=0, le=120)
    openai_max_retries: int = Field(default=2, ge=0, le=5)
    llm_timeout_seconds: float = Field(default=45.0, gt=0, le=180)
    llm_max_retries: int = Field(default=2, ge=0, le=5)
    rag_min_similarity: float = Field(default=0.45, ge=0, le=1)
    rag_min_results: int = Field(default=1, ge=1, le=10)
    whisper_model: str = Field(default="tiny", min_length=1)
    whisper_language: str = Field(default="es", min_length=2, max_length=10)
    whisper_cache_dir: str = Field(default="/models/whisper", min_length=1)
    tts_voice: str = Field(default="es-la", min_length=1)
    audio_max_file_size_bytes: int = Field(default=12 * 1024 * 1024, ge=1024)
    audio_output_mime_type: str = Field(default="audio/wav", min_length=1)
    chroma_host: str = Field(default="chroma", min_length=1)
    chroma_port: int = Field(default=8000, ge=1, le=65535)
    chroma_host_port: int = Field(default=8001, ge=1, le=65535)
    chroma_collection_prefix: str = Field(
        default="contact-center-documents",
        min_length=3,
        max_length=128,
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
