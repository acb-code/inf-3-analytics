"""Infrastructure inspection video analytics pipeline."""

from inf3_analytics.types.transcript import (
    Segment,
    Transcript,
    TranscriptionEngineType,
    TranscriptMetadata,
    Word,
)

__version__ = "0.1.0"

__all__ = [
    "Segment",
    "Transcript",
    "TranscriptMetadata",
    "TranscriptionEngineType",
    "Word",
    "__version__",
]
