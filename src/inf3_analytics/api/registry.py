"""JSON file-backed run registry."""

import json
import uuid
from datetime import UTC, datetime
from pathlib import Path
from threading import Lock
from typing import Any

from inf3_analytics.api.models import RunMetadata, RunStatus


class RunRegistry:
    """Thread-safe JSON file registry for pipeline runs."""

    def __init__(self, registry_path: Path) -> None:
        """Initialize the registry.

        Args:
            registry_path: Path to the JSON registry file
        """
        self._path = registry_path
        self._lock = Lock()

    def _load(self) -> dict[str, Any]:
        """Load registry data from file."""
        if not self._path.exists():
            return {"runs": {}}
        with open(self._path, encoding="utf-8") as f:
            return json.load(f)  # type: ignore[no-any-return]

    def _save(self, data: dict[str, Any]) -> None:
        """Save registry data to file."""
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with open(self._path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, default=str)

    def _generate_run_id(self) -> str:
        """Generate a unique run ID."""
        timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
        short_uuid = uuid.uuid4().hex[:8]
        return f"run_{timestamp}_{short_uuid}"

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
            data = self._load()

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

            data["runs"][run_id] = run_data
            self._save(data)

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
            data = self._load()
            run_data = data["runs"].get(run_id)
            if run_data is None:
                return None
            return RunMetadata(
                run_id=run_data["run_id"],
                video_path=run_data["video_path"],
                run_root=run_data["run_root"],
                video_basename=run_data["video_basename"],
                status=RunStatus(run_data["status"]),
                created_at=datetime.fromisoformat(run_data["created_at"]),
            )

    def list_runs(self) -> list[RunMetadata]:
        """List all runs.

        Returns:
            List of RunMetadata for all runs
        """
        with self._lock:
            data = self._load()
            runs = []
            for run_data in data["runs"].values():
                runs.append(
                    RunMetadata(
                        run_id=run_data["run_id"],
                        video_path=run_data["video_path"],
                        run_root=run_data["run_root"],
                        video_basename=run_data["video_basename"],
                        status=RunStatus(run_data["status"]),
                        created_at=datetime.fromisoformat(run_data["created_at"]),
                    )
                )
            return sorted(runs, key=lambda r: r.created_at, reverse=True)

    def update_status(self, run_id: str, status: RunStatus) -> bool:
        """Update the status of a run.

        Args:
            run_id: The run identifier
            status: New status

        Returns:
            True if updated, False if run not found
        """
        with self._lock:
            data = self._load()
            if run_id not in data["runs"]:
                return False
            data["runs"][run_id]["status"] = status.value
            self._save(data)
            return True
