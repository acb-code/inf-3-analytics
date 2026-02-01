"""FastAPI dependencies for dependency injection."""

from functools import lru_cache
from pathlib import Path
from typing import Annotated

from fastapi import Depends, HTTPException, status

from inf3_analytics.api.config import Settings, get_settings
from inf3_analytics.api.models import RunMetadata
from inf3_analytics.api.registry import RunRegistry


@lru_cache
def _registry_for_path(registry_path: Path) -> RunRegistry:
    """Cache a registry per path (Path is hashable)."""
    return RunRegistry(registry_path)


def get_registry(settings: Annotated[Settings, Depends(get_settings)]) -> RunRegistry:
    """Get cached registry instance."""
    return _registry_for_path(settings.inf3_registry_path)


def validate_path_security(path: Path, settings: Settings) -> None:
    """Validate that a path is within the allowed data root.

    Args:
        path: Path to validate
        settings: Settings with data root

    Raises:
        HTTPException: 403 if path is outside data root
    """
    try:
        resolved = path.resolve()
        data_root = settings.inf3_data_root.resolve()
        resolved.relative_to(data_root)
    except ValueError as err:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Path {path} is outside allowed data root",
        ) from err


def get_run_or_404(
    run_id: str,
    registry: Annotated[RunRegistry, Depends(get_registry)],
) -> RunMetadata:
    """Get a run by ID or raise 404.

    Args:
        run_id: The run identifier
        registry: Run registry

    Returns:
        RunMetadata for the run

    Raises:
        HTTPException: 404 if run not found
    """
    run = registry.get_run(run_id)
    if run is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Run {run_id} not found",
        )
    return run
