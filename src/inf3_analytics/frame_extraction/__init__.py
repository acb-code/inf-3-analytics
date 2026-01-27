"""Frame extraction module for extracting frames from video events."""

from inf3_analytics.frame_extraction.extract import extract_event_frames
from inf3_analytics.frame_extraction.policies import (
    FixedFPSWithinEventPolicy,
    FrameSamplingPolicy,
    NFramesPerEventPolicy,
)

__all__ = [
    "extract_event_frames",
    "FrameSamplingPolicy",
    "NFramesPerEventPolicy",
    "FixedFPSWithinEventPolicy",
]
