"""Audio extraction from video files using FFmpeg."""

import json
import shutil
import subprocess
from pathlib import Path

from inf3_analytics.types.media import AudioInfo


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


class AudioExtractionError(RuntimeError):
    """Raised when audio extraction fails."""

    pass


def _check_ffmpeg() -> None:
    """Check if FFmpeg is available.

    Raises:
        FFmpegNotFoundError: If FFmpeg is not found
    """
    if shutil.which("ffmpeg") is None:
        raise FFmpegNotFoundError()


def _check_ffprobe() -> None:
    """Check if ffprobe is available.

    Raises:
        FFmpegNotFoundError: If ffprobe is not found
    """
    if shutil.which("ffprobe") is None:
        raise FFmpegNotFoundError()


def get_video_duration(video_path: Path) -> float:
    """Get the duration of a video file using ffprobe.

    Args:
        video_path: Path to the video file

    Returns:
        Duration in seconds

    Raises:
        FFmpegNotFoundError: If ffprobe is not found
        AudioExtractionError: If duration cannot be determined
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
        str(video_path),
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        data = json.loads(result.stdout)
        duration = float(data["format"]["duration"])
        return duration
    except subprocess.CalledProcessError as e:
        raise AudioExtractionError(
            f"Failed to get video duration: {e.stderr or 'Unknown error'}"
        ) from e
    except (json.JSONDecodeError, KeyError) as e:
        raise AudioExtractionError(f"Failed to parse ffprobe output: {e}") from e


def extract_audio(
    video_path: Path,
    output_path: Path,
    sample_rate: int = 16000,
    channels: int = 1,
) -> AudioInfo:
    """Extract audio from video file as WAV.

    Extracts audio in a format optimized for speech recognition:
    - Mono channel (default)
    - 16kHz sample rate (default, optimal for Whisper)
    - 16-bit PCM WAV format

    Args:
        video_path: Path to the source video file
        output_path: Path for the output WAV file
        sample_rate: Audio sample rate in Hz (default: 16000)
        channels: Number of audio channels (default: 1 for mono)

    Returns:
        AudioInfo with details about the extracted audio

    Raises:
        FFmpegNotFoundError: If FFmpeg is not found
        FileNotFoundError: If video file doesn't exist
        AudioExtractionError: If extraction fails
    """
    _check_ffmpeg()

    if not video_path.exists():
        raise FileNotFoundError(f"Video file not found: {video_path}")

    # Create output directory if needed
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Get video duration first
    duration = get_video_duration(video_path)

    cmd = [
        "ffmpeg",
        "-y",  # Overwrite output file
        "-i",
        str(video_path),
        "-vn",  # No video
        "-acodec",
        "pcm_s16le",  # 16-bit PCM
        "-ar",
        str(sample_rate),
        "-ac",
        str(channels),
        str(output_path),
    ]

    try:
        subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True,
        )
    except subprocess.CalledProcessError as e:
        raise AudioExtractionError(
            f"Audio extraction failed: {e.stderr or 'Unknown error'}"
        ) from e

    if not output_path.exists():
        raise AudioExtractionError(f"Output file was not created: {output_path}")

    return AudioInfo(
        path=output_path,
        duration_s=duration,
        sample_rate=sample_rate,
        channels=channels,
        format="wav",
        source_video=video_path,
    )
