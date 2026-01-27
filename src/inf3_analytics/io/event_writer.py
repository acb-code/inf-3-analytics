"""Event serialization and output writers."""

import json
from pathlib import Path
from typing import Any

from inf3_analytics.types.event import EventList


def write_json(events: EventList, path: Path) -> None:
    """Write events to JSON file.

    Args:
        events: EventList to serialize
        path: Output file path
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    data = events.to_dict()
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def read_json(path: Path) -> EventList:
    """Read events from JSON file.

    Args:
        path: Path to JSON file

    Returns:
        Deserialized EventList

    Raises:
        FileNotFoundError: If file doesn't exist
        json.JSONDecodeError: If file is not valid JSON
        KeyError/ValueError: If JSON structure is invalid
    """
    with open(path, encoding="utf-8") as f:
        data: dict[str, Any] = json.load(f)
    return EventList.from_dict(data)


def write_ndjson(events: EventList, path: Path) -> None:
    """Write events as newline-delimited JSON (one event per line).

    This format is useful for streaming processing and log aggregation.

    Args:
        events: EventList to serialize
        path: Output file path
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for event in events.events:
            f.write(json.dumps(event.to_dict(), ensure_ascii=False) + "\n")


def write_markdown(events: EventList, path: Path) -> None:
    """Write human-readable event summary as Markdown.

    Args:
        events: EventList to format
        path: Output file path
    """
    path.parent.mkdir(parents=True, exist_ok=True)

    content: list[str] = ["# Event Extraction Summary\n"]
    content.append(f"**Source:** {events.source_transcript_path or 'Unknown'}\n")
    content.append(f"**Engine:** {events.extraction_engine}\n")
    content.append(f"**Extracted:** {events.extraction_timestamp}\n")
    content.append(f"**Total Events:** {len(events.events)}\n\n")

    if not events.events:
        content.append("*No events detected.*\n")
    else:
        # Group events by type
        by_type: dict[str, list[Any]] = {}
        for event in events.events:
            type_key = event.event_type.value
            if type_key not in by_type:
                by_type[type_key] = []
            by_type[type_key].append(event)

        content.append("## Events by Type\n\n")

        for event_type, type_events in sorted(by_type.items()):
            type_display = event_type.replace("_", " ").title()
            content.append(f"### {type_display} ({len(type_events)})\n\n")

            for event in type_events:
                severity_badge = ""
                if event.severity:
                    severity_badge = f" [{event.severity.value.upper()}]"

                content.append(f"#### {event.title}{severity_badge}\n\n")
                content.append(f"- **Time:** {event.start_ts} → {event.end_ts}\n")
                content.append(f"- **Confidence:** {event.confidence:.0%}\n")
                content.append(f"- **Summary:** {event.summary}\n")
                content.append(f"- **Excerpt:** \"{event.transcript_ref.excerpt}\"\n")

                if event.transcript_ref.keywords:
                    keywords_str = ", ".join(event.transcript_ref.keywords)
                    content.append(f"- **Keywords:** {keywords_str}\n")

                if event.suggested_actions:
                    content.append("- **Suggested Actions:**\n")
                    for action in event.suggested_actions:
                        content.append(f"  - {action}\n")

                content.append("\n")

    with open(path, "w", encoding="utf-8") as f:
        f.write("".join(content))
