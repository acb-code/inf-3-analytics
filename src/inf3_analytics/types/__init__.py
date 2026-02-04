"""Core type definitions for the analytics pipeline."""

from inf3_analytics.types.comment import CommentStore, EventComment
from inf3_analytics.types.event import (
    Event,
    EventList,
    EventMetadata,
    EventSeverity,
    EventType,
    RuleEventCorrelation,
    TranscriptReference,
)
from inf3_analytics.types.frame import (
    EventFrameSet,
    Frame,
    FrameExtractionMetadata,
    FrameExtractionStatus,
    FrameManifest,
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
    "CommentStore",
    "Event",
    "EventComment",
    "EventFrameSet",
    "EventList",
    "EventMetadata",
    "EventSeverity",
    "EventType",
    "Frame",
    "FrameExtractionMetadata",
    "FrameExtractionStatus",
    "FrameManifest",
    "RuleEventCorrelation",
    "Segment",
    "Transcript",
    "TranscriptMetadata",
    "TranscriptReference",
    "TranscriptionEngineType",
    "VideoInfo",
    "Word",
]
