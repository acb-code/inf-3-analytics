"""Video upload endpoints."""

import re
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, UploadFile, status

from inf3_analytics.api.config import Settings, get_settings
from inf3_analytics.api.dependencies import get_registry
from inf3_analytics.api.models import UploadResponse
from inf3_analytics.api.registry import RunRegistry

router = APIRouter(prefix="/upload", tags=["upload"])


def _sanitize_filename(filename: str) -> str:
    """Sanitize a filename for safe filesystem use.

    Args:
        filename: Original filename

    Returns:
        Sanitized filename with only alphanumeric chars, underscores, hyphens
    """
    # Remove extension first
    stem = Path(filename).stem
    # Replace spaces and special chars with underscores
    sanitized = re.sub(r"[^\w\-]", "_", stem)
    # Collapse multiple underscores
    sanitized = re.sub(r"_+", "_", sanitized)
    # Trim to reasonable length
    return sanitized[:50].strip("_")


def _generate_unique_filename(original_name: str) -> str:
    """Generate a unique filename with timestamp and UUID.

    Args:
        original_name: Original filename

    Returns:
        Unique filename in format: {timestamp}_{uuid}_{sanitized_name}.{ext}
    """
    timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    short_uuid = uuid.uuid4().hex[:8]
    sanitized = _sanitize_filename(original_name)
    ext = Path(original_name).suffix.lower()
    return f"{timestamp}_{short_uuid}_{sanitized}{ext}"


@router.post("", response_model=UploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_video(
    file: UploadFile,
    settings: Annotated[Settings, Depends(get_settings)],
    registry: Annotated[RunRegistry, Depends(get_registry)],
) -> UploadResponse:
    """Upload a video file and create a new run.

    The video is saved to the uploads directory with a unique filename,
    and a new run is created in the registry with pipeline steps initialized.
    """
    # Validate filename
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No filename provided",
        )

    # Validate extension
    ext = Path(file.filename).suffix.lower()
    if ext not in settings.inf3_allowed_video_extensions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid file type '{ext}'. Allowed: {settings.inf3_allowed_video_extensions}",
        )

    # Check file size (read in chunks to avoid loading entire file into memory)
    max_size_bytes = settings.inf3_max_upload_size_mb * 1024 * 1024
    content = await file.read()
    if len(content) > max_size_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File too large. Maximum size: {settings.inf3_max_upload_size_mb}MB",
        )

    # Generate unique filename and paths
    unique_filename = _generate_unique_filename(file.filename)

    # Resolve uploads directory (relative to data root if not absolute)
    if settings.inf3_uploads_dir.is_absolute():
        uploads_dir = settings.inf3_uploads_dir
    else:
        uploads_dir = settings.inf3_data_root / settings.inf3_uploads_dir
    uploads_dir.mkdir(parents=True, exist_ok=True)

    video_path = uploads_dir / unique_filename

    # Generate run_id based on unique filename (without extension)
    run_id = f"run_{Path(unique_filename).stem}"

    # Resolve outputs directory
    if settings.inf3_outputs_dir.is_absolute():
        outputs_dir = settings.inf3_outputs_dir
    else:
        outputs_dir = settings.inf3_data_root / settings.inf3_outputs_dir
    run_root = outputs_dir / run_id
    run_root.mkdir(parents=True, exist_ok=True)

    # Save the uploaded file
    try:
        video_path.write_bytes(content)
    except OSError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save video file: {e}",
        ) from e

    # Create run in registry
    try:
        registry.create_run(
            video_path=str(video_path),
            run_root=str(run_root),
            run_id=run_id,
        )
        # Initialize pipeline steps
        registry.init_pipeline_steps(run_id)
    except Exception as e:
        # Clean up uploaded file on registry error
        video_path.unlink(missing_ok=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create run: {e}",
        ) from e

    return UploadResponse(
        run_id=run_id,
        video_path=str(video_path),
        run_root=str(run_root),
        message=f"Video uploaded successfully. Run ID: {run_id}",
    )
