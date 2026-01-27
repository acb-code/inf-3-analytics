"""Input/output utilities for the analytics pipeline."""

from inf3_analytics.io.event_writer import read_json as read_events_json
from inf3_analytics.io.event_writer import write_json as write_events_json
from inf3_analytics.io.event_writer import write_markdown as write_events_markdown
from inf3_analytics.io.event_writer import write_ndjson as write_events_ndjson
from inf3_analytics.io.frame_manifest_writer import (
    read_event_frames_json,
    read_manifest,
    write_event_frames_json,
    write_manifest,
)
from inf3_analytics.io.transcript_writer import (
    read_json,
    write_json,
    write_srt,
    write_txt,
)

__all__ = [
    # Transcript IO
    "read_json",
    "write_json",
    "write_srt",
    "write_txt",
    # Event IO
    "read_events_json",
    "write_events_json",
    "write_events_markdown",
    "write_events_ndjson",
    # Frame manifest IO
    "read_event_frames_json",
    "read_manifest",
    "write_event_frames_json",
    "write_manifest",
]
