"""Video decomposition endpoints."""

import asyncio
import json
import uuid
from collections.abc import AsyncGenerator
from dataclasses import replace
from datetime import datetime
from pathlib import Path
from typing import Annotated, Any

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, status
from sse_starlette.sse import EventSourceResponse

from inf3_analytics.api.config import Settings, get_settings
from inf3_analytics.api.dependencies import get_registry
from inf3_analytics.api.models import (
    AnalyzeDecompositionRequest,
    DecompositionJobResponse,
    DecompositionJobStatus,
    DecompositionPlanResponse,
    DecompositionStatusResponse,
    ExecuteDecompositionRequest,
    SegmentPreview,
    SegmentResultResponse,
    SplitPointResponse,
)
from inf3_analytics.api.registry import RunRegistry
from inf3_analytics.media.video_decompose import (
    DecompositionError,
    analyze_video_for_splits,
    create_plan_from_timestamps,
    execute_decomposition,
)
from inf3_analytics.types.decomposition import DecompositionManifest

router = APIRouter(prefix="/decompose", tags=["decomposition"])

# In-memory job storage (in production, use Redis or database)
_jobs: dict[str, dict[str, Any]] = {}


def _validate_video_path(video_path: str, settings: Settings) -> Path:
    """Validate that video path is within allowed directories."""
    path = Path(video_path).resolve()
    uploads_dir = settings.inf3_uploads_dir.resolve()
    outputs_dir = settings.inf3_outputs_dir.resolve()

    # Check if path is within uploads or outputs directory
    try:
        path.relative_to(uploads_dir)
        return path
    except ValueError:
        pass

    try:
        path.relative_to(outputs_dir)
        return path
    except ValueError:
        pass

    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=f"Video path must be within uploads or outputs directory",
    )


@router.post("/analyze", response_model=DecompositionPlanResponse)
def analyze_video(
    request: AnalyzeDecompositionRequest,
    settings: Annotated[Settings, Depends(get_settings)],
) -> DecompositionPlanResponse:
    """Analyze a video and return suggested split points.

    Fast operation (~5-10 seconds for 1-hour video).
    """
    video_path = _validate_video_path(request.video_path, settings)

    if not video_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Video file not found: {video_path}",
        )

    try:
        plan = analyze_video_for_splits(
            video_path=video_path,
            target_segment_duration_s=request.target_segment_duration_s,
            silence_threshold_db=request.silence_threshold_db,
        )
    except DecompositionError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        ) from e

    return DecompositionPlanResponse(
        video_path=str(plan.video_path),
        duration_s=plan.duration_s,
        duration_ts=plan.duration_ts,
        file_size_mb=plan.file_size_mb,
        suggested_splits=[
            SplitPointResponse(
                timestamp_s=sp.timestamp_s,
                timestamp_ts=sp.timestamp_ts,
                type=sp.type,
                keyframe_s=sp.keyframe_s,
                confidence=sp.confidence,
            )
            for sp in plan.split_points
        ],
        estimated_segments=[
            SegmentPreview(
                index=seg.index,
                start_s=seg.start_s,
                end_s=seg.end_s,
                duration_s=seg.duration_s,
                start_ts=seg.start_ts,
                end_ts=seg.end_ts,
                estimated_size_mb=seg.estimated_size_mb,
            )
            for seg in plan.segments
        ],
    )


def _run_decomposition_job(
    job_id: str,
    video_path: Path,
    split_timestamps: list[float],
    create_child_runs: bool,
    parent_run_id: str | None,
    settings: Settings,
    registry: RunRegistry,
) -> None:
    """Background task to execute video decomposition."""
    job = _jobs[job_id]

    try:
        # Update status to splitting
        job["status"] = DecompositionJobStatus.SPLITTING
        job["progress_message"] = "Creating decomposition plan..."

        # Create plan from timestamps
        plan = create_plan_from_timestamps(video_path, split_timestamps)
        job["progress_total"] = len(plan.segments)

        # Determine output directory
        if parent_run_id:
            output_dir = settings.inf3_outputs_dir / f"run_{parent_run_id}" / "decomposition" / "segments"
        else:
            video_stem = video_path.stem
            output_dir = settings.inf3_outputs_dir / f"run_{video_stem}" / "decomposition" / "segments"

        # Execute decomposition with progress callback
        def progress_callback(current: int, total: int, message: str) -> None:
            job["progress_current"] = current
            job["progress_total"] = total
            job["progress_message"] = message

        results = execute_decomposition(
            plan=plan,
            output_dir=output_dir,
            progress_callback=progress_callback,
        )

        # Convert results to response format
        segment_results = [
            SegmentResultResponse(
                index=r.index,
                path=str(r.path),
                start_s=r.start_s,
                end_s=r.end_s,
                duration_s=r.duration_s,
                file_size_mb=r.file_size_mb,
                child_run_id=None,
            )
            for r in results
        ]
        job["segments_created"] = segment_results

        # Create child runs if requested
        child_run_ids = []
        if create_child_runs:
            job["status"] = DecompositionJobStatus.CREATING_RUNS
            job["progress_message"] = "Creating child runs..."

            for i, result in enumerate(results):
                job["progress_current"] = i
                job["progress_total"] = len(results)

                # Generate child run ID
                video_stem = video_path.stem
                child_run_id = f"{video_stem}_seg{result.index:03d}"

                # Create run in registry
                run_root = settings.inf3_outputs_dir / f"run_{child_run_id}"
                run_root.mkdir(parents=True, exist_ok=True)

                registry.create_run(
                    run_id=child_run_id,
                    video_path=str(result.path),
                    run_root=str(run_root),
                )
                registry.init_pipeline_steps(child_run_id)

                child_run_ids.append(child_run_id)

                # Update segment result with child run ID
                segment_results[i] = SegmentResultResponse(
                    index=result.index,
                    path=str(result.path),
                    start_s=result.start_s,
                    end_s=result.end_s,
                    duration_s=result.duration_s,
                    file_size_mb=result.file_size_mb,
                    child_run_id=child_run_id,
                )

            job["segments_created"] = segment_results

        job["child_run_ids"] = child_run_ids

        # Save manifest
        manifest_dir = output_dir.parent
        manifest_path = manifest_dir / "manifest.json"
        # Build segment results with child run IDs
        manifest_segments = []
        for i, result in enumerate(results):
            child_id = child_run_ids[i] if create_child_runs and i < len(child_run_ids) else None
            manifest_segments.append(
                replace(result, child_run_id=child_id)
            )

        manifest = DecompositionManifest(
            video_path=video_path,
            duration_s=plan.duration_s,
            created_at=datetime.utcnow().isoformat(),
            segments=tuple(manifest_segments),
            child_run_ids=tuple(child_run_ids),
        )
        manifest_path.write_text(json.dumps(manifest.to_dict(), indent=2))

        # Mark as completed
        job["status"] = DecompositionJobStatus.COMPLETED
        job["progress_current"] = len(results)
        job["progress_total"] = len(results)
        job["progress_message"] = "Decomposition complete"

    except Exception as e:
        job["status"] = DecompositionJobStatus.FAILED
        job["error_message"] = str(e)
        job["progress_message"] = f"Failed: {e}"


@router.post("/execute", response_model=DecompositionJobResponse, status_code=status.HTTP_202_ACCEPTED)
def execute_decomposition_endpoint(
    request: ExecuteDecompositionRequest,
    background_tasks: BackgroundTasks,
    settings: Annotated[Settings, Depends(get_settings)],
    registry: Annotated[RunRegistry, Depends(get_registry)],
) -> DecompositionJobResponse:
    """Execute video decomposition with specified split points.

    Creates segment files and optionally child runs.
    Returns job_id for progress tracking.
    """
    video_path = _validate_video_path(request.video_path, settings)

    if not video_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Video file not found: {video_path}",
        )

    if not request.split_timestamps:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one split timestamp is required",
        )

    # Create job
    job_id = str(uuid.uuid4())[:8]
    _jobs[job_id] = {
        "status": DecompositionJobStatus.ANALYZING,
        "progress_current": 0,
        "progress_total": 0,
        "progress_message": "Starting decomposition...",
        "segments_created": [],
        "child_run_ids": [],
        "error_message": None,
    }

    # Start background task
    background_tasks.add_task(
        _run_decomposition_job,
        job_id=job_id,
        video_path=video_path,
        split_timestamps=request.split_timestamps,
        create_child_runs=request.create_child_runs,
        parent_run_id=request.parent_run_id,
        settings=settings,
        registry=registry,
    )

    return DecompositionJobResponse(
        job_id=job_id,
        message="Decomposition job started",
        status_url=f"/decompose/{job_id}/status",
    )


@router.get("/{job_id}/status", response_model=DecompositionStatusResponse)
def get_decomposition_status(job_id: str) -> DecompositionStatusResponse:
    """Get current status of a decomposition job."""
    if job_id not in _jobs:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job not found: {job_id}",
        )

    job = _jobs[job_id]
    return DecompositionStatusResponse(
        job_id=job_id,
        status=job["status"],
        progress_current=job["progress_current"],
        progress_total=job["progress_total"],
        progress_message=job["progress_message"],
        segments_created=job["segments_created"],
        child_run_ids=job["child_run_ids"],
        error_message=job["error_message"],
    )


async def _status_event_generator(
    request: Request,
    job_id: str,
) -> AsyncGenerator[dict[str, Any], None]:
    """Generate SSE events for decomposition status updates."""
    last_status_json: str | None = None

    while True:
        # Check if client disconnected
        if await request.is_disconnected():
            break

        if job_id not in _jobs:
            yield {"event": "error", "data": json.dumps({"error": "Job not found"})}
            break

        job = _jobs[job_id]
        status_response = DecompositionStatusResponse(
            job_id=job_id,
            status=job["status"],
            progress_current=job["progress_current"],
            progress_total=job["progress_total"],
            progress_message=job["progress_message"],
            segments_created=job["segments_created"],
            child_run_ids=job["child_run_ids"],
            error_message=job["error_message"],
        )

        status_dict = status_response.model_dump(mode="json")
        current_status_json = json.dumps(status_dict, sort_keys=True)

        # Only emit if status changed
        if current_status_json != last_status_json:
            last_status_json = current_status_json
            yield {"event": "status", "data": json.dumps(status_dict)}

        # Check if job is done
        if job["status"] in (DecompositionJobStatus.COMPLETED, DecompositionJobStatus.FAILED):
            yield {"event": "done", "data": json.dumps({"status": job["status"].value})}
            break

        await asyncio.sleep(0.5)


@router.get("/{job_id}/stream")
async def stream_decomposition_status(
    request: Request,
    job_id: str,
) -> EventSourceResponse:
    """Stream decomposition status updates via Server-Sent Events."""
    if job_id not in _jobs:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job not found: {job_id}",
        )

    return EventSourceResponse(
        _status_event_generator(request, job_id),
        media_type="text/event-stream",
    )
