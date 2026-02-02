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

    inf3_uploads_dir: Path = Path("uploads")
    """Directory for uploaded video files (relative to data root or absolute)."""

    inf3_outputs_dir: Path = Path("outputs")
    """Directory for pipeline outputs (relative to data root or absolute)."""

    inf3_max_upload_size_mb: int = 2048
    """Maximum upload file size in megabytes."""

    inf3_allowed_video_extensions: list[str] = [".mp4", ".mov", ".avi", ".mkv", ".webm"]
    """Allowed video file extensions for upload."""

    model_config = {"env_prefix": ""}


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
