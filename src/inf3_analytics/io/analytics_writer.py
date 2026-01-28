"""IO utilities for frame analytics outputs."""

import json
from pathlib import Path

from inf3_analytics.types.detection import (
    AnalyticsManifest,
    EventAnalyticsSummary,
    FrameAnalyticsResult,
)


def write_frame_result_jsonl(
    results: list[FrameAnalyticsResult],
    path: Path,
) -> None:
    """Write frame analysis results to JSONL file (one JSON per line).

    Args:
        results: List of frame analysis results
        path: Output file path
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for result in results:
            json.dump(result.to_dict(), f, ensure_ascii=False)
            f.write("\n")


def read_frame_results_jsonl(path: Path) -> list[FrameAnalyticsResult]:
    """Read frame analysis results from JSONL file.

    Args:
        path: Input file path

    Returns:
        List of FrameAnalyticsResult
    """
    results: list[FrameAnalyticsResult] = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                data = json.loads(line)
                results.append(FrameAnalyticsResult.from_dict(data))
    return results


def write_event_summary(
    summary: EventAnalyticsSummary,
    path: Path,
) -> None:
    """Write event analytics summary to JSON file.

    Args:
        summary: Event analytics summary
        path: Output file path
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(summary.to_dict(), f, indent=2, ensure_ascii=False)


def read_event_summary(path: Path) -> EventAnalyticsSummary:
    """Read event analytics summary from JSON file.

    Args:
        path: Input file path

    Returns:
        EventAnalyticsSummary
    """
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    return EventAnalyticsSummary.from_dict(data)


def write_analytics_manifest(
    manifest: AnalyticsManifest,
    path: Path,
) -> None:
    """Write analytics manifest to JSON file.

    Args:
        manifest: Analytics manifest
        path: Output file path
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(manifest.to_dict(), f, indent=2, ensure_ascii=False)


def read_analytics_manifest(path: Path) -> AnalyticsManifest:
    """Read analytics manifest from JSON file.

    Args:
        path: Input file path

    Returns:
        AnalyticsManifest
    """
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    return AnalyticsManifest.from_dict(data)


def _sanitize_dirname(name: str) -> str:
    """Sanitize a string for use as directory name."""
    # Replace problematic characters
    for char in ["<", ">", ":", '"', "/", "\\", "|", "?", "*"]:
        name = name.replace(char, "_")
    # Truncate and strip
    return name[:50].strip().rstrip(".")


def create_event_output_dir(
    base_dir: Path,
    event_id: str,
    event_title: str | None = None,
) -> Path:
    """Create output directory for an event.

    Args:
        base_dir: Base output directory
        event_id: Event identifier
        event_title: Optional event title for directory name

    Returns:
        Path to event output directory
    """
    dir_name = f"{event_id[:12]}_{_sanitize_dirname(event_title)}" if event_title else event_id
    event_dir = base_dir / dir_name
    event_dir.mkdir(parents=True, exist_ok=True)
    return event_dir


def write_event_analytics(
    event_dir: Path,
    results: list[FrameAnalyticsResult],
    summary: EventAnalyticsSummary,
) -> tuple[Path, Path]:
    """Write all analytics outputs for an event.

    Args:
        event_dir: Event output directory
        results: Frame analysis results
        summary: Event summary

    Returns:
        Tuple of (frame_analyses_path, event_summary_path)
    """
    frames_path = event_dir / "frame_analyses.jsonl"
    summary_path = event_dir / "event_summary.json"

    write_frame_result_jsonl(results, frames_path)
    write_event_summary(summary, summary_path)

    return frames_path, summary_path


def generate_analytics_report(
    manifest: AnalyticsManifest,
    summaries: list[EventAnalyticsSummary],
) -> str:
    """Generate a human-readable analytics report.

    Args:
        manifest: Analytics manifest
        summaries: List of event summaries

    Returns:
        Markdown-formatted report string
    """
    lines = [
        "# Frame Analytics Report",
        "",
        f"**Run ID:** {manifest.run_id}",
        f"**Engine:** {manifest.engine.name}",
    ]

    if manifest.engine.provider:
        lines.append(f"**Provider:** {manifest.engine.provider}")
    if manifest.engine.model:
        lines.append(f"**Model:** {manifest.engine.model}")

    lines.extend(
        [
            "",
            "## Summary",
            "",
            f"- Total Events: {manifest.total_events}",
            f"- Total Frames: {manifest.total_frames}",
            f"- Analyzed Frames: {manifest.analyzed_frames}",
            f"- Failed Frames: {manifest.failed_frames}",
            "",
            "## Events",
            "",
        ]
    )

    for summary in summaries:
        lines.append(f"### Event: {summary.event_id}")
        lines.append("")
        lines.append(
            f"- Time Range: {summary.time_range.start_s:.2f}s - {summary.time_range.end_s:.2f}s"
        )
        lines.append(f"- Frames Analyzed: {summary.analyzed_count}/{summary.frame_count}")

        if summary.top_findings:
            lines.append("- Top Findings:")
            for finding in summary.top_findings[:5]:
                sev = f" ({finding.severity.value})" if finding.severity else ""
                lines.append(
                    f"  - {finding.detection_type.value}: {finding.label} "
                    f"(conf: {finding.max_confidence:.0%}, frames: {finding.frame_count}){sev}"
                )
        else:
            lines.append("- No issues detected")

        lines.append("")

    return "\n".join(lines)


def write_analytics_report(
    manifest: AnalyticsManifest,
    summaries: list[EventAnalyticsSummary],
    path: Path,
) -> None:
    """Write human-readable analytics report.

    Args:
        manifest: Analytics manifest
        summaries: List of event summaries
        path: Output file path
    """
    report = generate_analytics_report(manifest, summaries)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(report)
