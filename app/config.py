"""Application configuration using Pydantic Settings."""

import os
from functools import lru_cache
from typing import Optional

from pydantic import field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # App settings
    app_name: str = "Applify"
    debug: bool = False
    environment: str = "production"
    
    # JWT settings
    jwt_secret_key: str = os.environ.get(
        "JWT_SECRET_KEY",
        os.environ.get("SECRET_KEY", "dev-secret-key-change-in-production"),
    )
    jwt_algorithm: str = "HS256"
    jwt_issuer: Optional[str] = None
    jwt_audience: Optional[str] = None
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 7
    
    # Database
    database_url: Optional[str] = None
    
    # Redis
    redis_url: Optional[str] = None
    
    # OpenAI
    openai_api_key: Optional[str] = None
    openai_default_model: str = "gpt-5.4"
    
    # CORS
    allowed_origins: str = ""
    
    # Frontend
    frontend_origin: Optional[str] = None
    public_url: Optional[str] = None

    # Queue / worker
    run_queue_name: str = "applify:runs"
    worker_poll_timeout_seconds: int = 5

    # Artifact storage
    artifact_storage_backend: str = "local"
    artifact_storage_local_root: str = "uploads/artifacts"
    s3_bucket_name: Optional[str] = None
    s3_region: Optional[str] = None
    s3_endpoint_url: Optional[str] = None
    s3_access_key_id: Optional[str] = None
    s3_secret_access_key: Optional[str] = None

    @field_validator("artifact_storage_backend")
    @classmethod
    def validate_storage_backend(cls, value: str) -> str:
        normalized = (value or "local").strip().lower()
        if normalized not in {"local", "s3"}:
            raise ValueError("artifact_storage_backend must be 'local' or 's3'")
        return normalized

    @field_validator("allowed_origins")
    @classmethod
    def normalize_origins(cls, value: str) -> str:
        return (value or "").strip()

    @property
    def cors_origins(self) -> list[str]:
        origins = []
        for candidate in [self.allowed_origins, self.frontend_origin, self.public_url]:
            if not candidate:
                continue
            origins.extend(
                item.strip()
                for item in candidate.split(",")
                if item and item.strip()
            )
        deduped = []
        for origin in origins:
            if origin not in deduped:
                deduped.append(origin)
        return deduped
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
