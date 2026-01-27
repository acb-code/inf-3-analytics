"""Event data types for transcript analysis."""

from dataclasses import dataclass
from enum import Enum
from typing import Any


class EventType(Enum):
    """Categories of events detectable in infrastructure inspection transcripts."""

    OBSERVATION = "observation"
    STRUCTURAL_ANOMALY = "structural_anomaly"
    MAINTENANCE_NOTE = "maintenance_note"
    SAFETY_RISK = "safety_risk"
    MEASUREMENT = "measurement"
    LOCATION_REFERENCE = "location_reference"
    UNCERTAINTY = "uncertainty"
    OTHER = "other"


class EventSeverity(Enum):
    """Severity classification for events."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


@dataclass(frozen=True, slots=True)
class TranscriptReference:
    """Reference to transcript segments that sourced an event."""

    segment_ids: tuple[int, ...]
    excerpt: str
    keywords: tuple[str, ...] | None

    def to_dict(self) -> dict[str, list[int] | str | list[str] | None]:
        """Convert to dictionary for serialization."""
        return {
            "segment_ids": list(self.segment_ids),
            "excerpt": self.excerpt,
            "keywords": list(self.keywords) if self.keywords else None,
        }

    @classmethod
    def from_dict(
        cls, data: dict[str, list[int] | str | list[str] | None]
    ) -> "TranscriptReference":
        """Create TranscriptReference from dictionary."""
        segment_ids_data = data["segment_ids"]
        if not isinstance(segment_ids_data, list):
            raise ValueError("segment_ids must be a list")

        keywords_data = data.get("keywords")
        keywords = None
        if keywords_data is not None and isinstance(keywords_data, list):
            keywords = tuple(str(k) for k in keywords_data)

        return cls(
            segment_ids=tuple(int(i) for i in segment_ids_data),
            excerpt=str(data["excerpt"]),
            keywords=keywords,
        )


@dataclass(frozen=True, slots=True)
class EventMetadata:
    """Metadata about event extraction process."""

    extractor_engine: str
    extractor_version: str
    created_at: str
    source_transcript_path: str | None

    def to_dict(self) -> dict[str, str | None]:
        """Convert to dictionary for serialization."""
        return {
            "extractor_engine": self.extractor_engine,
            "extractor_version": self.extractor_version,
            "created_at": self.created_at,
            "source_transcript_path": self.source_transcript_path,
        }

    @classmethod
    def from_dict(cls, data: dict[str, str | None]) -> "EventMetadata":
        """Create EventMetadata from dictionary."""
        return cls(
            extractor_engine=str(data["extractor_engine"]),
            extractor_version=str(data["extractor_version"]),
            created_at=str(data["created_at"]),
            source_transcript_path=(
                str(data["source_transcript_path"])
                if data.get("source_transcript_path")
                else None
            ),
        )


@dataclass(frozen=True, slots=True)
class RuleEventCorrelation:
    """Correlation between an LLM event and related rule-based events."""

    rule_event_ids: tuple[str, ...]
    correlation_reason: str
    overlap_score: float  # 0.0-1.0, based on temporal/semantic overlap

    def to_dict(self) -> dict[str, list[str] | str | float]:
        """Convert to dictionary for serialization."""
        return {
            "rule_event_ids": list(self.rule_event_ids),
            "correlation_reason": self.correlation_reason,
            "overlap_score": self.overlap_score,
        }

    @classmethod
    def from_dict(cls, data: dict[str, list[str] | str | float]) -> "RuleEventCorrelation":
        """Create RuleEventCorrelation from dictionary."""
        rule_event_ids_data = data["rule_event_ids"]
        if not isinstance(rule_event_ids_data, list):
            raise ValueError("rule_event_ids must be a list")

        overlap_score = data["overlap_score"]
        if isinstance(overlap_score, list):
            raise ValueError("overlap_score must be a number")

        return cls(
            rule_event_ids=tuple(str(e) for e in rule_event_ids_data),
            correlation_reason=str(data["correlation_reason"]),
            overlap_score=float(overlap_score),
        )


@dataclass(frozen=True, slots=True)
class Event:
    """A detected event from transcript analysis."""

    event_id: str
    event_type: EventType
    severity: EventSeverity | None
    confidence: float
    start_s: float
    end_s: float
    start_ts: str
    end_ts: str
    title: str
    summary: str
    transcript_ref: TranscriptReference
    suggested_actions: tuple[str, ...] | None
    metadata: EventMetadata
    related_rule_events: RuleEventCorrelation | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "event_id": self.event_id,
            "event_type": self.event_type.value,
            "severity": self.severity.value if self.severity else None,
            "confidence": self.confidence,
            "start_s": self.start_s,
            "end_s": self.end_s,
            "start_ts": self.start_ts,
            "end_ts": self.end_ts,
            "title": self.title,
            "summary": self.summary,
            "transcript_ref": self.transcript_ref.to_dict(),
            "suggested_actions": (
                list(self.suggested_actions) if self.suggested_actions else None
            ),
            "metadata": self.metadata.to_dict(),
            "related_rule_events": (
                self.related_rule_events.to_dict() if self.related_rule_events else None
            ),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Event":
        """Create Event from dictionary."""
        transcript_ref_data = data["transcript_ref"]
        if not isinstance(transcript_ref_data, dict):
            raise ValueError("transcript_ref must be a dict")

        metadata_data = data["metadata"]
        if not isinstance(metadata_data, dict):
            raise ValueError("metadata must be a dict")

        severity_data = data.get("severity")
        severity = EventSeverity(severity_data) if severity_data else None

        suggested_actions_data = data.get("suggested_actions")
        suggested_actions = None
        if suggested_actions_data is not None and isinstance(suggested_actions_data, list):
            suggested_actions = tuple(str(a) for a in suggested_actions_data)

        related_rule_events_data = data.get("related_rule_events")
        related_rule_events = None
        if related_rule_events_data is not None and isinstance(related_rule_events_data, dict):
            related_rule_events = RuleEventCorrelation.from_dict(related_rule_events_data)

        return cls(
            event_id=str(data["event_id"]),
            event_type=EventType(data["event_type"]),
            severity=severity,
            confidence=float(data["confidence"]),
            start_s=float(data["start_s"]),
            end_s=float(data["end_s"]),
            start_ts=str(data["start_ts"]),
            end_ts=str(data["end_ts"]),
            title=str(data["title"]),
            summary=str(data["summary"]),
            transcript_ref=TranscriptReference.from_dict(transcript_ref_data),
            suggested_actions=suggested_actions,
            metadata=EventMetadata.from_dict(metadata_data),
            related_rule_events=related_rule_events,
        )


@dataclass(frozen=True, slots=True)
class EventList:
    """Collection of events with extraction metadata."""

    events: tuple[Event, ...]
    source_transcript_path: str | None
    extraction_engine: str
    extraction_timestamp: str

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "events": [e.to_dict() for e in self.events],
            "source_transcript_path": self.source_transcript_path,
            "extraction_engine": self.extraction_engine,
            "extraction_timestamp": self.extraction_timestamp,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "EventList":
        """Create EventList from dictionary."""
        events_data = data["events"]
        if not isinstance(events_data, list):
            raise ValueError("events must be a list")

        return cls(
            events=tuple(Event.from_dict(e) for e in events_data),
            source_transcript_path=(
                str(data["source_transcript_path"])
                if data.get("source_transcript_path")
                else None
            ),
            extraction_engine=str(data["extraction_engine"]),
            extraction_timestamp=str(data["extraction_timestamp"]),
        )
