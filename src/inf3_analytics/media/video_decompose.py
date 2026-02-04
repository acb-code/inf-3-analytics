"""Video decomposition utilities using FFmpeg."""

import json
import re
import shutil
import subprocess
from collections.abc import Callable
from pathlib import Path

from inf3_analytics.media.video_probe import probe_video
from inf3_analytics.types.decomposition import (
    DecompositionPlan,
    SegmentInfo,
    SegmentResult,
    SplitPoint,
)


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


class DecompositionError(RuntimeError):
    """Raised when video decomposition fails."""

    pass


def _check_ffmpeg() -> None:
    """Check if ffmpeg is available."""
    if shutil.which("ffmpeg") is None:
        raise FFmpegNotFoundError()


def _format_timestamp(seconds: float) -> str:
    """Format seconds as HH:MM:SS.mmm."""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = seconds % 60
    return f"{hours:02d}:{minutes:02d}:{secs:06.3f}"


def _get_keyframes(video_path: Path) -> list[float]:
    """Get all keyframe positions from a video.

    Args:
        video_path: Path to the video file

    Returns:
        List of keyframe timestamps in seconds, sorted
    """
    cmd = [
        "ffprobe",
        "-v", "quiet",
        "-select_streams", "v:0",
        "-show_entries", "packet=pts_time,flags",
        "-of", "csv=print_section=0",
        str(video_path),
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    except subprocess.CalledProcessError as e:
        raise DecompositionError(f"Failed to get keyframes: {e.stderr}") from e

    keyframes = []
    for line in result.stdout.strip().split("\n"):
        if not line:
            continue
        parts = line.split(",")
        if len(parts) >= 2 and "K" in parts[1]:
            try:
                keyframes.append(float(parts[0]))
            except ValueError:
                continue

    return sorted(keyframes)


def _detect_silence(
    video_path: Path,
    threshold_db: float = -35,
    min_duration_s: float = 1.0,
) -> list[tuple[float, float]]:
    """Detect silence periods in video audio.

    Args:
        video_path: Path to the video file
        threshold_db: Silence threshold in dB (default -35)
        min_duration_s: Minimum silence duration in seconds

    Returns:
        List of (start, end) tuples for silence periods
    """
    cmd = [
        "ffmpeg",
        "-i", str(video_path),
        "-af", f"silencedetect=noise={threshold_db}dB:d={min_duration_s}",
        "-f", "null",
        "-",
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
    except subprocess.CalledProcessError:
        return []  # Silence detection is optional

    # Parse silence detect output from stderr
    silence_periods = []
    silence_start = None

    for line in result.stderr.split("\n"):
        if "silence_start:" in line:
            match = re.search(r"silence_start:\s*([\d.]+)", line)
            if match:
                silence_start = float(match.group(1))
        elif "silence_end:" in line and silence_start is not None:
            match = re.search(r"silence_end:\s*([\d.]+)", line)
            if match:
                silence_end = float(match.group(1))
                silence_periods.append((silence_start, silence_end))
                silence_start = None

    return silence_periods


def _snap_to_keyframe(timestamp: float, keyframes: list[float]) -> float:
    """Snap a timestamp to the nearest keyframe.

    Args:
        timestamp: Target timestamp in seconds
        keyframes: List of keyframe timestamps

    Returns:
        Nearest keyframe timestamp
    """
    if not keyframes:
        return timestamp

    # Find nearest keyframe
    nearest = min(keyframes, key=lambda k: abs(k - timestamp))
    return nearest


def _generate_interval_splits(
    duration_s: float,
    target_duration_s: float,
) -> list[float]:
    """Generate split points at regular intervals.

    Args:
        duration_s: Total video duration
        target_duration_s: Target segment duration

    Returns:
        List of split timestamps
    """
    splits = []
    current = target_duration_s
    while current < duration_s - 30:  # Leave at least 30s for last segment
        splits.append(current)
        current += target_duration_s
    return splits


def analyze_video_for_splits(
    video_path: Path,
    target_segment_duration_s: float = 300,
    silence_threshold_db: float = -35,
    silence_duration_s: float = 1.0,
) -> DecompositionPlan:
    """Analyze video and compute optimal split points.

    Strategy:
    1. Get all keyframe positions (ffprobe)
    2. Detect silence boundaries (ffmpeg silencedetect)
    3. Generate interval-based splits at target duration
    4. Merge silence + interval splits, snap to keyframes
    5. Return plan with confidence scores

    Args:
        video_path: Path to the video file
        target_segment_duration_s: Target duration for each segment (default 5 min)
        silence_threshold_db: Silence detection threshold in dB
        silence_duration_s: Minimum silence duration to detect

    Returns:
        DecompositionPlan with suggested split points and segments
    """
    _check_ffmpeg()

    if not video_path.exists():
        raise FileNotFoundError(f"Video file not found: {video_path}")

    # Get video info
    video_info = probe_video(video_path)
    duration_s = video_info.duration_s
    file_size_mb = video_path.stat().st_size / (1024 * 1024)

    # Get keyframes
    keyframes = _get_keyframes(video_path)

    # Detect silence periods
    silence_periods = _detect_silence(
        video_path, silence_threshold_db, silence_duration_s
    )

    # Generate interval-based splits
    interval_splits = _generate_interval_splits(duration_s, target_segment_duration_s)

    # Build split points
    split_points: list[SplitPoint] = []
    used_timestamps: set[float] = set()

    # Add silence-based splits (midpoints of silence periods near interval boundaries)
    for interval_ts in interval_splits:
        # Look for silence within 30 seconds of interval
        best_silence = None
        best_distance = float("inf")

        for start, end in silence_periods:
            midpoint = (start + end) / 2
            distance = abs(midpoint - interval_ts)
            if distance < 30 and distance < best_distance:
                best_silence = (start, end, midpoint)
                best_distance = distance

        if best_silence:
            _, _, midpoint = best_silence
            snapped = _snap_to_keyframe(midpoint, keyframes)

            # Avoid duplicate timestamps
            if snapped not in used_timestamps:
                used_timestamps.add(snapped)
                split_points.append(
                    SplitPoint(
                        timestamp_s=snapped,
                        timestamp_ts=_format_timestamp(snapped),
                        type="silence",
                        keyframe_s=snapped,
                        confidence=0.95,
                    )
                )

    # Add interval-based splits for uncovered intervals
    for interval_ts in interval_splits:
        # Check if we already have a split point nearby
        has_nearby = any(
            abs(sp.timestamp_s - interval_ts) < 30 for sp in split_points
        )
        if not has_nearby:
            snapped = _snap_to_keyframe(interval_ts, keyframes)
            if snapped not in used_timestamps:
                used_timestamps.add(snapped)
                split_points.append(
                    SplitPoint(
                        timestamp_s=snapped,
                        timestamp_ts=_format_timestamp(snapped),
                        type="interval",
                        keyframe_s=snapped,
                        confidence=0.8,
                    )
                )

    # Sort split points by timestamp
    split_points.sort(key=lambda sp: sp.timestamp_s)

    # Calculate segments from split points
    segments = _calculate_segments(
        split_points, duration_s, file_size_mb
    )

    return DecompositionPlan(
        video_path=video_path,
        duration_s=duration_s,
        duration_ts=_format_timestamp(duration_s),
        file_size_mb=file_size_mb,
        split_points=tuple(split_points),
        segments=tuple(segments),
    )


def _calculate_segments(
    split_points: list[SplitPoint],
    duration_s: float,
    file_size_mb: float,
) -> list[SegmentInfo]:
    """Calculate segment info from split points.

    Args:
        split_points: List of split points (must be sorted)
        duration_s: Total video duration
        file_size_mb: Total file size in MB

    Returns:
        List of SegmentInfo
    """
    segments = []
    bitrate_mb_per_s = file_size_mb / duration_s if duration_s > 0 else 0

    boundaries = [0.0] + [sp.timestamp_s for sp in split_points] + [duration_s]

    for i in range(len(boundaries) - 1):
        start_s = boundaries[i]
        end_s = boundaries[i + 1]
        seg_duration = end_s - start_s
        estimated_size = seg_duration * bitrate_mb_per_s

        segments.append(
            SegmentInfo(
                index=i,
                start_s=start_s,
                end_s=end_s,
                duration_s=seg_duration,
                start_ts=_format_timestamp(start_s),
                end_ts=_format_timestamp(end_s),
                estimated_size_mb=round(estimated_size, 2),
            )
        )

    return segments


def create_plan_from_timestamps(
    video_path: Path,
    split_timestamps: list[float],
) -> DecompositionPlan:
    """Create a decomposition plan from user-specified timestamps.

    Args:
        video_path: Path to the video file
        split_timestamps: List of timestamps where to split

    Returns:
        DecompositionPlan with the specified split points
    """
    _check_ffmpeg()

    if not video_path.exists():
        raise FileNotFoundError(f"Video file not found: {video_path}")

    video_info = probe_video(video_path)
    duration_s = video_info.duration_s
    file_size_mb = video_path.stat().st_size / (1024 * 1024)

    # Get keyframes for snapping
    keyframes = _get_keyframes(video_path)

    # Create split points from timestamps
    split_points = []
    for ts in sorted(split_timestamps):
        if ts <= 0 or ts >= duration_s:
            continue
        snapped = _snap_to_keyframe(ts, keyframes)
        split_points.append(
            SplitPoint(
                timestamp_s=snapped,
                timestamp_ts=_format_timestamp(snapped),
                type="user",
                keyframe_s=snapped,
                confidence=1.0,
            )
        )

    segments = _calculate_segments(split_points, duration_s, file_size_mb)

    return DecompositionPlan(
        video_path=video_path,
        duration_s=duration_s,
        duration_ts=_format_timestamp(duration_s),
        file_size_mb=file_size_mb,
        split_points=tuple(split_points),
        segments=tuple(segments),
    )


def execute_decomposition(
    plan: DecompositionPlan,
    output_dir: Path,
    progress_callback: Callable[[int, int, str], None] | None = None,
) -> list[SegmentResult]:
    """Split video into segments using copy codec (no re-encoding).

    Uses: ffmpeg -ss {start} -to {end} -c copy segment_{i}.mp4
    Speed: ~100x realtime (pure copy)

    Args:
        plan: Decomposition plan with segments
        output_dir: Directory to write segments to
        progress_callback: Optional callback(current, total, message)

    Returns:
        List of SegmentResult with created segment files
    """
    _check_ffmpeg()

    output_dir.mkdir(parents=True, exist_ok=True)
    results = []
    total = len(plan.segments)

    for i, segment in enumerate(plan.segments):
        if progress_callback:
            progress_callback(i, total, f"Creating segment {i + 1}/{total}")

        # Generate output filename
        output_file = output_dir / f"segment_{segment.index:03d}.mp4"

        # Build ffmpeg command with copy codec
        cmd = [
            "ffmpeg",
            "-y",  # Overwrite output
            "-ss", str(segment.start_s),
            "-i", str(plan.video_path),
            "-to", str(segment.duration_s),  # Duration relative to -ss
            "-c", "copy",  # Copy codec (no re-encoding)
            "-avoid_negative_ts", "make_zero",
            str(output_file),
        ]

        try:
            subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True,
            )
        except subprocess.CalledProcessError as e:
            raise DecompositionError(
                f"Failed to create segment {i}: {e.stderr}"
            ) from e

        # Get actual file size
        actual_size_mb = output_file.stat().st_size / (1024 * 1024)

        results.append(
            SegmentResult(
                index=segment.index,
                path=output_file,
                start_s=segment.start_s,
                end_s=segment.end_s,
                duration_s=segment.duration_s,
                file_size_mb=round(actual_size_mb, 2),
                child_run_id=None,  # Set later when creating runs
            )
        )

    if progress_callback:
        progress_callback(total, total, "Decomposition complete")

    return results
