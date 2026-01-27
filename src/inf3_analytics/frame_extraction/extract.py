"""Frame extraction orchestrator for events."""

import re
from collections.abc import Callable
from datetime import datetime
from pathlib import Path

from inf3_analytics.frame_extraction.policies import FrameSamplingPolicy
from inf3_analytics.io.frame_manifest_writer import write_event_frames_json, write_manifest
from inf3_analytics.media.frame_extract import extract_frame, format_frame_filename
from inf3_analytics.media.video_probe import probe_video
from inf3_analytics.types.media import VideoInfo
from inf3_analytics.types.event import Event
from inf3_analytics.types.frame import (
    EventFrameSet,
    Frame,
    FrameExtractionMetadata,
    FrameExtractionStatus,
    FrameManifest,
)
from inf3_analytics.utils.time import seconds_to_timestamp


def _sanitize_dirname(name: str, max_len: int = 12) -> str:
    """Create a filesystem-safe directory name from a string.

    Args:
        name: Original string
        max_len: Maximum length for the result

    Returns:
        Sanitized, lowercase, truncated string
    """
    # Remove non-alphanumeric characters, replace spaces with underscores
    sanitized = re.sub(r"[^a-zA-Z0-9_\-]", "", name.replace(" ", "_"))
    return sanitized.lower()[:max_len]


def _create_event_dir_name(event: Event) -> str:
    """Create a unique directory name for an event.

    Format: evt_{index}_{sanitized_title}
    Example: evt_000_structur

    Args:
        event: Event to create directory name for

    Returns:
        Directory name string
    """
    # Extract index from event_id (e.g., "evt_000" -> "000")
    match = re.search(r"(\d+)", event.event_id)
    idx = match.group(1) if match else "000"

    # Sanitize title
    title_part = _sanitize_dirname(event.title)
    if not title_part:
        title_part = "event"

    return f"evt_{idx}_{title_part}"


def extract_event_frames(
    video_path: Path,
    events: tuple[Event, ...],
    events_path: Path,
    output_dir: Path,
    policy: FrameSamplingPolicy,
    jpeg_quality: int = 2,
    progress_callback: Callable[[Event, int, int], None] | None = None,
) -> FrameManifest:
    """Extract frames for all events using the specified policy.

    Args:
        video_path: Path to source video file
        events: Tuple of events to extract frames for
        events_path: Path to events JSON (for metadata)
        output_dir: Base output directory
        policy: Frame sampling policy to use
        jpeg_quality: JPEG quality (1-31, lower is better)
        progress_callback: Optional callback(event, index, total) for progress

    Returns:
        FrameManifest with extraction results

    Raises:
        FileNotFoundError: If video file doesn't exist
        VideoProbeError: If video probing fails
    """
    # Probe video for metadata
    video_info: VideoInfo = probe_video(video_path)

    # Create output directory
    output_dir.mkdir(parents=True, exist_ok=True)

    event_frame_sets: list[EventFrameSet] = []
    total_frames = 0
    successful_events = 0
    skipped_events = 0
    failed_events = 0

    for idx, event in enumerate(events):
        if progress_callback:
            progress_callback(event, idx, len(events))

        # Compute timestamps for this event
        timestamps = policy.compute_timestamps(
            event.start_s, event.end_s, video_info.duration_s
        )

        # Skip events with no valid timestamps
        if not timestamps:
            event_frame_set = EventFrameSet(
                event_id=event.event_id,
                event_title=event.title,
                start_s=event.start_s,
                end_s=event.end_s,
                start_ts=event.start_ts,
                end_ts=event.end_ts,
                frames=(),
                status=FrameExtractionStatus.SKIPPED,
                error_message="No valid timestamps within video bounds",
            )
            event_frame_sets.append(event_frame_set)
            skipped_events += 1
            continue

        # Create event directory
        event_dir_name = _create_event_dir_name(event)
        event_dir = output_dir / event_dir_name
        frames_dir = event_dir / "frames"
        frames_dir.mkdir(parents=True, exist_ok=True)

        # Extract frames
        frames: list[Frame] = []
        extraction_errors = 0

        for frame_idx, timestamp in enumerate(timestamps):
            filename = format_frame_filename(frame_idx, timestamp)
            frame_path = frames_dir / filename
            relative_path = Path("frames") / filename

            success = extract_frame(
                video_path=video_path,
                output_path=frame_path,
                timestamp_s=timestamp,
                quality=jpeg_quality,
            )

            if success:
                # Get file info
                file_size = frame_path.stat().st_size

                frame = Frame(
                    frame_id=f"{frame_idx:03d}",
                    path=relative_path,
                    timestamp_s=timestamp,
                    timestamp_ts=seconds_to_timestamp(timestamp),
                    width=video_info.width,
                    height=video_info.height,
                    file_size_bytes=file_size,
                )
                frames.append(frame)
            else:
                extraction_errors += 1

        # Determine status
        if not frames:
            status = FrameExtractionStatus.FAILED
            error_message = "All frame extractions failed"
            failed_events += 1
        elif extraction_errors > 0:
            status = FrameExtractionStatus.PARTIAL
            error_message = f"{extraction_errors} of {len(timestamps)} frames failed"
            successful_events += 1  # Still count as partial success
        else:
            status = FrameExtractionStatus.SUCCESS
            error_message = None
            successful_events += 1

        event_frame_set = EventFrameSet(
            event_id=event.event_id,
            event_title=event.title,
            start_s=event.start_s,
            end_s=event.end_s,
            start_ts=event.start_ts,
            end_ts=event.end_ts,
            frames=tuple(frames),
            status=status,
            error_message=error_message,
        )
        event_frame_sets.append(event_frame_set)
        total_frames += len(frames)

        # Write per-event frames.json
        write_event_frames_json(event_frame_set, event_dir / "frames.json")

    # Create metadata
    metadata = FrameExtractionMetadata(
        policy_name=policy.name,
        policy_params=policy.params,
        video_path=str(video_path),
        video_duration_s=video_info.duration_s,
        video_fps=video_info.fps,
        video_width=video_info.width,
        video_height=video_info.height,
        events_path=str(events_path),
        extraction_timestamp=datetime.now().isoformat(),
        jpeg_quality=jpeg_quality,
    )

    # Create manifest
    manifest = FrameManifest(
        event_frame_sets=tuple(event_frame_sets),
        metadata=metadata,
        total_frames=total_frames,
        total_events=len(events),
        successful_events=successful_events,
        skipped_events=skipped_events,
        failed_events=failed_events,
    )

    # Write top-level manifest
    write_manifest(manifest, output_dir / "manifest.json")

    return manifest
