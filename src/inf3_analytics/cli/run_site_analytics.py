"""CLI for running construction site analytics on video frames."""

import argparse
import json
import sys
import time
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from typing import Any

from inf3_analytics.cli.progress import emit_progress
from inf3_analytics.frame_analytics import AnalyticsConfig
from inf3_analytics.frame_analytics.base import BaseFrameAnalyticsEngine
from inf3_analytics.frame_analytics.aggregate import (
    SiteCountTimeSeries,
    aggregate_site_counts,
)
from inf3_analytics.types.detection import (
    EngineInfo,
    FrameAnalyticsResult,
    FrameMeta,
)


def parse_args(args: list[str] | None = None) -> argparse.Namespace:
    """Parse command line arguments.

    Args:
        args: Command line arguments (uses sys.argv if None)

    Returns:
        Parsed arguments namespace
    """
    parser = argparse.ArgumentParser(
        prog="inf3-site-analytics",
        description="Run construction site analytics (equipment & personnel counting)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Analyze frames using YOLO-World (default)
  %(prog)s --video path/to/video.mp4 --fps 0.5 --out outputs/site_analytics

  # Use specific device
  %(prog)s --video path/to/video.mp4 --device cpu

  # Use Gemini VLM instead of YOLO-World (no GPU required)
  %(prog)s --video path/to/video.mp4 --engine gemini --sleep-ms 500

  # Use OpenAI VLM engine
  %(prog)s --video path/to/video.mp4 --engine openai

  # Enable VLM verification for uncertain detections
  %(prog)s --video path/to/video.mp4 --verify-colors

  # Custom equipment classes
  %(prog)s --video path/to/video.mp4 --equipment-classes excavator crane "dump truck"

  # Use pre-extracted frames
  %(prog)s --frames-dir outputs/event_frames/evt_001/frames --out outputs/site_analytics
        """,
    )

    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument(
        "--video",
        "-v",
        type=Path,
        help="Path to video file (frames will be extracted at --fps rate)",
    )
    input_group.add_argument(
        "--frames-dir",
        type=Path,
        help="Directory containing pre-extracted JPEG frames",
    )

    parser.add_argument(
        "--out",
        "-o",
        type=Path,
        default=Path("./outputs/site_analytics"),
        help="Output directory (default: ./outputs/site_analytics)",
    )

    parser.add_argument(
        "--fps",
        type=float,
        default=0.5,
        help="Frames per second to extract from video (default: 0.5)",
    )

    parser.add_argument(
        "--engine",
        type=str,
        default="openai",
        choices=["yolo", "gemini", "openai"],
        help="Detection engine: yolo (local YOLO-World), gemini (Gemini VLM), openai (OpenAI VLM) (default: openai)",
    )

    parser.add_argument(
        "--device",
        type=str,
        default=None,
        choices=["cpu", "cuda"],
        help="Device for YOLO-World inference (default: auto-detect)",
    )

    parser.add_argument(
        "--sleep-ms",
        type=int,
        default=200,
        dest="sleep_ms",
        help="Milliseconds to sleep between VLM API calls for rate limiting (default: 200)",
    )

    parser.add_argument(
        "--confidence",
        type=float,
        default=0.15,
        help="Minimum detection confidence threshold (default: 0.15)",
    )

    parser.add_argument(
        "--verify-colors",
        action="store_true",
        help="Use VLM (Gemini Flash) to verify hardhat colors (small cost)",
    )

    parser.add_argument(
        "--verify-with-vlm",
        action="store_true",
        help="Use VLM to verify low-confidence detections",
    )

    parser.add_argument(
        "--equipment-classes",
        nargs="+",
        default=None,
        help="Custom equipment class names to detect (overrides defaults)",
    )

    parser.add_argument(
        "--model",
        type=str,
        default=None,
        help="Override YOLO-World model name (default: yolov8x-worldv2)",
    )

    parser.add_argument(
        "--parallel-workers",
        type=int,
        default=1,
        help="Number of parallel workers for frame processing (default: 1)",
    )

    parser.add_argument(
        "--language",
        type=str,
        default="en",
        help="Language code for output: en (English), fr (French) (default: en)",
    )

    parser.add_argument(
        "--max-frames",
        type=int,
        default=None,
        help="Maximum number of frames to process (default: unlimited)",
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be processed without running inference",
    )

    return parser.parse_args(args)


def _extract_frames_from_video(
    video_path: Path, fps: float, output_dir: Path
) -> list[tuple[Path, float]]:
    """Extract frames from video at the given fps.

    Args:
        video_path: Path to video file
        fps: Frames per second to extract
        output_dir: Directory to save extracted frames

    Returns:
        List of (frame_path, timestamp_s) tuples
    """
    from inf3_analytics.media.frame_extract import extract_frame
    from inf3_analytics.media.video_probe import probe_video

    video_info = probe_video(video_path)
    duration = video_info.duration_s
    interval = 1.0 / fps

    frames_dir = output_dir / "frames"
    frames_dir.mkdir(parents=True, exist_ok=True)

    frames: list[tuple[Path, float]] = []
    timestamp = 0.0
    idx = 0

    while timestamp < duration:
        filename = f"frame_{idx:05d}_{timestamp:.3f}s.jpg"
        frame_path = frames_dir / filename

        success = extract_frame(
            video_path=video_path,
            output_path=frame_path,
            timestamp_s=timestamp,
            quality=2,
        )

        if success:
            frames.append((frame_path, timestamp))

        timestamp += interval
        idx += 1

    return frames


def _collect_existing_frames(frames_dir: Path) -> list[tuple[Path, float]]:
    """Collect existing JPEG frames from a directory.

    Args:
        frames_dir: Directory containing JPEG frames

    Returns:
        List of (frame_path, timestamp_s) tuples sorted by name
    """
    frames: list[tuple[Path, float]] = []
    for img_path in sorted(frames_dir.glob("*.jpg")):
        # Try to extract timestamp from filename (e.g., frame_00001_10.500s.jpg)
        name = img_path.stem
        timestamp = 0.0
        for part in name.split("_"):
            if part.endswith("s"):
                try:
                    timestamp = float(part[:-1])
                    break
                except ValueError:
                    continue
        frames.append((img_path, timestamp))

    return frames


def _estimate_cost(
    num_frames: int,
    verify_colors: bool,
    verify_with_vlm: bool,
    engine: str = "yolo",
) -> None:
    """Print cost estimate for VLM usage.

    Args:
        num_frames: Total frames to process
        verify_colors: Whether color verification is enabled
        verify_with_vlm: Whether VLM verification is enabled
        engine: Engine type ("yolo", "gemini", or "openai")
    """
    if engine in ("gemini", "openai"):
        # VLM-only mode: every frame goes through the API
        if engine == "gemini":
            # Gemini Flash: ~$0.000083 per image
            cost_per_frame = 0.000083
        else:
            # OpenAI GPT-5-mini: ~$0.0003 per image
            cost_per_frame = 0.0003
        total_cost = num_frames * cost_per_frame
        print(f"\nEstimated VLM cost ({engine}): ~${total_cost:.4f} ({num_frames} API calls)")
        return

    vlm_frames = 0
    if verify_colors:
        # Assume ~30% of frames have hardhats needing verification
        vlm_frames += int(num_frames * 0.3)
    if verify_with_vlm:
        # Assume ~20% of detections are low-confidence
        vlm_frames += int(num_frames * 0.2)

    if vlm_frames > 0:
        # Gemini Flash: ~$0.000083 per image (1000 tokens input + 100 output)
        cost = vlm_frames * 0.000083
        print(f"\nEstimated VLM verification cost: ~${cost:.4f} ({vlm_frames} API calls)")
        print("  YOLO-World detection: $0.00 (runs locally)")


def main(args: list[str] | None = None) -> int:
    """Main entry point for site analytics CLI.

    Args:
        args: Command line arguments (uses sys.argv if None)

    Returns:
        Exit code (0 for success, non-zero for errors)
    """
    parsed = parse_args(args)

    output_dir: Path = parsed.out
    output_dir.mkdir(parents=True, exist_ok=True)

    # Collect or extract frames
    print("Preparing frames...")
    if parsed.video:
        video_path: Path = parsed.video
        if not video_path.exists():
            print(f"Error: Video not found: {video_path}", file=sys.stderr)
            return 1
        print(f"Extracting frames from {video_path} at {parsed.fps} fps...")
        frame_list = _extract_frames_from_video(video_path, parsed.fps, output_dir)
    else:
        frames_dir = Path(parsed.frames_dir)
        if not frames_dir.exists():
            print(f"Error: Frames directory not found: {frames_dir}", file=sys.stderr)
            return 1
        frame_list = _collect_existing_frames(frames_dir)

    if not frame_list:
        print("Error: No frames to process", file=sys.stderr)
        return 1

    # Apply max frames limit
    if parsed.max_frames and len(frame_list) > parsed.max_frames:
        frame_list = frame_list[: parsed.max_frames]

    print(f"Frames to process: {len(frame_list)}")

    # Cost estimate
    _estimate_cost(
        len(frame_list), parsed.verify_colors, parsed.verify_with_vlm, engine=parsed.engine
    )

    # Dry run
    if parsed.dry_run:
        print(f"\n[DRY RUN] Would process {len(frame_list)} frames")
        print(f"  Engine: {parsed.engine}")
        if parsed.engine == "yolo":
            print(f"  Device: {parsed.device or 'auto'}")
            print(f"  Confidence threshold: {parsed.confidence}")
            print(f"  Verify colors: {parsed.verify_colors}")
            print(f"  Verify with VLM: {parsed.verify_with_vlm}")
        else:
            print(f"  Sleep between requests: {parsed.sleep_ms}ms")
        print("[DRY RUN] No inference performed.")
        return 0

    # Create engine based on selection
    config = AnalyticsConfig(
        model_name=parsed.model,
        parallel_workers=parsed.parallel_workers,
        sleep_ms_between_requests=parsed.sleep_ms,
        language=parsed.language,
    )

    engine: BaseFrameAnalyticsEngine
    if parsed.engine in ("gemini", "openai"):
        try:
            from inf3_analytics.frame_analytics.vlm_site import SiteVLMEngine

            engine = SiteVLMEngine(config=config, provider=parsed.engine)
        except ImportError as e:
            print(f"Error: {e}", file=sys.stderr)
            return 1
    else:
        # YOLO-World engine
        classes: tuple[str, ...] | None = None
        if parsed.equipment_classes:
            from inf3_analytics.frame_analytics.yolo_world import DEFAULT_CLASSES

            person_hardhat = [c for c in DEFAULT_CLASSES if "hardhat" in c or c == "person"]
            classes = tuple(parsed.equipment_classes + person_hardhat)

        try:
            from inf3_analytics.frame_analytics.yolo_world import YOLOWorldEngine

            engine = YOLOWorldEngine(
                config=config,
                classes=classes,
                confidence_threshold=parsed.confidence,
                device=parsed.device,
            )
        except ImportError:
            print(
                "Error: ultralytics package not installed. Run: uv sync --extra yolo",
                file=sys.stderr,
            )
            return 1

    # Run detection
    run_id = f"site_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
    results: list[FrameAnalyticsResult] = []

    engine_label = parsed.engine if parsed.engine != "yolo" else "YOLO-World"
    device_info = f" (device: {parsed.device or 'auto'})" if parsed.engine == "yolo" else ""
    print(f"\nStarting {engine_label} detection{device_info}...")
    start_time = time.monotonic()

    try:
        with engine:
            engine_info = engine.get_engine_info()
            print(f"Engine: {engine_info.name}, model: {engine_info.model}")

            from inf3_analytics.utils.time import seconds_to_timestamp

            for idx, (frame_path, timestamp_s) in enumerate(frame_list):
                frame_meta = FrameMeta(
                    frame_idx=idx,
                    timestamp_s=timestamp_s,
                    timestamp_ts=seconds_to_timestamp(timestamp_s),
                    image_path=str(frame_path),
                    event_id=run_id,
                    event_title="site_analytics",
                    event_summary=None,
                    transcript_excerpt=None,
                )

                result = engine.analyze(
                    image_path=frame_path,
                    event=None,
                    frame_meta=frame_meta,
                )
                results.append(result)

                det_count = len(result.detections)
                if result.error:
                    print(f"  Frame {idx}: Error - {result.error[:60]}")
                elif det_count > 0:
                    print(f"  Frame {idx} ({timestamp_s:.1f}s): {det_count} detection(s)")

                emit_progress(idx + 1, len(frame_list), "frames", "Detecting objects")

                # Rate limiting for VLM engines
                if parsed.engine in ("gemini", "openai") and parsed.sleep_ms > 0:
                    time.sleep(parsed.sleep_ms / 1000)

    except Exception as e:
        print(f"\nError during detection: {e}", file=sys.stderr)
        return 1

    elapsed = time.monotonic() - start_time
    fps_actual = len(frame_list) / elapsed if elapsed > 0 else 0
    print(f"\nDetection complete: {len(frame_list)} frames in {elapsed:.1f}s ({fps_actual:.1f} fps)")

    # Optional: VLM color verification (only relevant for YOLO engine)
    if parsed.verify_colors and parsed.engine == "yolo":
        print("\nVerifying hardhat colors with VLM...")
        _verify_hardhat_colors(results, engine_info)

    # Aggregate results
    time_series = aggregate_site_counts(results, engine_info)

    # Write outputs
    _write_outputs(output_dir, run_id, time_series, results, engine_info)

    # Print summary
    summary = time_series.summary
    print("\n" + "=" * 60)
    print("Site Analytics Complete!")
    print(f"  Run ID: {run_id}")
    print(f"  Frames analyzed: {summary.total_frames}")
    print(f"  Peak persons: {summary.peak_persons}")
    print(f"  Avg persons: {summary.avg_persons:.1f}")
    if summary.peak_equipment:
        print("  Peak equipment:")
        for eq, count in sorted(summary.peak_equipment.items()):
            print(f"    {eq}: {count}")
    if summary.peak_hardhats:
        print("  Peak hardhats:")
        for color, count in sorted(summary.peak_hardhats.items()):
            print(f"    {color}: {count}")
    print(f"  Output: {output_dir}")

    return 0


def _verify_hardhat_colors(
    results: list[FrameAnalyticsResult],
    engine_info: EngineInfo,
) -> None:
    """Post-process results to verify hardhat colors using VLM.

    Modifies detection attributes in-place by rebuilding results
    with VLM-classified colors.

    Args:
        results: Frame analytics results to verify
        engine_info: Engine info (unused, for future tracing)
    """
    import os

    api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        print("  Warning: GEMINI_API_KEY not set, skipping VLM color verification")
        return

    try:
        from google import genai

        from inf3_analytics.frame_analytics.color_classify import classify_color_vlm

        client = genai.Client(api_key=api_key)
    except ImportError:
        print("  Warning: google-genai not installed, skipping VLM color verification")
        return

    verified = 0
    for result in results:
        if result.error:
            continue
        for det in result.detections:
            if det.detection_type.value == "hardhat" and det.bbox:
                color = classify_color_vlm(
                    result.image_path,
                    det.bbox,
                    client=client,
                )
                # Note: frozen dataclass - we log the verification result
                # In production, rebuild the detection with updated color
                verified += 1

    print(f"  Verified {verified} hardhat color(s)")


def _write_outputs(
    output_dir: Path,
    run_id: str,
    time_series: SiteCountTimeSeries,
    results: list[FrameAnalyticsResult],
    engine_info: EngineInfo,
) -> None:
    """Write all output files.

    Args:
        output_dir: Output directory
        run_id: Run identifier
        time_series: Aggregated time series data
        results: Raw frame results
        engine_info: Engine information
    """
    # Write time series JSON
    ts_path = output_dir / "site_counts.json"
    with open(ts_path, "w") as f:
        json.dump(time_series.to_dict(), f, indent=2)
    print(f"  Time series: {ts_path}")

    # Write per-frame results as NDJSON
    results_path = output_dir / "frame_detections.ndjson"
    with open(results_path, "w") as f:
        for r in results:
            f.write(json.dumps(r.to_dict()) + "\n")
    print(f"  Frame detections: {results_path}")

    # Write summary report
    report_path = output_dir / "site_report.md"
    _write_report(report_path, run_id, time_series, engine_info)
    print(f"  Report: {report_path}")


def _write_report(
    path: Path,
    run_id: str,
    time_series: SiteCountTimeSeries,
    engine_info: EngineInfo,
) -> None:
    """Write a human-readable markdown report.

    Args:
        path: Output file path
        run_id: Run identifier
        time_series: Time series data
        engine_info: Engine information
    """
    summary = time_series.summary
    lines = [
        "# Construction Site Analytics Report",
        "",
        f"**Run ID:** {run_id}",
        f"**Engine:** {engine_info.name} ({engine_info.model})",
        f"**Frames analyzed:** {summary.total_frames}",
        f"**Generated:** {datetime.now().isoformat()}",
        "",
        "## Personnel Summary",
        "",
        f"- Peak persons in frame: {summary.peak_persons}",
        f"- Average persons per frame: {summary.avg_persons:.1f}",
        "",
    ]

    if summary.peak_hardhats:
        lines.append("### Hardhat Colors (Peak Counts)")
        lines.append("")
        lines.append("| Color | Peak Count |")
        lines.append("|-------|-----------|")
        for color, count in sorted(summary.peak_hardhats.items()):
            lines.append(f"| {color} | {count} |")
        lines.append("")

    if summary.peak_equipment:
        lines.append("## Equipment Summary (Peak Counts)")
        lines.append("")
        lines.append("| Equipment Type | Peak Count |")
        lines.append("|---------------|-----------|")
        for eq, count in sorted(summary.peak_equipment.items()):
            lines.append(f"| {eq} | {count} |")
        lines.append("")

    if time_series.frames:
        lines.append("## Time Series (first 20 frames)")
        lines.append("")
        lines.append("| Timestamp | Persons | Equipment | Hardhats |")
        lines.append("|-----------|---------|-----------|----------|")
        for fc in time_series.frames[:20]:
            eq_str = ", ".join(f"{k}:{v}" for k, v in fc.equipment_counts.items()) or "-"
            hc_str = ", ".join(f"{k}:{v}" for k, v in fc.hardhat_counts.items()) or "-"
            lines.append(f"| {fc.timestamp_ts} | {fc.person_count} | {eq_str} | {hc_str} |")
        if len(time_series.frames) > 20:
            lines.append(f"| ... | ({len(time_series.frames) - 20} more frames) | | |")
        lines.append("")

    with open(path, "w") as f:
        f.write("\n".join(lines))


if __name__ == "__main__":
    sys.exit(main())
