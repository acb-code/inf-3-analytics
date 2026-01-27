"""IO utilities for frame extraction manifests."""

import json
from pathlib import Path
from typing import Any

from inf3_analytics.types.frame import EventFrameSet, FrameManifest


def write_manifest(manifest: FrameManifest, path: Path) -> None:
    """Write frame manifest to JSON file.

    Args:
        manifest: FrameManifest to serialize
        path: Output file path
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(manifest.to_dict(), f, indent=2, ensure_ascii=False)


def read_manifest(path: Path) -> FrameManifest:
    """Read frame manifest from JSON file.

    Args:
        path: Path to manifest JSON file

    Returns:
        Parsed FrameManifest

    Raises:
        FileNotFoundError: If file doesn't exist
        json.JSONDecodeError: If file is not valid JSON
    """
    with open(path, encoding="utf-8") as f:
        data: dict[str, Any] = json.load(f)
    return FrameManifest.from_dict(data)


def write_event_frames_json(event_frame_set: EventFrameSet, path: Path) -> None:
    """Write per-event frames.json file.

    Args:
        event_frame_set: EventFrameSet to serialize
        path: Output file path
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(event_frame_set.to_dict(), f, indent=2, ensure_ascii=False)


def read_event_frames_json(path: Path) -> EventFrameSet:
    """Read per-event frames.json file.

    Args:
        path: Path to frames.json file

    Returns:
        Parsed EventFrameSet

    Raises:
        FileNotFoundError: If file doesn't exist
        json.JSONDecodeError: If file is not valid JSON
    """
    with open(path, encoding="utf-8") as f:
        data: dict[str, Any] = json.load(f)
    return EventFrameSet.from_dict(data)
