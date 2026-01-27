"""Frame extraction data types."""

from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any


class FrameExtractionStatus(Enum):
    """Status of frame extraction for an event."""

    SUCCESS = "success"
    PARTIAL = "partial"  # Some frames failed
    SKIPPED = "skipped"  # Invalid timestamps
    FAILED = "failed"


@dataclass(frozen=True, slots=True)
class Frame:
    """A single extracted video frame."""

    frame_id: str  # "000", "001", etc.
    path: Path  # Relative path: "frames/000_00-07-14.200.jpg"
    timestamp_s: float
    timestamp_ts: str  # "00:07:14,200"
    width: int | None
    height: int | None
    file_size_bytes: int | None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "frame_id": self.frame_id,
            "path": str(self.path),
            "timestamp_s": self.timestamp_s,
            "timestamp_ts": self.timestamp_ts,
            "width": self.width,
            "height": self.height,
            "file_size_bytes": self.file_size_bytes,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Frame":
        """Create Frame from dictionary."""
        return cls(
            frame_id=str(data["frame_id"]),
            path=Path(data["path"]),
            timestamp_s=float(data["timestamp_s"]),
            timestamp_ts=str(data["timestamp_ts"]),
            width=int(data["width"]) if data.get("width") is not None else None,
            height=int(data["height"]) if data.get("height") is not None else None,
            file_size_bytes=(
                int(data["file_size_bytes"])
                if data.get("file_size_bytes") is not None
                else None
            ),
        )


@dataclass(frozen=True, slots=True)
class EventFrameSet:
    """Collection of frames extracted for a single event."""

    event_id: str
    event_title: str
    start_s: float
    end_s: float
    start_ts: str
    end_ts: str
    frames: tuple[Frame, ...]
    status: FrameExtractionStatus
    error_message: str | None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "event_id": self.event_id,
            "event_title": self.event_title,
            "start_s": self.start_s,
            "end_s": self.end_s,
            "start_ts": self.start_ts,
            "end_ts": self.end_ts,
            "frames": [f.to_dict() for f in self.frames],
            "status": self.status.value,
            "error_message": self.error_message,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "EventFrameSet":
        """Create EventFrameSet from dictionary."""
        frames_data = data["frames"]
        if not isinstance(frames_data, list):
            raise ValueError("frames must be a list")

        return cls(
            event_id=str(data["event_id"]),
            event_title=str(data["event_title"]),
            start_s=float(data["start_s"]),
            end_s=float(data["end_s"]),
            start_ts=str(data["start_ts"]),
            end_ts=str(data["end_ts"]),
            frames=tuple(Frame.from_dict(f) for f in frames_data),
            status=FrameExtractionStatus(data["status"]),
            error_message=(
                str(data["error_message"]) if data.get("error_message") else None
            ),
        )


@dataclass(frozen=True, slots=True)
class FrameExtractionMetadata:
    """Metadata about the frame extraction process."""

    policy_name: str
    policy_params: dict[str, int | float]
    video_path: str
    video_duration_s: float
    video_fps: float | None
    video_width: int | None
    video_height: int | None
    events_path: str
    extraction_timestamp: str
    jpeg_quality: int

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "policy_name": self.policy_name,
            "policy_params": self.policy_params,
            "video_path": self.video_path,
            "video_duration_s": self.video_duration_s,
            "video_fps": self.video_fps,
            "video_width": self.video_width,
            "video_height": self.video_height,
            "events_path": self.events_path,
            "extraction_timestamp": self.extraction_timestamp,
            "jpeg_quality": self.jpeg_quality,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "FrameExtractionMetadata":
        """Create FrameExtractionMetadata from dictionary."""
        policy_params = data["policy_params"]
        if not isinstance(policy_params, dict):
            raise ValueError("policy_params must be a dict")

        return cls(
            policy_name=str(data["policy_name"]),
            policy_params={str(k): v for k, v in policy_params.items()},
            video_path=str(data["video_path"]),
            video_duration_s=float(data["video_duration_s"]),
            video_fps=(
                float(data["video_fps"]) if data.get("video_fps") is not None else None
            ),
            video_width=(
                int(data["video_width"]) if data.get("video_width") is not None else None
            ),
            video_height=(
                int(data["video_height"]) if data.get("video_height") is not None else None
            ),
            events_path=str(data["events_path"]),
            extraction_timestamp=str(data["extraction_timestamp"]),
            jpeg_quality=int(data["jpeg_quality"]),
        )


@dataclass(frozen=True, slots=True)
class FrameManifest:
    """Complete manifest of frame extraction for all events."""

    event_frame_sets: tuple[EventFrameSet, ...]
    metadata: FrameExtractionMetadata
    total_frames: int
    total_events: int
    successful_events: int
    skipped_events: int
    failed_events: int

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "event_frame_sets": [efs.to_dict() for efs in self.event_frame_sets],
            "metadata": self.metadata.to_dict(),
            "total_frames": self.total_frames,
            "total_events": self.total_events,
            "successful_events": self.successful_events,
            "skipped_events": self.skipped_events,
            "failed_events": self.failed_events,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "FrameManifest":
        """Create FrameManifest from dictionary."""
        event_frame_sets_data = data["event_frame_sets"]
        if not isinstance(event_frame_sets_data, list):
            raise ValueError("event_frame_sets must be a list")

        metadata_data = data["metadata"]
        if not isinstance(metadata_data, dict):
            raise ValueError("metadata must be a dict")

        return cls(
            event_frame_sets=tuple(
                EventFrameSet.from_dict(efs) for efs in event_frame_sets_data
            ),
            metadata=FrameExtractionMetadata.from_dict(metadata_data),
            total_frames=int(data["total_frames"]),
            total_events=int(data["total_events"]),
            successful_events=int(data["successful_events"]),
            skipped_events=int(data["skipped_events"]),
            failed_events=int(data["failed_events"]),
        )
