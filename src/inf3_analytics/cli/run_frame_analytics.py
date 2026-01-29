"""CLI for running frame analytics on extracted event frames."""

import argparse
import json
import sys
import time
import uuid
from datetime import datetime
from pathlib import Path

from inf3_analytics.frame_analytics import AnalyticsConfig, get_engine, list_engines
from inf3_analytics.frame_analytics.aggregate import aggregate_event_results
from inf3_analytics.io.analytics_writer import (
    create_event_output_dir,
    write_analytics_manifest,
    write_analytics_report,
    write_event_analytics,
)
from inf3_analytics.io.event_writer import read_json as read_events_json
from inf3_analytics.io.frame_manifest_writer import read_manifest
from inf3_analytics.types.detection import AnalyticsManifest, EventAnalyticsSummary, FrameMeta
from inf3_analytics.types.event import Event


def _find_event_directory(event_frames_dir: Path, event_id: str) -> Path | None:
    """Find the directory containing frames for the given event_id.

    The frame extraction creates directories with format evt_{idx}_{title},
    but the manifest stores the full event_id. We need to find the matching
    directory by checking the frames.json file in each subdirectory.

    Args:
        event_frames_dir: Base directory containing event frame directories
        event_id: Event ID to find

    Returns:
        Path to the event directory, or None if not found
    """
    for subdir in event_frames_dir.iterdir():
        if not subdir.is_dir():
            continue

        frames_json = subdir / "frames.json"
        if frames_json.exists():
            try:
                with open(frames_json) as f:
                    data = json.load(f)
                if data.get("event_id") == event_id:
                    return subdir
            except (json.JSONDecodeError, OSError):
                continue

    return None


def parse_args(args: list[str] | None = None) -> argparse.Namespace:
    """Parse command line arguments.

    Args:
        args: Command line arguments (uses sys.argv if None)

    Returns:
        Parsed arguments namespace
    """
    parser = argparse.ArgumentParser(
        prog="inf3-frame-analytics",
        description="Run VLM-based analytics on extracted event frames",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Analyze frames using Gemini (default)
  %(prog)s --event-frames outputs/event_frames --out outputs/frame_analytics

  # Use OpenAI GPT-5-mini
  %(prog)s --event-frames outputs/event_frames --engine openai

  # Use baseline quality metrics (no API required)
  %(prog)s --event-frames outputs/event_frames --engine baseline_quality

  # Limit frames per event and add delay between API calls
  %(prog)s --event-frames outputs/event_frames --max-frames-per-event 5 --sleep-ms 500

  # Dry run - show what would be processed without calling APIs
  %(prog)s --event-frames outputs/event_frames --dry-run

Environment Variables:
  OPENAI_API_KEY     Required for --engine openai
  GEMINI_API_KEY     Required for --engine gemini (or GOOGLE_API_KEY)
        """,
    )

    parser.add_argument(
        "--event-frames",
        "-f",
        type=Path,
        required=True,
        help="Directory containing event frames (with manifest.json)",
    )

    parser.add_argument(
        "--events",
        "-e",
        type=Path,
        default=None,
        help="Optional events.json for richer context (from Step 2)",
    )

    parser.add_argument(
        "--out",
        "-o",
        type=Path,
        default=Path("./outputs/frame_analytics"),
        help="Output directory (default: ./outputs/frame_analytics)",
    )

    parser.add_argument(
        "--engine",
        type=str,
        default="gemini",
        choices=list_engines(),
        help="Analytics engine: gemini (default), openai, or baseline_quality",
    )

    parser.add_argument(
        "--model",
        type=str,
        default=None,
        help="Override model name (e.g., gpt-5-mini, gemini-3-flash-preview)",
    )

    parser.add_argument(
        "--max-frames-per-event",
        type=int,
        default=10,
        help="Maximum frames to analyze per event (default: 10)",
    )

    parser.add_argument(
        "--max-total-frames",
        type=int,
        default=100,
        help="Maximum total frames to analyze (default: 100)",
    )

    parser.add_argument(
        "--sleep-ms-between-requests",
        "--sleep-ms",
        type=int,
        default=200,
        dest="sleep_ms",
        help="Milliseconds to sleep between API requests (default: 200)",
    )

    parser.add_argument(
        "--fallback-to-baseline",
        action="store_true",
        help="Fall back to baseline quality engine if VLM fails",
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be processed without calling APIs",
    )

    return parser.parse_args(args)


def main(args: list[str] | None = None) -> int:
    """Main entry point for frame analytics CLI.

    Args:
        args: Command line arguments (uses sys.argv if None)

    Returns:
        Exit code (0 for success, non-zero for errors)
    """
    parsed = parse_args(args)

    # Validate inputs
    event_frames_dir: Path = parsed.event_frames
    manifest_path = event_frames_dir / "manifest.json"

    if not manifest_path.exists():
        print(f"Error: Manifest not found: {manifest_path}", file=sys.stderr)
        return 1

    # Load frame manifest
    print(f"Loading frame manifest: {manifest_path}")
    try:
        frame_manifest = read_manifest(manifest_path)
        print(f"Found {frame_manifest.total_events} events, {frame_manifest.total_frames} frames")
    except Exception as e:
        print(f"Error loading manifest: {e}", file=sys.stderr)
        return 1

    # Load events if provided
    events_by_id: dict[str, Event] = {}
    if parsed.events:
        events_path: Path = parsed.events
        if events_path.exists():
            print(f"Loading events: {events_path}")
            try:
                event_list = read_events_json(events_path)
                events_by_id = {e.event_id: e for e in event_list.events}
                print(f"Loaded {len(events_by_id)} events")
            except Exception as e:
                print(f"Warning: Could not load events: {e}", file=sys.stderr)
        else:
            print(f"Warning: Events file not found: {events_path}", file=sys.stderr)

    # Build config
    config = AnalyticsConfig(
        max_frames_per_event=parsed.max_frames_per_event,
        max_total_frames=parsed.max_total_frames,
        sleep_ms_between_requests=parsed.sleep_ms,
        fallback_to_baseline=parsed.fallback_to_baseline,
        model_name=parsed.model,
    )

    # Count frames to process
    total_frames_to_process = 0
    for efs in frame_manifest.event_frame_sets:
        frame_count = min(len(efs.frames), config.max_frames_per_event)
        total_frames_to_process += frame_count
        if total_frames_to_process >= config.max_total_frames:
            total_frames_to_process = config.max_total_frames
            break

    print(f"\nEngine: {parsed.engine}")
    print(f"Frames to process: {total_frames_to_process}")

    # Dry run - just show what would be processed
    if parsed.dry_run:
        print("\n[DRY RUN] Would process:")
        frames_counted = 0
        for efs in frame_manifest.event_frame_sets:
            frames_for_event = min(len(efs.frames), config.max_frames_per_event)
            remaining = config.max_total_frames - frames_counted
            frames_for_event = min(frames_for_event, remaining)

            if frames_for_event > 0:
                print(f"  - {efs.event_id}: {frames_for_event} frames")
                frames_counted += frames_for_event

            if frames_counted >= config.max_total_frames:
                break

        print(f"\nTotal: {frames_counted} frames")
        print("[DRY RUN] No API calls made.")
        return 0

    # Create engine
    print(f"\nInitializing {parsed.engine} engine...")
    try:
        engine_cls = get_engine(parsed.engine)
        engine = engine_cls(config=config)
    except Exception as e:
        print(f"Error creating engine: {e}", file=sys.stderr)
        return 1

    # Set up output directory
    output_dir: Path = parsed.out
    output_dir.mkdir(parents=True, exist_ok=True)

    # Process frames
    run_id = f"run_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
    all_summaries: list[EventAnalyticsSummary] = []
    total_analyzed = 0
    total_failed = 0
    frames_processed = 0

    try:
        with engine:
            engine_info = engine.get_engine_info()
            print(f"Engine loaded: {engine_info.name}")
            if engine_info.provider:
                print(f"  Provider: {engine_info.provider}")
            if engine_info.model:
                print(f"  Model: {engine_info.model}")
            print()

            for efs_idx, efs in enumerate(frame_manifest.event_frame_sets):
                if frames_processed >= config.max_total_frames:
                    print(f"Reached max total frames limit ({config.max_total_frames})")
                    break

                event = events_by_id.get(efs.event_id)
                event_title = event.title if event else efs.event_title

                print(
                    f"[{efs_idx + 1}/{frame_manifest.total_events}] "
                    f"Processing: {event_title[:50]}..."
                )

                # Determine frames to process for this event
                frames_to_analyze = list(efs.frames)[: config.max_frames_per_event]
                remaining = config.max_total_frames - frames_processed
                frames_to_analyze = frames_to_analyze[:remaining]

                # Find the actual event directory (may differ from event_id)
                event_source_dir = _find_event_directory(event_frames_dir, efs.event_id)
                if event_source_dir is None:
                    print(f"    Warning: Could not find directory for event {efs.event_id}")
                    continue

                results = []
                for frame_idx, frame in enumerate(frames_to_analyze):
                    # Build absolute image path
                    image_path = event_source_dir / frame.path

                    # Build frame metadata
                    frame_meta = FrameMeta(
                        frame_idx=frame_idx,
                        timestamp_s=frame.timestamp_s,
                        timestamp_ts=frame.timestamp_ts,
                        image_path=str(frame.path),
                        event_id=efs.event_id,
                        event_title=event.title if event else efs.event_title,
                        event_summary=event.summary if event else None,
                        transcript_excerpt=(
                            event.transcript_ref.excerpt if event else None
                        ),
                    )

                    # Analyze frame
                    try:
                        result = engine.analyze(
                            image_path=image_path,
                            event=event,
                            frame_meta=frame_meta,
                        )
                        results.append(result)

                        if result.error:
                            total_failed += 1
                            print(f"    Frame {frame_idx}: Error - {result.error[:50]}")
                        else:
                            total_analyzed += 1
                            det_count = len(result.detections)
                            print(
                                f"    Frame {frame_idx}: {det_count} detection(s), "
                                f"scene: {result.scene_summary[:40]}..."
                            )

                    except Exception as e:
                        print(f"    Frame {frame_idx}: Exception - {e}")
                        total_failed += 1

                    frames_processed += 1

                    # Rate limiting
                    if (
                        frame_idx < len(frames_to_analyze) - 1
                        and config.sleep_ms_between_requests > 0
                    ):
                        time.sleep(config.sleep_ms_between_requests / 1000)

                # Aggregate results for this event
                summary = aggregate_event_results(
                    results=results,
                    event_id=efs.event_id,
                    engine_info=engine_info,
                    source_manifest=str(manifest_path),
                )

                # Write event outputs
                event_out_dir = create_event_output_dir(
                    output_dir, efs.event_id, event_title
                )
                write_event_analytics(event_out_dir, results, summary)
                all_summaries.append(summary)

                # Print event summary
                if summary.top_findings:
                    top = summary.top_findings[0]
                    print(
                        f"    Summary: {len(summary.top_findings)} finding type(s), "
                        f"top: {top.detection_type.value} ({top.max_confidence:.0%})"
                    )
                else:
                    print("    Summary: No issues detected")
                print()

    except Exception as e:
        print(f"\nError during processing: {e}", file=sys.stderr)
        return 1

    # Write manifest
    manifest = AnalyticsManifest(
        run_id=run_id,
        engine=engine_info,
        source_event_frames_manifest=str(manifest_path),
        events_file=str(parsed.events) if parsed.events else None,
        total_events=len(all_summaries),
        total_frames=frames_processed,
        analyzed_frames=total_analyzed,
        failed_frames=total_failed,
        created_at=datetime.now().isoformat(),
        event_summaries=tuple(
            str(output_dir / s.event_id[:12] / "event_summary.json") for s in all_summaries
        ),
    )

    manifest_out_path = output_dir / "manifest_analytics.json"
    write_analytics_manifest(manifest, manifest_out_path)

    # Write human-readable report
    report_path = output_dir / "analytics_report.md"
    write_analytics_report(manifest, all_summaries, report_path)

    # Print final summary
    print("=" * 60)
    print("Analytics Complete!")
    print(f"  Run ID: {run_id}")
    print(f"  Events processed: {len(all_summaries)}")
    print(f"  Frames analyzed: {total_analyzed}")
    print(f"  Frames failed: {total_failed}")
    print(f"  Output: {output_dir}")
    print(f"  Manifest: {manifest_out_path}")
    print(f"  Report: {report_path}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
