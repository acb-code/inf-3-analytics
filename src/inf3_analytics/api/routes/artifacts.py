"""Artifact retrieval endpoints."""

import json
from pathlib import Path
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse

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


@router.get("/event-frames/{event_dir}/frames/{frame_filename}")
def get_event_frame_image(
    event_dir: str,
    frame_filename: str,
    run: Annotated[RunMetadata, Depends(get_run_or_404)],
) -> FileResponse:
    """Serve an individual event frame image."""
    run_root = Path(run.run_root)
    frame_path = run_root / "event_frames" / event_dir / "frames" / frame_filename

    # Security: ensure path is within expected directory
    try:
        frame_path = frame_path.resolve()
        expected_root = (run_root / "event_frames").resolve()
        if not str(frame_path).startswith(str(expected_root)):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid path",
            )
    except (ValueError, OSError):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid path",
        )

    if not frame_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Frame image not found",
        )

    return FileResponse(frame_path, media_type="image/jpeg")


@router.get("/event-frames/{event_dir}/info")
def get_event_frames_info(
    event_dir: str,
    run: Annotated[RunMetadata, Depends(get_run_or_404)],
) -> dict[str, Any]:
    """Get frames info for a specific event directory."""
    run_root = Path(run.run_root)
    frames_json_path = run_root / "event_frames" / event_dir / "frames.json"

    if not frames_json_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event frames info not found",
        )

    with open(frames_json_path) as f:
        return json.load(f)


@router.get("/frame-analytics/by-event/{event_id}")
def get_event_frame_analyses(
    event_id: str,
    run: Annotated[RunMetadata, Depends(get_run_or_404)],
) -> dict[str, Any]:
    """Get frame analyses for a specific event by event_id.

    Returns per-frame VLM analysis including scene summaries and detections.
    """
    run_root = Path(run.run_root)
    analytics_root = run_root / "frame_analytics"

    if not analytics_root.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Frame analytics not found",
        )

    # Find the analytics directory for this event by checking event_summary.json
    matching_dir = None
    for d in analytics_root.iterdir():
        if not d.is_dir():
            continue
        summary_path = d / "event_summary.json"
        if summary_path.exists():
            with open(summary_path) as f:
                summary = json.load(f)
                if summary.get("event_id") == event_id:
                    matching_dir = d
                    break

    if not matching_dir:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Frame analytics not found for event: {event_id}",
        )

    # Read frame_analyses.jsonl
    analyses_path = matching_dir / "frame_analyses.jsonl"
    summary_path = matching_dir / "event_summary.json"

    result: dict[str, Any] = {
        "event_id": event_id,
        "frame_analyses": [],
        "event_summary": None,
    }

    if analyses_path.exists():
        with open(analyses_path) as f:
            for line in f:
                line = line.strip()
                if line:
                    result["frame_analyses"].append(json.loads(line))

    if summary_path.exists():
        with open(summary_path) as f:
            result["event_summary"] = json.load(f)

    return result
