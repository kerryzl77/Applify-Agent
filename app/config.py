"""Application configuration using Pydantic Settings."""

import os
from functools import lru_cache
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # App settings
    app_name: str = "Applify"
    debug: bool = False
    environment: str = "production"
    
    # JWT settings
    jwt_secret_key: str = os.environ.get("JWT_SECRET_KEY", os.environ.get("SECRET_KEY", "dev-secret-key-change-in-production"))
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 7
    
    # Database
    database_url: Optional[str] = None
    
    # Redis
    redis_url: Optional[str] = None
    
    # OpenAI
    openai_api_key: Optional[str] = None
    
    # Google CSE (optional)
    google_cse_api_key: Optional[str] = None
    google_cse_cx: Optional[str] = None
    
    # CORS
    allowed_origins: str = "*"
    
    # Frontend
    frontend_origin: Optional[str] = None
    public_url: Optional[str] = None
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
