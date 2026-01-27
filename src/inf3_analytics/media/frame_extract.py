"""Frame extraction from video using FFmpeg."""

import shutil
import subprocess
from pathlib import Path


class FrameExtractionError(RuntimeError):
    """Raised when frame extraction fails."""

    pass


class FFmpegNotFoundError(RuntimeError):
    """Raised when FFmpeg is not installed or not found in PATH."""

    def __init__(self) -> None:
        super().__init__(
            "FFmpeg not found. Please install FFmpeg and ensure it's in your PATH.\n"
            "Installation instructions:\n"
            "  - Ubuntu/Debian: sudo apt install ffmpeg\n"
            "  - macOS: brew install ffmpeg\n"
            "  - Windows: Download from https://ffmpeg.org/download.html"
        )


def _check_ffmpeg() -> None:
    """Check if FFmpeg is available.

    Raises:
        FFmpegNotFoundError: If FFmpeg is not found
    """
    if shutil.which("ffmpeg") is None:
        raise FFmpegNotFoundError()


def format_frame_filename(index: int, timestamp_s: float) -> str:
    """Format a frame filename with index and timestamp.

    Creates a filesystem-safe filename with the frame index and timestamp.
    Example: "000_00-07-14.200.jpg"

    Args:
        index: Frame index (0, 1, 2, ...)
        timestamp_s: Timestamp in seconds

    Returns:
        Formatted filename string
    """
    # Convert to time components
    total_ms = int(round(timestamp_s * 1000))
    ms = total_ms % 1000
    total_seconds = total_ms // 1000
    s = total_seconds % 60
    total_minutes = total_seconds // 60
    m = total_minutes % 60
    h = total_minutes // 60

    # Use hyphens and dots for filesystem safety
    ts_str = f"{h:02d}-{m:02d}-{s:02d}.{ms:03d}"
    return f"{index:03d}_{ts_str}.jpg"


def extract_frame(
    video_path: Path,
    output_path: Path,
    timestamp_s: float,
    quality: int = 2,
) -> bool:
    """Extract a single frame from a video at a specific timestamp.

    Args:
        video_path: Path to the source video file
        output_path: Path for the output JPEG file
        timestamp_s: Timestamp in seconds to extract
        quality: JPEG quality (1-31, lower is better, default: 2)

    Returns:
        True if extraction succeeded, False otherwise

    Raises:
        FFmpegNotFoundError: If FFmpeg is not found
        FileNotFoundError: If video file doesn't exist
    """
    _check_ffmpeg()

    if not video_path.exists():
        raise FileNotFoundError(f"Video file not found: {video_path}")

    # Create output directory if needed
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Use -ss before -i for faster seeking (input seeking)
    cmd = [
        "ffmpeg",
        "-y",  # Overwrite output
        "-ss",
        str(timestamp_s),  # Seek position
        "-i",
        str(video_path),
        "-frames:v",
        "1",  # Extract single frame
        "-q:v",
        str(quality),  # JPEG quality
        str(output_path),
    ]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=False,  # Don't raise on non-zero exit
        )

        # Check if output was created
        if output_path.exists() and output_path.stat().st_size > 0:
            return True

        # Log error for debugging
        if result.returncode != 0:
            # Frame extraction can fail for timestamps beyond video duration
            # This is expected behavior, not an error to raise
            return False

        return False

    except Exception:
        return False
