from functools import lru_cache
from typing import Literal

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = Field(default="Contact Center API", min_length=1)
    app_version: str = Field(default="0.3.0", min_length=1)
    app_env: Literal["development", "testing", "production"] = "development"
    app_debug: bool = False
    app_host: str = "0.0.0.0"
    app_port: int = Field(default=8000, ge=1, le=65535)
    embedding_provider: Literal["local", "openai"] = "local"
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
    openai_timeout_seconds: float = Field(default=30.0, gt=0, le=120)
    openai_max_retries: int = Field(default=2, ge=0, le=5)
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
