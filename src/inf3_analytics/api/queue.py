"""File-based task queue for pipeline execution.

Provides restart resilience by persisting tasks to the filesystem.

Directory structure:
    .inf3-analytics/queue/
        pending/      # Tasks waiting to run
        processing/   # Tasks currently being processed
        completed/    # Finished tasks
        failed/       # Failed tasks with error info
"""

import json
import time
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from filelock import FileLock


@dataclass
class Task:
    """A queued pipeline task."""

    task_id: str
    run_id: str
    video_path: str
    run_root: str
    video_basename: str
    request: dict[str, Any]
    step: str | None  # None for full pipeline, step name for single step
    created_at: str
    started_at: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "task_id": self.task_id,
            "run_id": self.run_id,
            "video_path": self.video_path,
            "run_root": self.run_root,
            "video_basename": self.video_basename,
            "request": self.request,
            "step": self.step,
            "created_at": self.created_at,
            "started_at": self.started_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Task":
        """Create from dictionary."""
        return cls(
            task_id=data["task_id"],
            run_id=data["run_id"],
            video_path=data["video_path"],
            run_root=data["run_root"],
            video_basename=data["video_basename"],
            request=data["request"],
            step=data.get("step"),
            created_at=data["created_at"],
            started_at=data.get("started_at"),
        )


class TaskQueue:
    """File-based task queue with atomic operations via file locking."""

    def __init__(self, base_dir: Path | None = None) -> None:
        """Initialize the queue.

        Args:
            base_dir: Base directory for queue storage.
                      Defaults to .inf3-analytics/queue in current directory.
        """
        if base_dir is None:
            base_dir = Path.cwd() / ".inf3-analytics" / "queue"

        self._base_dir = base_dir
        self._pending_dir = base_dir / "pending"
        self._processing_dir = base_dir / "processing"
        self._completed_dir = base_dir / "completed"
        self._failed_dir = base_dir / "failed"
        self._lock_file = base_dir / ".queue.lock"

        # Ensure directories exist
        for d in [
            self._pending_dir,
            self._processing_dir,
            self._completed_dir,
            self._failed_dir,
        ]:
            d.mkdir(parents=True, exist_ok=True)

    def _get_lock(self) -> FileLock:
        """Get a file lock for atomic queue operations."""
        return FileLock(self._lock_file, timeout=10)

    def enqueue(
        self,
        run_id: str,
        video_path: str,
        run_root: str,
        video_basename: str,
        request: dict[str, Any],
        step: str | None = None,
    ) -> str:
        """Add a task to the pending queue.

        Args:
            run_id: Run identifier
            video_path: Path to video file
            run_root: Output directory for the run
            video_basename: Video filename without extension
            request: Pipeline request configuration
            step: Specific step to run (None for full pipeline)

        Returns:
            Task ID
        """
        task_id = f"task_{datetime.now(UTC).strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"

        task = Task(
            task_id=task_id,
            run_id=run_id,
            video_path=video_path,
            run_root=run_root,
            video_basename=video_basename,
            request=request,
            step=step,
            created_at=datetime.now(UTC).isoformat(),
        )

        task_file = self._pending_dir / f"{task_id}.json"

        with self._get_lock(), open(task_file, "w") as f:
            json.dump(task.to_dict(), f, indent=2)

        return task_id

    def claim_next(self) -> Task | None:
        """Claim the next pending task (atomic).

        Moves task from pending to processing directory.

        Returns:
            Task if one was claimed, None if queue is empty
        """
        with self._get_lock():
            # Get oldest pending task by filename (timestamp-based IDs sort chronologically)
            pending_files = sorted(self._pending_dir.glob("*.json"))
            if not pending_files:
                return None

            task_file = pending_files[0]
            with open(task_file) as f:
                task_data = json.load(f)

            task = Task.from_dict(task_data)
            task.started_at = datetime.now(UTC).isoformat()

            # Move to processing
            processing_file = self._processing_dir / task_file.name
            with open(processing_file, "w") as f:
                json.dump(task.to_dict(), f, indent=2)

            task_file.unlink()
            return task

    def complete(self, task_id: str) -> bool:
        """Mark a task as completed.

        Moves task from processing to completed directory.

        Args:
            task_id: Task identifier

        Returns:
            True if task was moved, False if not found
        """
        with self._get_lock():
            processing_file = self._processing_dir / f"{task_id}.json"
            if not processing_file.exists():
                return False

            completed_file = self._completed_dir / f"{task_id}.json"
            processing_file.rename(completed_file)
            return True

    def fail(self, task_id: str, error: str) -> bool:
        """Mark a task as failed.

        Moves task from processing to failed directory and adds error info.

        Args:
            task_id: Task identifier
            error: Error message

        Returns:
            True if task was moved, False if not found
        """
        with self._get_lock():
            processing_file = self._processing_dir / f"{task_id}.json"
            if not processing_file.exists():
                return False

            with open(processing_file) as f:
                task_data = json.load(f)

            task_data["error"] = error
            task_data["failed_at"] = datetime.now(UTC).isoformat()

            failed_file = self._failed_dir / f"{task_id}.json"
            with open(failed_file, "w") as f:
                json.dump(task_data, f, indent=2)

            processing_file.unlink()
            return True

    def recover_stale(self, max_age_seconds: int = 3600) -> int:
        """Move stale processing tasks back to pending.

        Tasks that have been processing for longer than max_age_seconds
        are considered stale (likely from a crashed worker).

        Args:
            max_age_seconds: Maximum age in seconds before task is considered stale

        Returns:
            Number of tasks recovered
        """
        now = time.time()
        recovered = 0

        with self._get_lock():
            for processing_file in self._processing_dir.glob("*.json"):
                with open(processing_file) as f:
                    task_data = json.load(f)

                started_at = task_data.get("started_at")
                if started_at:
                    started_time = datetime.fromisoformat(started_at.replace("Z", "+00:00"))
                    age_seconds = now - started_time.timestamp()

                    if age_seconds > max_age_seconds:
                        # Move back to pending
                        task_data["started_at"] = None
                        task_data["recovery_note"] = (
                            f"Recovered from stale processing state after {age_seconds:.0f}s"
                        )

                        pending_file = self._pending_dir / processing_file.name
                        with open(pending_file, "w") as f:
                            json.dump(task_data, f, indent=2)

                        processing_file.unlink()
                        recovered += 1

        return recovered

    def get_pending_count(self) -> int:
        """Get the number of pending tasks."""
        return len(list(self._pending_dir.glob("*.json")))

    def get_processing_count(self) -> int:
        """Get the number of processing tasks."""
        return len(list(self._processing_dir.glob("*.json")))

    def get_task(self, task_id: str) -> Task | None:
        """Get a task by ID from any queue directory.

        Args:
            task_id: Task identifier

        Returns:
            Task if found, None otherwise
        """
        for queue_dir in [
            self._pending_dir,
            self._processing_dir,
            self._completed_dir,
            self._failed_dir,
        ]:
            task_file = queue_dir / f"{task_id}.json"
            if task_file.exists():
                with open(task_file) as f:
                    return Task.from_dict(json.load(f))
        return None

    def get_task_status(self, task_id: str) -> str | None:
        """Get the status of a task.

        Args:
            task_id: Task identifier

        Returns:
            Status string ('pending', 'processing', 'completed', 'failed') or None
        """
        for status, queue_dir in [
            ("pending", self._pending_dir),
            ("processing", self._processing_dir),
            ("completed", self._completed_dir),
            ("failed", self._failed_dir),
        ]:
            if (queue_dir / f"{task_id}.json").exists():
                return status
        return None
