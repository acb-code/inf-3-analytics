"""Pipeline execution endpoints."""

import asyncio
import json
import time
from collections.abc import AsyncGenerator
from typing import Annotated, Any

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, status
from sse_starlette.sse import EventSourceResponse

from inf3_analytics.api.dependencies import get_registry, get_run_or_404
from inf3_analytics.api.models import (
    PipelineStatusResponse,
    PipelineStep,
    PipelineStepInfo,
    RunMetadata,
    RunStatus,
    StepStatus,
    TriggerPipelineRequest,
)
from inf3_analytics.api.pipeline_executor import (
    cancel_pipeline,
    execute_pipeline,
    execute_single_step,
)
from inf3_analytics.api.queue import TaskQueue
from inf3_analytics.api.registry import RunRegistry

router = APIRouter(prefix="/runs/{run_id}/pipeline", tags=["pipeline"])

# Shared queue instance (initialized lazily)
_queue: TaskQueue | None = None


def get_queue() -> TaskQueue:
    """Get the shared task queue instance."""
    global _queue
    if _queue is None:
        _queue = TaskQueue()
    return _queue


def _calculate_progress(steps: list[PipelineStepInfo]) -> int:
    """Calculate progress percentage from step statuses.

    Args:
        steps: List of pipeline step info

    Returns:
        Progress percentage (0-100)
    """
    if not steps:
        return 0

    total = len(steps)
    progress_sum = 0.0
    for step in steps:
        if step.status in (StepStatus.COMPLETED, StepStatus.SKIPPED):
            progress_sum += 1.0
        elif step.status == StepStatus.RUNNING:
            if step.progress_total and step.progress_total > 0 and step.progress_current is not None:
                fraction = min(step.progress_current / step.progress_total, 1.0)
                progress_sum += fraction
            else:
                progress_sum += 0.5

    progress = (progress_sum / total) * 100
    return int(progress)


def _check_step_prerequisites(step: PipelineStep, steps: list[PipelineStepInfo]) -> str | None:
    """Check if prerequisites for a step are met.

    Args:
        step: The step to check
        steps: Current step statuses

    Returns:
        Error message if prerequisites not met, None otherwise
    """
    step_order = list(PipelineStep)
    step_index = step_order.index(step)

    # Build a map of step -> status
    status_map = {s.step: s.status for s in steps}

    # Check all previous steps
    for prev_step in step_order[:step_index]:
        prev_status = status_map.get(prev_step)
        if prev_status not in (StepStatus.COMPLETED, StepStatus.SKIPPED):
            return f"Step '{step.value}' requires '{prev_step.value}' to be completed first"

    return None


@router.get("/status", response_model=PipelineStatusResponse)
def get_pipeline_status(
    run: Annotated[RunMetadata, Depends(get_run_or_404)],
    registry: Annotated[RunRegistry, Depends(get_registry)],
) -> PipelineStatusResponse:
    """Get the current pipeline status for a run."""
    steps = registry.get_pipeline_steps(run.run_id)

    # If no steps exist yet (legacy run), initialize them
    if not steps:
        registry.init_pipeline_steps(run.run_id)
        steps = registry.get_pipeline_steps(run.run_id)

    return PipelineStatusResponse(
        run_id=run.run_id,
        run_status=run.status,
        steps=steps,
        progress_percent=_calculate_progress(steps),
    )


async def _status_event_generator(
    request: Request,
    run_id: str,
    registry: RunRegistry,
) -> AsyncGenerator[dict[str, Any], None]:
    """Generate SSE events for pipeline status updates.

    Emits status events every 500ms when status changes, and a done event
    when the pipeline completes or fails.
    """
    last_status_json: str | None = None
    last_emit = time.monotonic()
    ping_interval = 10.0

    while True:
        # Check if client disconnected
        if await request.is_disconnected():
            break

        # Get current status
        run = registry.get_run(run_id)
        if run is None:
            yield {"event": "error", "data": json.dumps({"error": "Run not found"})}
            break

        steps = registry.get_pipeline_steps(run_id)
        if not steps:
            registry.init_pipeline_steps(run_id)
            steps = registry.get_pipeline_steps(run_id)

        status_response = PipelineStatusResponse(
            run_id=run_id,
            run_status=run.status,
            steps=steps,
            progress_percent=_calculate_progress(steps),
        )

        # Serialize status (excluding output to reduce payload size)
        status_dict = status_response.model_dump(mode="json")
        # Strip large output fields from SSE to reduce bandwidth
        for step in status_dict.get("steps", []):
            if step.get("output"):
                step["output"] = step["output"][-500:] if len(step["output"]) > 500 else step["output"]

        current_status_json = json.dumps(status_dict, sort_keys=True)

        now = time.monotonic()

        # Only emit if status changed
        if current_status_json != last_status_json:
            last_status_json = current_status_json
            yield {"event": "status", "data": json.dumps(status_dict)}
            last_emit = now

        # Send heartbeat to keep SSE alive through proxies
        if now - last_emit >= ping_interval:
            yield {"event": "ping", "data": "{}"}
            last_emit = now

        # Check if pipeline is done
        is_done = run.status in (RunStatus.COMPLETED, RunStatus.FAILED) or all(
            s.status in (StepStatus.COMPLETED, StepStatus.FAILED, StepStatus.SKIPPED)
            for s in steps
        )

        if is_done:
            yield {"event": "done", "data": json.dumps({"run_status": run.status.value})}
            break

        # Wait before next poll
        await asyncio.sleep(0.5)


@router.get("/stream")
async def stream_pipeline_status(
    request: Request,
    run: Annotated[RunMetadata, Depends(get_run_or_404)],
    registry: Annotated[RunRegistry, Depends(get_registry)],
) -> EventSourceResponse:
    """Stream pipeline status updates via Server-Sent Events.

    Emits events:
    - status: Pipeline status update (when changed)
    - done: Pipeline completed or failed (closes stream)
    - error: Error occurred
    """
    return EventSourceResponse(
        _status_event_generator(request, run.run_id, registry),
        media_type="text/event-stream",
    )


@router.post("/start", status_code=status.HTTP_202_ACCEPTED)
def start_pipeline(
    run: Annotated[RunMetadata, Depends(get_run_or_404)],
    registry: Annotated[RunRegistry, Depends(get_registry)],
    background_tasks: BackgroundTasks,
    request: TriggerPipelineRequest | None = None,
    use_queue: bool = False,
) -> dict[str, Any]:
    """Start the full pipeline for a run.

    Queues all pipeline steps to run in sequence. By default uses background tasks
    for immediate execution. Set use_queue=True to use file-based queue for
    restart resilience (requires separate worker process).
    """
    # Use default request if none provided
    if request is None:
        request = TriggerPipelineRequest()

    # Check if pipeline is already running
    if run.status == RunStatus.RUNNING:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Pipeline is already running",
        )

    # Ensure pipeline steps are initialized
    steps = registry.get_pipeline_steps(run.run_id)
    if not steps:
        registry.init_pipeline_steps(run.run_id)

    # Reset any failed steps to pending
    for step in PipelineStep:
        registry.update_step_status(run.run_id, step, StepStatus.PENDING)

    if use_queue:
        # Use file-based queue for restart resilience
        queue = get_queue()
        task_id = queue.enqueue(
            run_id=run.run_id,
            video_path=run.video_path,
            run_root=run.run_root,
            video_basename=run.video_basename,
            request=request.model_dump(),
            step=None,  # Full pipeline
        )
        return {
            "message": "Pipeline queued",
            "run_id": run.run_id,
            "task_id": task_id,
            "status_url": f"/runs/{run.run_id}/pipeline/status",
        }
    else:
        # Use background task for immediate execution (legacy behavior)
        background_tasks.add_task(
            execute_pipeline,
            registry=registry,
            run_id=run.run_id,
            video_path=run.video_path,
            run_root=run.run_root,
            video_basename=run.video_basename,
            request=request,
        )
        return {
            "message": "Pipeline started",
            "run_id": run.run_id,
            "status_url": f"/runs/{run.run_id}/pipeline/status",
        }


@router.post("/step/{step_name}", status_code=status.HTTP_202_ACCEPTED)
def run_single_step(
    step_name: str,
    run: Annotated[RunMetadata, Depends(get_run_or_404)],
    registry: Annotated[RunRegistry, Depends(get_registry)],
    background_tasks: BackgroundTasks,
    request: TriggerPipelineRequest | None = None,
    use_queue: bool = False,
) -> dict[str, Any]:
    """Run a single pipeline step.

    Validates that prerequisites are met before running. By default uses background
    tasks for immediate execution. Set use_queue=True to use file-based queue for
    restart resilience (requires separate worker process).
    """
    # Validate step name
    try:
        step = PipelineStep(step_name)
    except ValueError:
        valid_steps = [s.value for s in PipelineStep]
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid step '{step_name}'. Valid steps: {valid_steps}",
        ) from None

    # Use default request if none provided
    if request is None:
        request = TriggerPipelineRequest()

    # Ensure pipeline steps are initialized
    steps = registry.get_pipeline_steps(run.run_id)
    if not steps:
        registry.init_pipeline_steps(run.run_id)
        steps = registry.get_pipeline_steps(run.run_id)

    # Check if this specific step is already running
    step_info = next((s for s in steps if s.step == step), None)
    if step_info and step_info.status == StepStatus.RUNNING:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Step '{step_name}' is already running",
        )

    # Check prerequisites
    error = _check_step_prerequisites(step, steps)
    if error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error,
        )

    if use_queue:
        # Use file-based queue for restart resilience
        queue = get_queue()
        task_id = queue.enqueue(
            run_id=run.run_id,
            video_path=run.video_path,
            run_root=run.run_root,
            video_basename=run.video_basename,
            request=request.model_dump(),
            step=step_name,
        )
        return {
            "message": f"Step '{step_name}' queued",
            "run_id": run.run_id,
            "step": step_name,
            "task_id": task_id,
            "status_url": f"/runs/{run.run_id}/pipeline/status",
        }
    else:
        # Use background task for immediate execution (legacy behavior)
        background_tasks.add_task(
            execute_single_step,
            registry=registry,
            run_id=run.run_id,
            video_path=run.video_path,
            run_root=run.run_root,
            video_basename=run.video_basename,
            step=step,
            request=request,
        )
        return {
            "message": f"Step '{step_name}' started",
            "run_id": run.run_id,
            "step": step_name,
            "status_url": f"/runs/{run.run_id}/pipeline/status",
        }


@router.post("/step/{step_name}/cancel", status_code=status.HTTP_200_OK)
def cancel_running_step(
    step_name: str,
    run: Annotated[RunMetadata, Depends(get_run_or_404)],
    registry: Annotated[RunRegistry, Depends(get_registry)],
) -> dict[str, str]:
    """Cancel a running pipeline step."""
    # Validate step name
    try:
        step = PipelineStep(step_name)
    except ValueError:
        valid_steps = [s.value for s in PipelineStep]
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid step '{step_name}'. Valid steps: {valid_steps}",
        ) from None

    if run.status != RunStatus.RUNNING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Pipeline is not running",
        )

    steps = registry.get_pipeline_steps(run.run_id)
    running_step = next((s for s in steps if s.status == StepStatus.RUNNING), None)
    if running_step is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="No running step found",
        )

    if running_step.step != step:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Step '{running_step.step.value}' is running, not '{step_name}'",
        )

    cancelled = cancel_pipeline(run.run_id)
    if cancelled:
        registry.update_status(run.run_id, RunStatus.FAILED)
        registry.update_step_status(
            run.run_id,
            step,
            StepStatus.FAILED,
            error_message="Cancelled by user",
        )
        return {
            "message": f"Step '{step_name}' cancelled",
            "run_id": run.run_id,
            "step": step_name,
        }

    return {
        "message": "No running process found (may have already completed)",
        "run_id": run.run_id,
        "step": step_name,
    }


@router.post("/cancel", status_code=status.HTTP_200_OK)
def cancel_running_pipeline(
    run: Annotated[RunMetadata, Depends(get_run_or_404)],
    registry: Annotated[RunRegistry, Depends(get_registry)],
) -> dict[str, str]:
    """Cancel a running pipeline.

    Terminates any running subprocess and marks the current step as failed.
    """
    # Check if pipeline is running
    if run.status != RunStatus.RUNNING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Pipeline is not running",
        )

    # Attempt to cancel the subprocess
    cancelled = cancel_pipeline(run.run_id)

    if cancelled:
        # Update run status
        registry.update_status(run.run_id, RunStatus.FAILED)

        # Find and update the running step
        steps = registry.get_pipeline_steps(run.run_id)
        for step_info in steps:
            if step_info.status == StepStatus.RUNNING:
                registry.update_step_status(
                    run.run_id,
                    step_info.step,
                    StepStatus.FAILED,
                    error_message="Cancelled by user",
                )
                break

        return {
            "message": "Pipeline cancelled",
            "run_id": run.run_id,
        }
    else:
        # No subprocess found, but pipeline was marked as running
        # This can happen if the process already finished
        return {
            "message": "No running process found (may have already completed)",
            "run_id": run.run_id,
        }
