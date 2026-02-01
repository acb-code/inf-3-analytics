"""Artifact retrieval endpoints."""

from pathlib import Path
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, status

from inf3_analytics.api.dependencies import get_run_or_404
from inf3_analytics.api.models import RunMetadata
from inf3_analytics.io import read_events_json, read_json, read_manifest
from inf3_analytics.io.analytics_writer import read_analytics_manifest

router = APIRouter(prefix="/runs/{run_id}/artifacts", tags=["artifacts"])


@router.get("/transcript")
def get_transcript(
    run: Annotated[RunMetadata, Depends(get_run_or_404)],
) -> dict[str, Any]:
    """Get the transcript for a run."""
    run_root = Path(run.run_root)
    transcript_path = run_root / f"{run.video_basename}.json"

    if not transcript_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transcript not found",
        )

    transcript = read_json(transcript_path)
    return transcript.to_dict()


@router.get("/events")
def get_events(
    run: Annotated[RunMetadata, Depends(get_run_or_404)],
) -> dict[str, Any]:
    """Get the events for a run."""
    run_root = Path(run.run_root)
    events_path = run_root / "events" / f"{run.video_basename}_events.json"

    if not events_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Events not found",
        )

    events = read_events_json(events_path)
    return events.to_dict()


@router.get("/event-frames/manifest")
def get_event_frames_manifest(
    run: Annotated[RunMetadata, Depends(get_run_or_404)],
) -> dict[str, Any]:
    """Get the event frames manifest for a run."""
    run_root = Path(run.run_root)
    manifest_path = run_root / "event_frames" / "manifest.json"

    if not manifest_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event frames manifest not found",
        )

    manifest = read_manifest(manifest_path)
    return manifest.to_dict()


@router.get("/frame-analytics/manifest")
def get_frame_analytics_manifest(
    run: Annotated[RunMetadata, Depends(get_run_or_404)],
) -> dict[str, Any]:
    """Get the frame analytics manifest for a run."""
    run_root = Path(run.run_root)
    manifest_path = run_root / "frame_analytics" / "manifest_analytics.json"

    if not manifest_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Frame analytics manifest not found",
        )

    manifest = read_analytics_manifest(manifest_path)
    return manifest.to_dict()
