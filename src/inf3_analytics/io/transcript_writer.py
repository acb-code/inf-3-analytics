"""Transcript serialization and output writers."""

import json
from pathlib import Path
from typing import Any

from inf3_analytics.types.transcript import Transcript
from inf3_analytics.utils.time import seconds_to_timestamp


def write_json(transcript: Transcript, path: Path) -> None:
    """Write transcript to JSON file.

    Args:
        transcript: Transcript to serialize
        path: Output file path
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    data = transcript.to_dict()
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def read_json(path: Path) -> Transcript:
    """Read transcript from JSON file.

    Args:
        path: Path to JSON file

    Returns:
        Deserialized Transcript

    Raises:
        FileNotFoundError: If file doesn't exist
        json.JSONDecodeError: If file is not valid JSON
        KeyError/ValueError: If JSON structure is invalid
    """
    with open(path, encoding="utf-8") as f:
        data: dict[str, Any] = json.load(f)
    return Transcript.from_dict(data)


def write_txt(
    transcript: Transcript,
    path: Path,
    include_timestamps: bool = True,
) -> None:
    """Write transcript to plain text file.

    Args:
        transcript: Transcript to write
        path: Output file path
        include_timestamps: Whether to include timestamps (default: True)
    """
    path.parent.mkdir(parents=True, exist_ok=True)

    lines: list[str] = []
    for segment in transcript.segments:
        if include_timestamps:
            lines.append(f"[{segment.start_ts} --> {segment.end_ts}]")
        lines.append(segment.text)
        if include_timestamps:
            lines.append("")  # Blank line between segments

    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


def write_srt(transcript: Transcript, path: Path) -> None:
    """Write transcript to SRT (SubRip) subtitle format.

    SRT format:
    1
    00:00:00,000 --> 00:00:05,000
    Subtitle text

    2
    00:00:05,500 --> 00:00:10,000
    Next subtitle

    Args:
        transcript: Transcript to write
        path: Output file path
    """
    path.parent.mkdir(parents=True, exist_ok=True)

    lines: list[str] = []
    for idx, segment in enumerate(transcript.segments, start=1):
        # SRT uses 1-based index
        lines.append(str(idx))

        # Timestamp line: start --> end
        start_ts = seconds_to_timestamp(segment.start_s)
        end_ts = seconds_to_timestamp(segment.end_s)
        lines.append(f"{start_ts} --> {end_ts}")

        # Subtitle text
        lines.append(segment.text)

        # Blank line between entries
        lines.append("")

    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
