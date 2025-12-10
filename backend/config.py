"""
Backend Configuration
Load environment variables using Pydantic BaseSettings
"""
import sys
from pydantic_settings import BaseSettings
from pydantic import field_validator
from typing import Optional


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""

    # Database
    DATABASE_URL: str = "postgresql://postgres:password@localhost:5432/hab_public_data"
    DATABASE_POOL_SIZE: int = 10

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    CACHE_TTL: int = 3600

    # Celery
    CELERY_BROKER_URL: str = "redis://localhost:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/2"

    # Backend Server
    BACKEND_HOST: str = "0.0.0.0"
    BACKEND_PORT: int = 8000
    BACKEND_RELOAD: bool = False

    # CORS
    CORS_ORIGINS: list[str] = ["http://localhost:8501", "http://streamlit:8501"]

    # T093: Validate critical environment variables
    @field_validator('DATABASE_URL')
    @classmethod
    def validate_database_url(cls, v: str) -> str:
        """Ensure DATABASE_URL is properly formatted."""
        if not v or not v.startswith(('postgresql://', 'postgres://')):
            raise ValueError(
                "DATABASE_URL must be a valid PostgreSQL connection string "
                "(e.g., postgresql://user:password@host:port/dbname)"
            )
        return v

    @field_validator('REDIS_URL', 'CELERY_BROKER_URL', 'CELERY_RESULT_BACKEND')
    @classmethod
    def validate_redis_url(cls, v: str) -> str:
        """Ensure Redis URLs are properly formatted."""
        if not v or not v.startswith('redis://'):
            raise ValueError(
                f"Redis URL must start with 'redis://' (got: {v})"
            )
        return v

    @field_validator('BACKEND_PORT')
    @classmethod
    def validate_port(cls, v: int) -> int:
        """Ensure port is in valid range."""
        if not 1 <= v <= 65535:
            raise ValueError(f"BACKEND_PORT must be between 1-65535 (got: {v})")
        return v

    class Config:
        env_file = "backend/.env"
        case_sensitive = True


# T093: Global settings instance with validation
try:
    settings = Settings()
except Exception as e:
    print(f"❌ Configuration Error: {str(e)}", file=sys.stderr)
    print("Please check your backend/.env file and ensure all required variables are set.", file=sys.stderr)
    sys.exit(1)
