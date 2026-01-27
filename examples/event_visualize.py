"""Visualize events.json summaries and a simple timeline in the terminal.

Run:
  uv run python examples/event_visualize.py --events outputs/events/inspection_events.json
  uv run python examples/event_visualize.py --events outputs/events/*.json --bin-size 10
"""

from __future__ import annotations

import argparse
import statistics
from pathlib import Path

from inf3_analytics.io.event_writer import read_json as read_events_json


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Summarize and visualize event JSON files.",
    )
    parser.add_argument(
        "--events",
        type=str,
        nargs="+",
        required=True,
        help="Event JSON file(s) or glob patterns",
    )
    parser.add_argument(
        "--bin-size",
        type=float,
        default=5.0,
        help="Timeline bin size in seconds (default: 5.0)",
    )
    parser.add_argument(
        "--max-bars",
        type=int,
        default=80,
        help="Max timeline bars (default: 80)",
    )
    return parser.parse_args()


def _collect_paths(patterns: list[str]) -> list[Path]:
    paths: list[Path] = []
    for pattern in patterns:
        expanded = list(Path().glob(pattern))
        if expanded:
            paths.extend(expanded)
        else:
            paths.append(Path(pattern))
    return paths


def _timeline(events: list[dict[str, float]], bin_size: float, max_bars: int) -> str:
    if not events:
        return "(no events)"

    start = min(e["start_s"] for e in events)
    end = max(e["end_s"] for e in events)
    duration = max(end - start, 0.001)

    bins = int(duration // bin_size) + 1
    if bins > max_bars:
        bin_size = duration / max_bars
        bins = max_bars

    counts = [0] * bins
    for event in events:
        idx = int((event["start_s"] - start) // bin_size)
        idx = max(0, min(idx, bins - 1))
        counts[idx] += 1

    max_count = max(counts) if counts else 1
    charset = " ▁▂▃▄▅▆▇█"
    scale = (len(charset) - 1) / max_count if max_count else 1
    bars = "".join(charset[min(int(c * scale), len(charset) - 1)] for c in counts)

    start_label = f"{start:.1f}s"
    end_label = f"{end:.1f}s"
    return f"{start_label} {bars} {end_label} (bin={bin_size:.1f}s)"


def main() -> int:
    args = parse_args()
    paths = _collect_paths(args.events)

    for path in paths:
        if not path.exists():
            print(f"Missing: {path}")
            continue

        event_list = read_events_json(path)
        events = list(event_list.events)
        print(f"\n=== {path} ===")
        print(f"Total events: {len(events)}")
        print(f"Engine: {event_list.extraction_engine}")
        print(f"Extracted: {event_list.extraction_timestamp}")

        if not events:
            continue

        # Summary by type
        by_type: dict[str, int] = {}
        by_severity: dict[str, int] = {}
        confidences = []
        for event in events:
            by_type[event.event_type.value] = by_type.get(event.event_type.value, 0) + 1
            if event.severity:
                by_severity[event.severity.value] = by_severity.get(event.severity.value, 0) + 1
            confidences.append(event.confidence)

        print("\nBy type:")
        for event_type, count in sorted(by_type.items()):
            print(f"  {event_type}: {count}")

        if by_severity:
            print("\nBy severity:")
            for sev, count in sorted(by_severity.items()):
                print(f"  {sev}: {count}")

        if confidences:
            mean = statistics.mean(confidences)
            median = statistics.median(confidences)
            print(f"\nConfidence: mean={mean:.2f} median={median:.2f}")

        # Timeline
        event_times = [
            {"start_s": e.start_s, "end_s": e.end_s} for e in events
        ]
        print("\nTimeline:")
        print(_timeline(event_times, args.bin_size, args.max_bars))

        # All events
        print("\nEvents:")
        for event in sorted(events, key=lambda e: e.start_s):
            sev = f" [{event.severity.value.upper()}]" if event.severity else ""
            print(
                f"- {event.start_ts} {event.title}{sev} "
                f"({event.event_type.value}, {event.confidence:.0%})"
            )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
