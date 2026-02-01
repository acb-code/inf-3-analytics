"""API configuration settings."""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """API configuration via environment variables."""

    inf3_data_root: Path = Path.cwd()
    """Root path for security validation. All file operations must be within this path."""

    inf3_registry_path: Path = Path(".inf3-analytics/registry.json")
    """Path to the JSON registry file (relative to cwd or absolute)."""

    inf3_cors_origins: list[str] = ["http://localhost:3000", "http://localhost:8080"]
    """Allowed CORS origins."""

    model_config = {"env_prefix": ""}


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
