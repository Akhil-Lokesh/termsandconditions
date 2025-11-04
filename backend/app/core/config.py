"""
Configuration settings for the T&C Analysis System.

Uses Pydantic Settings to load and validate environment variables.
"""

from typing import List
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
import json


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Application
    APP_NAME: str = "T&C Analysis API"
    ENVIRONMENT: str = "development"
    DEBUG: bool = False

    # OpenAI Configuration
    OPENAI_API_KEY: str
    OPENAI_MODEL_GPT4: str = "gpt-4"
    OPENAI_MODEL_GPT35: str = "gpt-3.5-turbo"
    OPENAI_EMBEDDING_MODEL: str = "text-embedding-3-small"
    OPENAI_MAX_RETRIES: int = 3
    OPENAI_TIMEOUT: int = 60

    # Pinecone Configuration
    PINECONE_API_KEY: str
    PINECONE_ENVIRONMENT: str = "us-east-1"
    PINECONE_CLOUD: str = "aws"
    PINECONE_INDEX_NAME: str = "tc-analysis"
    PINECONE_USER_NAMESPACE: str = "user_tcs"
    PINECONE_BASELINE_NAMESPACE: str = "baseline"

    # Database Configuration
    DATABASE_URL: str
    DATABASE_POOL_SIZE: int = 5
    DATABASE_MAX_OVERFLOW: int = 10

    # Redis Configuration
    REDIS_URL: str = "redis://localhost:6379/0"
    CACHE_TTL: int = 3600  # 1 hour in seconds
    REDIS_MAX_CONNECTIONS: int = 10

    # JWT Authentication
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # API Settings
    API_V1_PREFIX: str = "/api/v1"
    BACKEND_CORS_ORIGINS: List[str] = [
        "http://localhost:5173",
        "http://localhost:3000",
        "http://localhost:8000",
    ]

    # File Upload Settings
    MAX_FILE_SIZE_MB: int = 10
    ALLOWED_FILE_TYPES: List[str] = [".pdf"]

    # Anomaly Detection Settings
    PREVALENCE_THRESHOLD: float = 0.30
    SIMILARITY_THRESHOLD: float = 0.85
    BASELINE_SAMPLE_SIZE: int = 50

    # Rate Limiting
    RATE_LIMIT_PER_HOUR: int = 100

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", case_sensitive=True, extra="ignore"
    )

    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, v):
        """Parse CORS origins from JSON string or list."""
        if isinstance(v, str):
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                # If it's a single origin, return as list
                return [v]
        return v

    @field_validator("ALLOWED_FILE_TYPES", mode="before")
    @classmethod
    def parse_allowed_file_types(cls, v):
        """Parse allowed file types from JSON string or list."""
        if isinstance(v, str):
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                return [v]
        return v

    @property
    def max_file_size_bytes(self) -> int:
        """Convert MB to bytes."""
        return self.MAX_FILE_SIZE_MB * 1024 * 1024

    @property
    def MAX_UPLOAD_SIZE_MB(self) -> int:
        """Alias for MAX_FILE_SIZE_MB for backwards compatibility."""
        return self.MAX_FILE_SIZE_MB


# Create global settings instance
settings = Settings()
