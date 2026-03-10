"""CLI for extracting video frames from events."""

import argparse
import sys
from pathlib import Path

from inf3_analytics.cli.progress import emit_progress
from inf3_analytics.frame_extraction import (
    FixedFPSWithinEventPolicy,
    NFramesPerEventPolicy,
    extract_event_frames,
)
from inf3_analytics.io.event_writer import read_json as read_events_json
from inf3_analytics.io.frame_manifest_writer import read_manifest, write_manifest
from inf3_analytics.types.event import Event
from inf3_analytics.types.frame import FrameManifest


def parse_args(args: list[str] | None = None) -> argparse.Namespace:
    """Parse command line arguments.

    Args:
        args: Command line arguments (uses sys.argv if None)

    Returns:
        Parsed arguments namespace
    """
    parser = argparse.ArgumentParser(
        prog="inf3-extract-event-frames",
        description="Extract video frames for each event's time window",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Default: 5 frames per event
  %(prog)s --video inspection.mp4 --events outputs/events/events.json

  # 10 frames per event
  %(prog)s --video inspection.mp4 --events events.json --policy nframes --n 10

  # 2 FPS, max 20 frames per event
  %(prog)s --video inspection.mp4 --events events.json --policy fps --fps 2 --max-frames 20

  # Higher quality JPEG (lower number = better quality)
  %(prog)s --video inspection.mp4 --events events.json --quality 1
        """,
    )

    parser.add_argument(
        "--video",
        "-v",
        type=Path,
        required=True,
        help="Input video file",
    )

    parser.add_argument(
        "--events",
        "-e",
        type=Path,
        required=True,
        help="Input events JSON file",
    )

    parser.add_argument(
        "--out",
        "-o",
        type=Path,
        default=Path("./outputs/event_frames"),
        help="Output directory (default: ./outputs/event_frames)",
    )

    parser.add_argument(
        "--policy",
        type=str,
        default="nframes",
        choices=["nframes", "fps"],
        help="Frame sampling policy: nframes (N evenly-spaced) or fps (fixed rate)",
    )

    parser.add_argument(
        "--n",
        type=int,
        default=5,
        help="Number of frames per event for nframes policy (default: 5)",
    )

    parser.add_argument(
        "--fps",
        type=float,
        default=1.0,
        help="Frames per second for fps policy (default: 1.0)",
    )

    parser.add_argument(
        "--max-frames",
        type=int,
        default=30,
        help="Maximum frames per event for fps policy (default: 30)",
    )

    parser.add_argument(
        "--quality",
        type=int,
        default=2,
        choices=range(1, 32),
        metavar="1-31",
        help="JPEG quality (1-31, lower is better, default: 2)",
    )

    parser.add_argument(
        "--event-id",
        type=str,
        default=None,
        help="If set, only extract frames for the event with this ID",
    )

    return parser.parse_args(args)


def main(args: list[str] | None = None) -> int:
    """Main entry point for frame extraction CLI.

    Args:
        args: Command line arguments (uses sys.argv if None)

    Returns:
        Exit code (0 for success, non-zero for errors)
    """
    parsed = parse_args(args)

    # Validate inputs
    video_path: Path = parsed.video
    if not video_path.exists():
        print(f"Error: Video file not found: {video_path}", file=sys.stderr)
        return 1

    events_path: Path = parsed.events
    if not events_path.exists():
        print(f"Error: Events file not found: {events_path}", file=sys.stderr)
        return 1

    # Load events
    print(f"Loading events: {events_path}")
    try:
        event_list = read_events_json(events_path)
        all_events: tuple[Event, ...] = event_list.events
        print(f"Loaded {len(all_events)} events")
    except Exception as e:
        print(f"Error loading events: {e}", file=sys.stderr)
        return 1

    # Filter to a single event if --event-id was specified
    event_id_filter: str | None = parsed.event_id
    if event_id_filter:
        events: tuple[Event, ...] = tuple(e for e in all_events if e.event_id == event_id_filter)
        if not events:
            print(f"Error: No event found with event_id={event_id_filter!r}", file=sys.stderr)
            return 1
        print(f"Filtering to event: {event_id_filter}")
    else:
        events = all_events

    if not events:
        print("No events to process")
        return 0

    # Create policy
    policy: NFramesPerEventPolicy | FixedFPSWithinEventPolicy
    if parsed.policy == "nframes":
        policy = NFramesPerEventPolicy(n=parsed.n)
        print(f"Using nframes policy with n={parsed.n}")
    else:
        policy = FixedFPSWithinEventPolicy(fps=parsed.fps, max_frames=parsed.max_frames)
        print(f"Using fps policy with fps={parsed.fps}, max_frames={parsed.max_frames}")

    # Set up output directory
    output_dir: Path = parsed.out
    output_dir.mkdir(parents=True, exist_ok=True)

    # Progress callback
    def progress(event: Event, idx: int, total: int) -> None:
        emit_progress(idx + 1, total, "events", "Extracting frames")
        print(f"[{idx + 1}/{total}] Extracting frames for: {event.title[:50]}...")

    # Extract frames
    print(f"Extracting frames from: {video_path}")
    try:
        manifest = extract_event_frames(
            video_path=video_path,
            events=events,
            events_path=events_path,
            output_dir=output_dir,
            policy=policy,
            jpeg_quality=parsed.quality,
            progress_callback=progress,
        )
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Error during extraction: {e}", file=sys.stderr)
        return 1

    # If filtering to a single event, merge the new frame set into the existing manifest
    if event_id_filter:
        manifest_path = output_dir / "manifest.json"
        if manifest_path.exists():
            try:
                existing = read_manifest(manifest_path)
                # Replace or append this event's frame set
                new_sets = [fs for fs in existing.event_frame_sets if fs.event_id != event_id_filter]
                new_sets.extend(manifest.event_frame_sets)
                merged = FrameManifest(
                    event_frame_sets=tuple(new_sets),
                    metadata=manifest.metadata,
                    total_frames=sum(len(fs.frames) for fs in new_sets),
                    total_events=len(new_sets),
                    successful_events=sum(
                        1 for fs in new_sets if fs.status.value in ("success", "partial")
                    ),
                    skipped_events=sum(1 for fs in new_sets if fs.status.value == "skipped"),
                    failed_events=sum(1 for fs in new_sets if fs.status.value == "failed"),
                )
                write_manifest(merged, manifest_path)
                manifest = merged
                print(f"Merged into existing manifest ({len(new_sets)} total events)")
            except Exception as e:
                print(f"Warning: Could not merge manifest: {e}", file=sys.stderr)

    # Print summary
    print()
    print("Extraction complete!")
    print(f"  Total events: {manifest.total_events}")
    print(f"  Successful: {manifest.successful_events}")
    print(f"  Skipped: {manifest.skipped_events}")
    print(f"  Failed: {manifest.failed_events}")
    print(f"  Total frames: {manifest.total_frames}")
    print(f"  Output: {output_dir}")
    print(f"  Manifest: {output_dir / 'manifest.json'}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
