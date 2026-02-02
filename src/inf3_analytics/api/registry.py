"""SQLite-backed run registry."""

import json
import sqlite3
import uuid
from datetime import UTC, datetime
from pathlib import Path
from threading import Lock
from typing import Any

from inf3_analytics.api.models import (
    PipelineStep,
    PipelineStepInfo,
    RunMetadata,
    RunStatus,
    StepStatus,
)

SQLITE_HEADER = b"SQLite format 3\x00"


class RunRegistry:
    """Thread-safe SQLite registry for pipeline runs."""

    def __init__(self, registry_path: Path) -> None:
        """Initialize the registry.

        Args:
            registry_path: Path to the SQLite registry file
        """
        self._path = registry_path
        self._lock = Lock()
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._migrate_json_if_needed()
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS runs (
                    run_id TEXT PRIMARY KEY,
                    video_path TEXT NOT NULL,
                    run_root TEXT NOT NULL,
                    video_basename TEXT NOT NULL,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS pipeline_steps (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_id TEXT NOT NULL,
                    step TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'pending',
                    started_at TEXT,
                    completed_at TEXT,
                    error_message TEXT,
                    output TEXT,
                    FOREIGN KEY (run_id) REFERENCES runs(run_id),
                    UNIQUE(run_id, step)
                )
                """
            )
            # Add output column if it doesn't exist (migration for existing DBs)
            try:
                conn.execute("ALTER TABLE pipeline_steps ADD COLUMN output TEXT")
            except Exception:
                pass  # Column already exists

    def _is_sqlite_file(self) -> bool:
        if not self._path.exists():
            return False
        try:
            with open(self._path, "rb") as f:
                header = f.read(len(SQLITE_HEADER))
            return header == SQLITE_HEADER
        except OSError:
            return False

    def _migrate_json_if_needed(self) -> None:
        if not self._path.exists():
            return
        if self._is_sqlite_file():
            return

        try:
            with open(self._path, encoding="utf-8") as f:
                data = json.load(f)
        except (OSError, json.JSONDecodeError):
            return

        runs = data.get("runs")
        if not isinstance(runs, dict):
            return

        backup_path = self._path.with_suffix(
            self._path.suffix + f".bak-{datetime.now(UTC).strftime('%Y%m%d_%H%M%S')}"
        )
        self._path.replace(backup_path)
        self._init_db()

        with self._connect() as conn:
            for run_data in runs.values():
                try:
                    conn.execute(
                        """
                        INSERT OR REPLACE INTO runs
                        (run_id, video_path, run_root, video_basename, status, created_at)
                        VALUES (?, ?, ?, ?, ?, ?)
                        """,
                        (
                            run_data["run_id"],
                            run_data["video_path"],
                            run_data["run_root"],
                            run_data["video_basename"],
                            run_data["status"],
                            run_data["created_at"],
                        ),
                    )
                except KeyError:
                    continue

    def create_run(
        self,
        video_path: str,
        run_root: str,
        run_id: str | None = None,
    ) -> RunMetadata:
        """Create a new run entry.

        Args:
            video_path: Path to the video file
            run_root: Directory for pipeline outputs
            run_id: Optional custom run ID

        Returns:
            RunMetadata for the created run
        """
        with self._lock:
            if run_id is None:
                run_id = self._generate_run_id()

            resolved_video_path = Path(video_path).resolve()
            resolved_run_root = Path(run_root).resolve()
            video_basename = resolved_video_path.stem
            now = datetime.now(UTC)

            run_data = {
                "run_id": run_id,
                "video_path": str(resolved_video_path),
                "run_root": str(resolved_run_root),
                "video_basename": video_basename,
                "status": RunStatus.CREATED.value,
                "created_at": now.isoformat(),
            }

            with self._connect() as conn:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO runs
                    (run_id, video_path, run_root, video_basename, status, created_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        run_data["run_id"],
                        run_data["video_path"],
                        run_data["run_root"],
                        run_data["video_basename"],
                        run_data["status"],
                        run_data["created_at"],
                    ),
                )

            return RunMetadata(
                run_id=run_id,
                video_path=str(resolved_video_path),
                run_root=str(resolved_run_root),
                video_basename=video_basename,
                status=RunStatus.CREATED,
                created_at=now,
            )

    def get_run(self, run_id: str) -> RunMetadata | None:
        """Get a run by ID.

        Args:
            run_id: The run identifier

        Returns:
            RunMetadata if found, None otherwise
        """
        with self._lock:
            with self._connect() as conn:
                row = conn.execute(
                    "SELECT * FROM runs WHERE run_id = ?",
                    (run_id,),
                ).fetchone()
            if row is None:
                return None
            return RunMetadata(
                run_id=row["run_id"],
                video_path=row["video_path"],
                run_root=row["run_root"],
                video_basename=row["video_basename"],
                status=RunStatus(row["status"]),
                created_at=datetime.fromisoformat(row["created_at"]),
            )

    def list_runs(self) -> list[RunMetadata]:
        """List all runs.

        Returns:
            List of RunMetadata for all runs
        """
        with self._lock:
            with self._connect() as conn:
                rows = conn.execute(
                    "SELECT * FROM runs ORDER BY created_at DESC"
                ).fetchall()
            return [
                RunMetadata(
                    run_id=row["run_id"],
                    video_path=row["video_path"],
                    run_root=row["run_root"],
                    video_basename=row["video_basename"],
                    status=RunStatus(row["status"]),
                    created_at=datetime.fromisoformat(row["created_at"]),
                )
                for row in rows
            ]

    def update_status(self, run_id: str, status: RunStatus) -> bool:
        """Update the status of a run.

        Args:
            run_id: The run identifier
            status: New status

        Returns:
            True if updated, False if run not found
        """
        with self._lock:
            with self._connect() as conn:
                cur = conn.execute(
                    "UPDATE runs SET status = ? WHERE run_id = ?",
                    (status.value, run_id),
                )
                return cur.rowcount > 0

    def init_pipeline_steps(self, run_id: str) -> None:
        """Initialize pipeline steps for a run.

        Creates pending entries for all pipeline steps.

        Args:
            run_id: The run identifier
        """
        with self._lock:
            with self._connect() as conn:
                for step in PipelineStep:
                    conn.execute(
                        """
                        INSERT OR IGNORE INTO pipeline_steps (run_id, step, status)
                        VALUES (?, ?, ?)
                        """,
                        (run_id, step.value, StepStatus.PENDING.value),
                    )

    def update_step_status(
        self,
        run_id: str,
        step: PipelineStep,
        status: StepStatus,
        error_message: str | None = None,
        output: str | None = None,
    ) -> bool:
        """Update the status of a pipeline step.

        Args:
            run_id: The run identifier
            step: The pipeline step
            status: New status
            error_message: Optional error message for failed steps
            output: Optional stdout/stderr output from the step

        Returns:
            True if updated, False if step not found
        """
        with self._lock:
            now = datetime.now(UTC).isoformat()
            with self._connect() as conn:
                if status == StepStatus.RUNNING:
                    cur = conn.execute(
                        """
                        UPDATE pipeline_steps
                        SET status = ?, started_at = ?, error_message = NULL, output = NULL
                        WHERE run_id = ? AND step = ?
                        """,
                        (status.value, now, run_id, step.value),
                    )
                elif status in (StepStatus.COMPLETED, StepStatus.FAILED, StepStatus.SKIPPED):
                    cur = conn.execute(
                        """
                        UPDATE pipeline_steps
                        SET status = ?, completed_at = ?, error_message = ?, output = ?
                        WHERE run_id = ? AND step = ?
                        """,
                        (status.value, now, error_message, output, run_id, step.value),
                    )
                else:
                    cur = conn.execute(
                        """
                        UPDATE pipeline_steps
                        SET status = ?, error_message = ?, output = ?
                        WHERE run_id = ? AND step = ?
                        """,
                        (status.value, error_message, output, run_id, step.value),
                    )
                return cur.rowcount > 0

    def get_pipeline_steps(self, run_id: str) -> list[PipelineStepInfo]:
        """Get all pipeline steps for a run.

        Args:
            run_id: The run identifier

        Returns:
            List of PipelineStepInfo for all steps
        """
        with self._lock:
            with self._connect() as conn:
                rows = conn.execute(
                    """
                    SELECT step, status, started_at, completed_at, error_message, output
                    FROM pipeline_steps
                    WHERE run_id = ?
                    ORDER BY id
                    """,
                    (run_id,),
                ).fetchall()

            return [
                PipelineStepInfo(
                    step=PipelineStep(row["step"]),
                    status=StepStatus(row["status"]),
                    started_at=(
                        datetime.fromisoformat(row["started_at"])
                        if row["started_at"]
                        else None
                    ),
                    completed_at=(
                        datetime.fromisoformat(row["completed_at"])
                        if row["completed_at"]
                        else None
                    ),
                    error_message=row["error_message"],
                    output=row["output"],
                )
                for row in rows
            ]

    def _generate_run_id(self) -> str:
        """Generate a unique run ID."""
        timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
        short_uuid = uuid.uuid4().hex[:8]
        return f"run_{timestamp}_{short_uuid}"
