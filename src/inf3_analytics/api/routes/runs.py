"""Run management endpoints."""

from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from inf3_analytics.api.config import Settings, get_settings
from inf3_analytics.api.dependencies import (
    get_registry,
    get_run_or_404,
    validate_path_security,
)
from inf3_analytics.api.models import (
    ArtifactInfo,
    ArtifactType,
    CreateRunRequest,
    RunDetailResponse,
    RunListResponse,
    RunMetadata,
)
from inf3_analytics.api.registry import RunRegistry

router = APIRouter(prefix="/runs", tags=["runs"])


def _detect_artifacts(run: RunMetadata) -> list[ArtifactInfo]:
    """Detect available artifacts for a run."""
    run_root = Path(run.run_root)
    basename = run.video_basename
    artifacts = []

    # Transcript: {run_root}/{basename}.json
    transcript_path = run_root / f"{basename}.json"
    artifacts.append(
        ArtifactInfo(
            type=ArtifactType.TRANSCRIPT,
            available=transcript_path.exists(),
            url=f"/runs/{run.run_id}/artifacts/transcript" if transcript_path.exists() else None,
        )
    )

    # Events: {run_root}/events/{basename}_events.json
    events_path = run_root / "events" / f"{basename}_events.json"
    artifacts.append(
        ArtifactInfo(
            type=ArtifactType.EVENTS,
            available=events_path.exists(),
            url=f"/runs/{run.run_id}/artifacts/events" if events_path.exists() else None,
        )
    )

    # Event frames manifest: {run_root}/event_frames/manifest.json
    frames_manifest_path = run_root / "event_frames" / "manifest.json"
    artifacts.append(
        ArtifactInfo(
            type=ArtifactType.EVENT_FRAMES_MANIFEST,
            available=frames_manifest_path.exists(),
            url=(
                f"/runs/{run.run_id}/artifacts/event-frames/manifest"
                if frames_manifest_path.exists()
                else None
            ),
        )
    )

    # Frame analytics manifest: {run_root}/frame_analytics/manifest_analytics.json
    analytics_manifest_path = run_root / "frame_analytics" / "manifest_analytics.json"
    artifacts.append(
        ArtifactInfo(
            type=ArtifactType.FRAME_ANALYTICS_MANIFEST,
            available=analytics_manifest_path.exists(),
            url=(
                f"/runs/{run.run_id}/artifacts/frame-analytics/manifest"
                if analytics_manifest_path.exists()
                else None
            ),
        )
    )

    return artifacts


@router.post("", response_model=RunMetadata, status_code=status.HTTP_201_CREATED)
def create_run(
    request: CreateRunRequest,
    settings: Annotated[Settings, Depends(get_settings)],
    registry: Annotated[RunRegistry, Depends(get_registry)],
) -> RunMetadata:
    """Register a new pipeline run."""
    video_path = Path(request.video_path)
    run_root = Path(request.run_root)

    # Validate paths are within data root
    validate_path_security(video_path, settings)
    validate_path_security(run_root, settings)

    # Validate video exists
    if not video_path.exists():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Video file not found: {request.video_path}",
        )

    # Create run_root if needed
    run_root.mkdir(parents=True, exist_ok=True)

    return registry.create_run(
        video_path=request.video_path,
        run_root=request.run_root,
        run_id=request.run_id,
    )


@router.get("", response_model=RunListResponse)
def list_runs(
    registry: Annotated[RunRegistry, Depends(get_registry)],
) -> RunListResponse:
    """List all registered runs."""
    runs = registry.list_runs()
    return RunListResponse(runs=runs)


@router.get("/{run_id}", response_model=RunDetailResponse)
def get_run(
    run: Annotated[RunMetadata, Depends(get_run_or_404)],
) -> RunDetailResponse:
    """Get details for a specific run."""
    artifacts = _detect_artifacts(run)
    return RunDetailResponse(run=run, artifacts=artifacts)
