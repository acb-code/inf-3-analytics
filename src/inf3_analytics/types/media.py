"""Media-related data types."""

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class AudioInfo:
    """Information about an extracted audio file."""

    path: Path
    duration_s: float
    sample_rate: int
    channels: int
    format: str
    source_video: Path | None

    def to_dict(self) -> dict[str, str | float | int | None]:
        """Convert to dictionary for serialization."""
        return {
            "path": str(self.path),
            "duration_s": self.duration_s,
            "sample_rate": self.sample_rate,
            "channels": self.channels,
            "format": self.format,
            "source_video": str(self.source_video) if self.source_video else None,
        }


@dataclass(frozen=True, slots=True)
class VideoInfo:
    """Information about a video file."""

    path: Path
    duration_s: float
    width: int | None
    height: int | None
    fps: float | None
    codec: str | None

    def to_dict(self) -> dict[str, str | float | int | None]:
        """Convert to dictionary for serialization."""
        return {
            "path": str(self.path),
            "duration_s": self.duration_s,
            "width": self.width,
            "height": self.height,
            "fps": self.fps,
            "codec": self.codec,
        }
