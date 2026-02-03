"""Background pipeline executor for running analytics steps."""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path
from threading import Lock
from typing import TYPE_CHECKING

from dotenv import dotenv_values

from inf3_analytics.api.models import PipelineStep, RunStatus, StepStatus, TriggerPipelineRequest

if TYPE_CHECKING:
    from inf3_analytics.api.registry import RunRegistry


STEP_TIMEOUT_SECONDS = 3600  # 1 hour per step

# Map engine names to required extras
ENGINE_EXTRAS: dict[str, list[str]] = {
    "openai": ["openai"],
    "gemini": ["gemini"],
    "faster-whisper": [],
    "rules": [],
    "baseline_quality": ["cv"],
}

# Track running processes for cancellation
_running_processes: dict[str, subprocess.Popen[str]] = {}
_process_lock = Lock()

_FRAME_TOTAL_RE = re.compile(r"Frames to process:\s*(\d+)")
_FRAME_LINE_RE = re.compile(r"^\s*Frame\s+\d+:", re.MULTILINE)
_EXTRACT_EVENT_RE = re.compile(r"\[(\d+)/(\d+)\]\s+Extracting frames for:", re.MULTILINE)

# Structured progress format: ##PROGRESS##{"current":5,"total":10,"unit":"frames"}##
_STRUCTURED_PROGRESS_RE = re.compile(r"##PROGRESS##(.+?)##")


def _register_process(run_id: str, process: subprocess.Popen[str]) -> None:
    """Register a running process for a run."""
    with _process_lock:
        _running_processes[run_id] = process


def _unregister_process(run_id: str) -> None:
    """Unregister a process when done."""
    with _process_lock:
        _running_processes.pop(run_id, None)


def cancel_pipeline(run_id: str) -> bool:
    """Cancel a running pipeline by terminating its subprocess.

    Args:
        run_id: The run identifier

    Returns:
        True if a process was terminated, False if no process was running
    """
    with _process_lock:
        process = _running_processes.get(run_id)
        if process is None:
            return False

        try:
            # Try graceful termination first
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                # Force kill if it doesn't terminate
                process.kill()
                process.wait()
            return True
        except Exception:
            return False


def is_pipeline_running(run_id: str) -> bool:
    """Check if a pipeline is currently running.

    Args:
        run_id: The run identifier

    Returns:
        True if a process is running for this run
    """
    with _process_lock:
        process = _running_processes.get(run_id)
        if process is None:
            return False
        # Check if process is still alive
        return process.poll() is None


def _get_subprocess_env() -> dict[str, str]:
    """Get environment variables for subprocess, including .env file values.

    Returns:
        Environment dict with current env merged with .env file values
    """
    # Start with current environment
    env = os.environ.copy()

    # Look for .env file in current directory or parent directories
    cwd = Path.cwd()
    for path in [cwd, *cwd.parents]:
        env_file = path / ".env"
        if env_file.exists():
            # Load .env values and merge (don't override existing env vars)
            dotenv_vars = dotenv_values(env_file)
            for key, value in dotenv_vars.items():
                if key not in env and value is not None:
                    env[key] = value
            break

    return env


def _build_uv_command(module: str, args: list[str], extras: list[str]) -> list[str]:
    """Build a uv run command with extras.

    Args:
        module: Python module to run (e.g., "inf3_analytics.cli.transcribe")
        args: Arguments to pass to the module
        extras: List of extras to include (e.g., ["openai", "cv"])

    Returns:
        Complete command list for subprocess
    """
    # Check if uv is available
    uv_path = shutil.which("uv")
    if uv_path:
        cmd = [uv_path, "run"]
        for extra in extras:
            cmd.extend(["--extra", extra])
        cmd.extend(["python", "-m", module])
        cmd.extend(args)
        return cmd

    # Fall back to direct python execution if uv not available
    return [sys.executable, "-m", module] + args


def _run_subprocess(
    cmd: list[str],
    timeout: int = STEP_TIMEOUT_SECONDS,
    on_output: Callable[[str], None] | None = None,
    run_id: str | None = None,
    registry: "RunRegistry | None" = None,
    step: PipelineStep | None = None,
) -> tuple[bool, str]:
    """Run a subprocess command and return success status and output.

    Args:
        cmd: Command and arguments
        timeout: Timeout in seconds
        on_output: Optional callback called periodically with accumulated output
        run_id: Optional run ID for process tracking (enables cancellation)
        registry: Optional registry to store PID
        step: Optional step to associate with PID

    Returns:
        Tuple of (success, output_or_error)
    """
    import select
    import time

    process: subprocess.Popen[str] | None = None
    try:
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            env=_get_subprocess_env(),
            bufsize=1,  # Line buffered
        )

        # Register process for cancellation
        if run_id:
            _register_process(run_id, process)

        # Store PID in registry for orphan detection
        if registry and run_id and step and process.pid:
            registry.update_step_pid(run_id, step, process.pid)

        output_lines: list[str] = []
        start_time = time.time()
        last_update = start_time
        cancelled = False

        while True:
            # Check timeout
            elapsed = time.time() - start_time
            if elapsed > timeout:
                process.kill()
                process.wait()
                output_lines.append(f"\n[Step timed out after {timeout} seconds]")
                return False, "".join(output_lines)

            # Check if process has finished
            poll_result = process.poll()
            if poll_result is not None:
                # Check if it was killed by signal (cancellation)
                if poll_result < 0:
                    cancelled = True
                # Read any remaining output
                if process.stdout:
                    remaining = process.stdout.read()
                    if remaining:
                        output_lines.append(remaining)
                break

            # Try to read output (non-blocking on Unix)
            if process.stdout:
                try:
                    # Use select for non-blocking read on Unix
                    ready, _, _ = select.select([process.stdout], [], [], 0.5)
                    if ready:
                        line = process.stdout.readline()
                        if line:
                            output_lines.append(line)
                except (ValueError, OSError):
                    # select might fail on some platforms, fall back to blocking read
                    time.sleep(0.1)

            # Call output callback every 2 seconds
            now = time.time()
            if on_output and (now - last_update) >= 2.0:
                on_output("".join(output_lines))
                last_update = now

        # Final output callback
        full_output = "".join(output_lines)
        if cancelled:
            full_output += "\n[Cancelled by user]"
        if on_output:
            on_output(full_output)

        if cancelled:
            return False, full_output
        if process.returncode == 0:
            return True, full_output
        return False, full_output or f"Exit code: {process.returncode}"

    except Exception as e:
        return False, str(e)
    finally:
        # Unregister process
        if run_id:
            _unregister_process(run_id)


def _get_transcript_path(run_root: Path, video_basename: str) -> Path:
    """Get the path to the transcript JSON file."""
    return run_root / f"{video_basename}.json"


def _get_events_path(run_root: Path, video_basename: str) -> Path:
    """Get the path to the events JSON file."""
    return run_root / "events" / f"{video_basename}_events.json"


def _get_event_frames_dir(run_root: Path) -> Path:
    """Get the path to the event frames directory."""
    return run_root / "event_frames"


def _get_frame_analytics_dir(run_root: Path) -> Path:
    """Get the path to the frame analytics directory."""
    return run_root / "frame_analytics"


def run_transcription(
    video_path: Path,
    run_root: Path,
    engine: str = "openai",
    on_output: Callable[[str], None] | None = None,
    run_id: str | None = None,
    registry: "RunRegistry | None" = None,
) -> tuple[bool, str]:
    """Run the transcription step.

    Args:
        video_path: Path to video file
        run_root: Output directory for the run
        engine: Transcription engine to use
        on_output: Optional callback for streaming output
        run_id: Optional run ID for process tracking
        registry: Optional registry for PID tracking

    Returns:
        Tuple of (success, message)
    """
    extras = ENGINE_EXTRAS.get(engine, [])
    args = [
        "--video",
        str(video_path),
        "--out",
        str(run_root),
        "--engine",
        engine,
        "--format",
        "json,txt,srt",
    ]
    cmd = _build_uv_command("inf3_analytics.cli.transcribe", args, extras)
    return _run_subprocess(
        cmd, on_output=on_output, run_id=run_id, registry=registry, step=PipelineStep.TRANSCRIBE
    )


def run_event_extraction(
    run_root: Path,
    video_basename: str,
    engine: str = "openai",
    on_output: Callable[[str], None] | None = None,
    run_id: str | None = None,
    registry: "RunRegistry | None" = None,
) -> tuple[bool, str]:
    """Run the event extraction step.

    Args:
        run_root: Output directory for the run
        video_basename: Video filename without extension
        engine: Event extraction engine to use
        on_output: Optional callback for streaming output
        run_id: Optional run ID for process tracking
        registry: Optional registry for PID tracking

    Returns:
        Tuple of (success, message)
    """
    transcript_path = _get_transcript_path(run_root, video_basename)
    if not transcript_path.exists():
        return False, f"Transcript not found: {transcript_path}"

    events_dir = run_root / "events"
    extras = ENGINE_EXTRAS.get(engine, [])
    args = [
        "--transcript",
        str(transcript_path),
        "--out",
        str(events_dir),
        "--engine",
        engine,
        "--format",
        "json,md",
    ]
    cmd = _build_uv_command("inf3_analytics.cli.extract_events", args, extras)
    return _run_subprocess(
        cmd, on_output=on_output, run_id=run_id, registry=registry, step=PipelineStep.EXTRACT_EVENTS
    )


def run_frame_extraction(
    video_path: Path,
    run_root: Path,
    video_basename: str,
    on_output: Callable[[str], None] | None = None,
    run_id: str | None = None,
    registry: "RunRegistry | None" = None,
) -> tuple[bool, str]:
    """Run the frame extraction step.

    Args:
        video_path: Path to video file
        run_root: Output directory for the run
        video_basename: Video filename without extension
        on_output: Optional callback for streaming output
        run_id: Optional run ID for process tracking
        registry: Optional registry for PID tracking

    Returns:
        Tuple of (success, message)
    """
    events_path = _get_events_path(run_root, video_basename)
    if not events_path.exists():
        return False, f"Events file not found: {events_path}"

    frames_dir = _get_event_frames_dir(run_root)
    # Frame extraction uses ffmpeg, no special extras needed
    args = [
        "--video",
        str(video_path),
        "--events",
        str(events_path),
        "--out",
        str(frames_dir),
    ]
    cmd = _build_uv_command("inf3_analytics.cli.extract_event_frames", args, [])
    return _run_subprocess(
        cmd, on_output=on_output, run_id=run_id, registry=registry, step=PipelineStep.EXTRACT_FRAMES
    )


def run_frame_analytics(
    run_root: Path,
    video_basename: str,
    engine: str = "gemini",
    on_output: Callable[[str], None] | None = None,
    run_id: str | None = None,
    registry: "RunRegistry | None" = None,
) -> tuple[bool, str]:
    """Run the frame analytics step.

    Args:
        run_root: Output directory for the run
        video_basename: Video filename without extension
        engine: Frame analytics engine to use
        on_output: Optional callback for streaming output
        run_id: Optional run ID for process tracking
        registry: Optional registry for PID tracking

    Returns:
        Tuple of (success, message)
    """
    frames_dir = _get_event_frames_dir(run_root)
    if not frames_dir.exists():
        return False, f"Event frames directory not found: {frames_dir}"

    events_path = _get_events_path(run_root, video_basename)
    analytics_dir = _get_frame_analytics_dir(run_root)

    extras = ENGINE_EXTRAS.get(engine, [])
    args = [
        "--event-frames",
        str(frames_dir),
        "--out",
        str(analytics_dir),
        "--engine",
        engine,
    ]
    if events_path.exists():
        args.extend(["--events", str(events_path)])

    cmd = _build_uv_command("inf3_analytics.cli.run_frame_analytics", args, extras)
    return _run_subprocess(
        cmd, on_output=on_output, run_id=run_id, registry=registry, step=PipelineStep.FRAME_ANALYTICS
    )


def _make_output_callback(
    registry: RunRegistry,
    run_id: str,
    step: PipelineStep,
) -> Callable[[str], None]:
    """Create a callback that updates step output in the database.

    Args:
        registry: Run registry
        run_id: Run identifier
        step: Pipeline step

    Returns:
        Callback function that updates step output
    """

    def _parse_structured_progress(
        output: str,
    ) -> tuple[int | None, int | None, str | None, str | None]:
        """Parse structured progress from ##PROGRESS##...## lines.

        Returns:
            Tuple of (current, total, unit, message) from last progress line,
            or (None, None, None, None) if no structured progress found.
        """
        import json as json_module

        last_match = None
        for match in _STRUCTURED_PROGRESS_RE.finditer(output):
            last_match = match

        if last_match is None:
            return None, None, None, None

        try:
            data = json_module.loads(last_match.group(1))
            return (
                data.get("current"),
                data.get("total"),
                data.get("unit"),
                data.get("message"),
            )
        except (json_module.JSONDecodeError, KeyError):
            return None, None, None, None

    def _extract_progress_legacy(
        output: str,
    ) -> tuple[int | None, int | None, str | None, str | None]:
        """Extract progress using legacy regex patterns (fallback)."""
        if step == PipelineStep.FRAME_ANALYTICS:
            total_match = None
            for match in _FRAME_TOTAL_RE.finditer(output):
                total_match = match
            if total_match is None:
                return None, None, None, None
            total = int(total_match.group(1))
            current = len(_FRAME_LINE_RE.findall(output))
            if current > total:
                current = total
            return current, total, "frames", "Analyzing frames"

        if step == PipelineStep.EXTRACT_FRAMES:
            progress_match = None
            for match in _EXTRACT_EVENT_RE.finditer(output):
                progress_match = match
            if progress_match is None:
                return None, None, None, None
            current = int(progress_match.group(1))
            total = int(progress_match.group(2))
            return current, total, "events", "Extracting frames"

        return None, None, None, None

    def _extract_progress(output: str) -> tuple[int | None, int | None, str | None, str | None]:
        """Extract progress details from step output.

        Tries structured ##PROGRESS## format first, falls back to legacy regex.
        """
        # Try structured progress first
        result = _parse_structured_progress(output)
        if result[0] is not None:
            return result

        # Fall back to legacy regex parsing
        return _extract_progress_legacy(output)

    def callback(output: str) -> None:
        progress_current, progress_total, progress_unit, progress_message = _extract_progress(output)
        registry.update_step_progress(
            run_id,
            step,
            progress_current=progress_current,
            progress_total=progress_total,
            progress_unit=progress_unit,
            progress_message=progress_message,
            output=output,
        )

    return callback


def execute_pipeline(
    registry: RunRegistry,
    run_id: str,
    video_path: str,
    run_root: str,
    video_basename: str,
    request: TriggerPipelineRequest,
) -> None:
    """Execute the pipeline steps in sequence.

    This is designed to be run as a background task.

    Args:
        registry: Run registry for status updates
        run_id: Run identifier
        video_path: Path to video file
        run_root: Output directory for the run
        video_basename: Video filename without extension
        request: Pipeline configuration
    """
    video_path_obj = Path(video_path)
    run_root_obj = Path(run_root)

    # Determine which steps to run
    steps_to_run = request.steps or list(PipelineStep)

    # Update run status to running
    registry.update_status(run_id, RunStatus.RUNNING)

    failed = False

    for step in PipelineStep:
        if step not in steps_to_run:
            registry.update_step_status(run_id, step, StepStatus.SKIPPED)
            continue

        # Mark step as running
        registry.update_step_status(run_id, step, StepStatus.RUNNING)

        # Create output callback for streaming updates
        on_output = _make_output_callback(registry, run_id, step)

        # Execute the step
        if step == PipelineStep.TRANSCRIBE:
            success, message = run_transcription(
                video_path_obj, run_root_obj, request.transcription_engine, on_output, run_id, registry
            )
        elif step == PipelineStep.EXTRACT_EVENTS:
            success, message = run_event_extraction(
                run_root_obj, video_basename, request.event_engine, on_output, run_id, registry
            )
        elif step == PipelineStep.EXTRACT_FRAMES:
            success, message = run_frame_extraction(
                video_path_obj, run_root_obj, video_basename, on_output, run_id, registry
            )
        elif step == PipelineStep.FRAME_ANALYTICS:
            success, message = run_frame_analytics(
                run_root_obj, video_basename, request.frame_analytics_engine, on_output, run_id, registry
            )
        else:
            success, message = False, f"Unknown step: {step}"

        # Check if cancelled
        cancelled = "[Cancelled by user]" in message

        # Update step status with output
        if success:
            registry.update_step_status(
                run_id, step, StepStatus.COMPLETED, output=message
            )
        elif cancelled:
            registry.update_step_status(
                run_id, step, StepStatus.FAILED, error_message="Cancelled by user", output=message
            )
            failed = True
            break
        else:
            registry.update_step_status(
                run_id, step, StepStatus.FAILED, error_message=message, output=message
            )
            failed = True
            # Stop pipeline on failure
            break

    # Update run status
    if failed:
        registry.update_status(run_id, RunStatus.FAILED)
    else:
        registry.update_status(run_id, RunStatus.COMPLETED)


def execute_single_step(
    registry: RunRegistry,
    run_id: str,
    video_path: str,
    run_root: str,
    video_basename: str,
    step: PipelineStep,
    request: TriggerPipelineRequest,
) -> tuple[bool, str]:
    """Execute a single pipeline step.

    Args:
        registry: Run registry for status updates
        run_id: Run identifier
        video_path: Path to video file
        run_root: Output directory for the run
        video_basename: Video filename without extension
        step: The step to execute
        request: Pipeline configuration

    Returns:
        Tuple of (success, message)
    """
    video_path_obj = Path(video_path)
    run_root_obj = Path(run_root)

    # Mark step as running
    registry.update_step_status(run_id, step, StepStatus.RUNNING)
    registry.update_status(run_id, RunStatus.RUNNING)

    # Create output callback for streaming updates
    on_output = _make_output_callback(registry, run_id, step)

    # Execute the step
    if step == PipelineStep.TRANSCRIBE:
        success, message = run_transcription(
            video_path_obj, run_root_obj, request.transcription_engine, on_output, run_id, registry
        )
    elif step == PipelineStep.EXTRACT_EVENTS:
        success, message = run_event_extraction(
            run_root_obj, video_basename, request.event_engine, on_output, run_id, registry
        )
    elif step == PipelineStep.EXTRACT_FRAMES:
        success, message = run_frame_extraction(
            video_path_obj, run_root_obj, video_basename, on_output, run_id, registry
        )
    elif step == PipelineStep.FRAME_ANALYTICS:
        success, message = run_frame_analytics(
            run_root_obj, video_basename, request.frame_analytics_engine, on_output, run_id, registry
        )
    else:
        success, message = False, f"Unknown step: {step}"

    # Check if cancelled
    cancelled = "[Cancelled by user]" in message

    # Update step status with output
    if success:
        registry.update_step_status(
            run_id, step, StepStatus.COMPLETED, output=message
        )
    elif cancelled:
        registry.update_step_status(
            run_id, step, StepStatus.FAILED, error_message="Cancelled by user", output=message
        )
    else:
        registry.update_step_status(
            run_id, step, StepStatus.FAILED, error_message=message, output=message
        )

    # Check if all steps are completed
    steps = registry.get_pipeline_steps(run_id)
    all_completed = all(s.status == StepStatus.COMPLETED for s in steps)
    any_failed = any(s.status == StepStatus.FAILED for s in steps)

    if all_completed:
        registry.update_status(run_id, RunStatus.COMPLETED)
    elif any_failed:
        registry.update_status(run_id, RunStatus.FAILED)
    else:
        # Still have pending steps, keep as created (unless currently running)
        current_run = registry.get_run(run_id)
        if current_run and current_run.status == RunStatus.RUNNING:
            registry.update_status(run_id, RunStatus.CREATED)

    return success, message
