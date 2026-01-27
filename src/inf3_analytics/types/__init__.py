"""Core type definitions for the analytics pipeline."""

from inf3_analytics.types.event import (
    Event,
    EventList,
    EventMetadata,
    EventSeverity,
    EventType,
    RuleEventCorrelation,
    TranscriptReference,
)
from inf3_analytics.types.media import AudioInfo, VideoInfo
from inf3_analytics.types.transcript import (
    Segment,
    Transcript,
    TranscriptionEngineType,
    TranscriptMetadata,
    Word,
)

__all__ = [
    "AudioInfo",
    "Event",
    "EventList",
    "EventMetadata",
    "EventSeverity",
    "EventType",
    "RuleEventCorrelation",
    "Segment",
    "Transcript",
    "TranscriptMetadata",
    "TranscriptReference",
    "TranscriptionEngineType",
    "VideoInfo",
    "Word",
]
