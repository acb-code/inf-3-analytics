"""Types for video decomposition."""

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal


@dataclass(frozen=True, slots=True)
class SplitPoint:
    """A point where a video can be split."""

    timestamp_s: float
    timestamp_ts: str  # "HH:MM:SS.mmm"
    type: Literal["silence", "scene", "interval", "user"]
    keyframe_s: float  # Nearest keyframe timestamp
    confidence: float  # 0-1, higher = better split point

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "timestamp_s": self.timestamp_s,
            "timestamp_ts": self.timestamp_ts,
            "type": self.type,
            "keyframe_s": self.keyframe_s,
            "confidence": self.confidence,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SplitPoint":
        """Create from dictionary."""
        return cls(
            timestamp_s=data["timestamp_s"],
            timestamp_ts=data["timestamp_ts"],
            type=data["type"],
            keyframe_s=data["keyframe_s"],
            confidence=data["confidence"],
        )


@dataclass(frozen=True, slots=True)
class SegmentInfo:
    """Information about a video segment."""

    index: int
    start_s: float
    end_s: float
    duration_s: float
    start_ts: str
    end_ts: str
    estimated_size_mb: float

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "index": self.index,
            "start_s": self.start_s,
            "end_s": self.end_s,
            "duration_s": self.duration_s,
            "start_ts": self.start_ts,
            "end_ts": self.end_ts,
            "estimated_size_mb": self.estimated_size_mb,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SegmentInfo":
        """Create from dictionary."""
        return cls(
            index=data["index"],
            start_s=data["start_s"],
            end_s=data["end_s"],
            duration_s=data["duration_s"],
            start_ts=data["start_ts"],
            end_ts=data["end_ts"],
            estimated_size_mb=data["estimated_size_mb"],
        )


@dataclass(frozen=True, slots=True)
class DecompositionPlan:
    """Plan for decomposing a video into segments."""

    video_path: Path
    duration_s: float
    duration_ts: str
    file_size_mb: float
    split_points: tuple[SplitPoint, ...]
    segments: tuple[SegmentInfo, ...]

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "video_path": str(self.video_path),
            "duration_s": self.duration_s,
            "duration_ts": self.duration_ts,
            "file_size_mb": self.file_size_mb,
            "split_points": [sp.to_dict() for sp in self.split_points],
            "segments": [seg.to_dict() for seg in self.segments],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "DecompositionPlan":
        """Create from dictionary."""
        return cls(
            video_path=Path(data["video_path"]),
            duration_s=data["duration_s"],
            duration_ts=data["duration_ts"],
            file_size_mb=data["file_size_mb"],
            split_points=tuple(
                SplitPoint.from_dict(sp) for sp in data["split_points"]
            ),
            segments=tuple(SegmentInfo.from_dict(seg) for seg in data["segments"]),
        )


@dataclass(frozen=True, slots=True)
class SegmentResult:
    """Result of creating a segment."""

    index: int
    path: Path
    start_s: float
    end_s: float
    duration_s: float
    file_size_mb: float
    child_run_id: str | None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "index": self.index,
            "path": str(self.path),
            "start_s": self.start_s,
            "end_s": self.end_s,
            "duration_s": self.duration_s,
            "file_size_mb": self.file_size_mb,
            "child_run_id": self.child_run_id,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SegmentResult":
        """Create from dictionary."""
        return cls(
            index=data["index"],
            path=Path(data["path"]),
            start_s=data["start_s"],
            end_s=data["end_s"],
            duration_s=data["duration_s"],
            file_size_mb=data["file_size_mb"],
            child_run_id=data.get("child_run_id"),
        )


@dataclass(frozen=True, slots=True)
class DecompositionManifest:
    """Manifest of a completed decomposition."""

    video_path: Path
    duration_s: float
    created_at: str
    segments: tuple[SegmentResult, ...]
    child_run_ids: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "video_path": str(self.video_path),
            "duration_s": self.duration_s,
            "created_at": self.created_at,
            "segments": [seg.to_dict() for seg in self.segments],
            "child_run_ids": list(self.child_run_ids),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "DecompositionManifest":
        """Create from dictionary."""
        return cls(
            video_path=Path(data["video_path"]),
            duration_s=data["duration_s"],
            created_at=data["created_at"],
            segments=tuple(SegmentResult.from_dict(seg) for seg in data["segments"]),
            child_run_ids=tuple(data["child_run_ids"]),
        )
