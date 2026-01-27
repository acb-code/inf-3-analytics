"""Video probing utilities using FFprobe."""

import json
import shutil
import subprocess
from pathlib import Path

from inf3_analytics.types.media import VideoInfo


class FFprobeNotFoundError(RuntimeError):
    """Raised when FFprobe is not installed or not found in PATH."""

    def __init__(self) -> None:
        super().__init__(
            "FFprobe not found. Please install FFmpeg and ensure it's in your PATH.\n"
            "Installation instructions:\n"
            "  - Ubuntu/Debian: sudo apt install ffmpeg\n"
            "  - macOS: brew install ffmpeg\n"
            "  - Windows: Download from https://ffmpeg.org/download.html"
        )


class VideoProbeError(RuntimeError):
    """Raised when video probing fails."""

    pass


def _check_ffprobe() -> None:
    """Check if ffprobe is available.

    Raises:
        FFprobeNotFoundError: If ffprobe is not found
    """
    if shutil.which("ffprobe") is None:
        raise FFprobeNotFoundError()


def probe_video(video_path: Path) -> VideoInfo:
    """Get detailed information about a video file.

    Args:
        video_path: Path to the video file

    Returns:
        VideoInfo with duration, dimensions, FPS, and codec

    Raises:
        FFprobeNotFoundError: If ffprobe is not found
        FileNotFoundError: If video file doesn't exist
        VideoProbeError: If probing fails
    """
    _check_ffprobe()

    if not video_path.exists():
        raise FileNotFoundError(f"Video file not found: {video_path}")

    cmd = [
        "ffprobe",
        "-v",
        "quiet",
        "-print_format",
        "json",
        "-show_format",
        "-show_streams",
        str(video_path),
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        data = json.loads(result.stdout)
    except subprocess.CalledProcessError as e:
        raise VideoProbeError(
            f"Failed to probe video: {e.stderr or 'Unknown error'}"
        ) from e
    except json.JSONDecodeError as e:
        raise VideoProbeError(f"Failed to parse ffprobe output: {e}") from e

    # Get duration from format
    try:
        duration = float(data["format"]["duration"])
    except KeyError as e:
        raise VideoProbeError(f"Failed to get video duration: {e}") from e

    # Find video stream for dimensions and FPS
    width: int | None = None
    height: int | None = None
    fps: float | None = None
    codec: str | None = None

    streams = data.get("streams", [])
    for stream in streams:
        if stream.get("codec_type") == "video":
            width = stream.get("width")
            height = stream.get("height")
            codec = stream.get("codec_name")

            # Parse frame rate from "30/1" or "30000/1001" format
            avg_frame_rate = stream.get("avg_frame_rate", "0/1")
            if avg_frame_rate and "/" in avg_frame_rate:
                num, den = avg_frame_rate.split("/")
                if float(den) > 0:
                    fps = float(num) / float(den)
            elif avg_frame_rate:
                try:
                    fps = float(avg_frame_rate)
                except ValueError:
                    pass

            break  # Use first video stream

    return VideoInfo(
        path=video_path,
        duration_s=duration,
        width=width,
        height=height,
        fps=fps,
        codec=codec,
    )
