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
    chroma_collection: str = Field(
        default="contact-center-documents",
        min_length=3,
        max_length=512,
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
