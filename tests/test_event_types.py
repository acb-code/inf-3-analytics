"""Tests for event type definitions and serialization."""

import pytest

from inf3_analytics.types.event import (
    Event,
    EventList,
    EventMetadata,
    EventSeverity,
    EventType,
    TranscriptReference,
)


class TestEventTypeEnum:
    """Tests for EventType enum."""

    def test_all_event_types_have_string_values(self) -> None:
        """Test that all event types have string values."""
        for event_type in EventType:
            assert isinstance(event_type.value, str)

    def test_event_type_values_are_unique(self) -> None:
        """Test that all event type values are unique."""
        values = [e.value for e in EventType]
        assert len(values) == len(set(values))

    def test_expected_event_types_exist(self) -> None:
        """Test that expected event types are defined."""
        expected = {
            "observation",
            "structural_anomaly",
            "maintenance_note",
            "safety_risk",
            "measurement",
            "location_reference",
            "uncertainty",
            "other",
        }
        actual = {e.value for e in EventType}
        assert expected == actual


class TestEventSeverityEnum:
    """Tests for EventSeverity enum."""

    def test_all_severities_have_string_values(self) -> None:
        """Test that all severities have string values."""
        for severity in EventSeverity:
            assert isinstance(severity.value, str)

    def test_expected_severities_exist(self) -> None:
        """Test that expected severities are defined."""
        expected = {"low", "medium", "high"}
        actual = {s.value for s in EventSeverity}
        assert expected == actual


class TestTranscriptReference:
    """Tests for TranscriptReference dataclass."""

    def test_to_dict(self, sample_transcript_reference: TranscriptReference) -> None:
        """Test TranscriptReference to_dict serialization."""
        data = sample_transcript_reference.to_dict()

        assert data["segment_ids"] == [2, 3]
        assert data["excerpt"] == "There's a crack visible here in the concrete"
        assert data["keywords"] == ["crack", "concrete"]

    def test_from_dict(self) -> None:
        """Test TranscriptReference from_dict deserialization."""
        data = {
            "segment_ids": [1, 2, 3],
            "excerpt": "Test excerpt",
            "keywords": ["test", "keywords"],
        }

        ref = TranscriptReference.from_dict(data)

        assert ref.segment_ids == (1, 2, 3)
        assert ref.excerpt == "Test excerpt"
        assert ref.keywords == ("test", "keywords")

    def test_from_dict_with_none_keywords(self) -> None:
        """Test TranscriptReference from_dict with null keywords."""
        data = {
            "segment_ids": [1],
            "excerpt": "Test",
            "keywords": None,
        }

        ref = TranscriptReference.from_dict(data)

        assert ref.keywords is None

    def test_roundtrip(self, sample_transcript_reference: TranscriptReference) -> None:
        """Test TranscriptReference serialization roundtrip."""
        data = sample_transcript_reference.to_dict()
        restored = TranscriptReference.from_dict(data)

        assert restored.segment_ids == sample_transcript_reference.segment_ids
        assert restored.excerpt == sample_transcript_reference.excerpt
        assert restored.keywords == sample_transcript_reference.keywords


class TestEventMetadata:
    """Tests for EventMetadata dataclass."""

    def test_to_dict(self, sample_event_metadata: EventMetadata) -> None:
        """Test EventMetadata to_dict serialization."""
        data = sample_event_metadata.to_dict()

        assert data["extractor_engine"] == "rules"
        assert data["extractor_version"] == "1.0.0"
        assert data["created_at"] == "2024-01-15T10:30:00"
        assert data["source_transcript_path"] == "/path/to/transcript.json"

    def test_from_dict(self) -> None:
        """Test EventMetadata from_dict deserialization."""
        data = {
            "extractor_engine": "llm",
            "extractor_version": "2.0.0",
            "created_at": "2024-02-01T12:00:00",
            "source_transcript_path": "/another/path.json",
        }

        metadata = EventMetadata.from_dict(data)

        assert metadata.extractor_engine == "llm"
        assert metadata.extractor_version == "2.0.0"
        assert metadata.created_at == "2024-02-01T12:00:00"
        assert metadata.source_transcript_path == "/another/path.json"

    def test_from_dict_with_none_path(self) -> None:
        """Test EventMetadata from_dict with null source path."""
        data = {
            "extractor_engine": "rules",
            "extractor_version": "1.0.0",
            "created_at": "2024-01-15T10:30:00",
            "source_transcript_path": None,
        }

        metadata = EventMetadata.from_dict(data)

        assert metadata.source_transcript_path is None

    def test_roundtrip(self, sample_event_metadata: EventMetadata) -> None:
        """Test EventMetadata serialization roundtrip."""
        data = sample_event_metadata.to_dict()
        restored = EventMetadata.from_dict(data)

        assert restored.extractor_engine == sample_event_metadata.extractor_engine
        assert restored.extractor_version == sample_event_metadata.extractor_version
        assert restored.created_at == sample_event_metadata.created_at
        assert restored.source_transcript_path == sample_event_metadata.source_transcript_path


class TestEvent:
    """Tests for Event dataclass."""

    def test_to_dict(self, sample_event: Event) -> None:
        """Test Event to_dict serialization."""
        data = sample_event.to_dict()

        assert data["event_id"] == "structural_anomaly_5000_abc12345"
        assert data["event_type"] == "structural_anomaly"
        assert data["severity"] == "medium"
        assert data["confidence"] == 0.75
        assert data["start_s"] == 5.0
        assert data["end_s"] == 10.0
        assert data["start_ts"] == "00:00:05,000"
        assert data["end_ts"] == "00:00:10,000"
        assert data["title"] == "Crack detected"
        assert isinstance(data["transcript_ref"], dict)
        assert isinstance(data["metadata"], dict)
        assert data["suggested_actions"] == ["Schedule detailed inspection"]

    def test_from_dict(self) -> None:
        """Test Event from_dict deserialization."""
        data = {
            "event_id": "test_event_123",
            "event_type": "safety_risk",
            "severity": "high",
            "confidence": 0.9,
            "start_s": 10.0,
            "end_s": 15.0,
            "start_ts": "00:00:10,000",
            "end_ts": "00:00:15,000",
            "title": "Safety hazard",
            "summary": "Potential safety issue detected.",
            "transcript_ref": {
                "segment_ids": [5, 6],
                "excerpt": "This is dangerous",
                "keywords": ["dangerous"],
            },
            "suggested_actions": ["Review safety"],
            "metadata": {
                "extractor_engine": "rules",
                "extractor_version": "1.0.0",
                "created_at": "2024-01-01T00:00:00",
                "source_transcript_path": None,
            },
        }

        event = Event.from_dict(data)

        assert event.event_id == "test_event_123"
        assert event.event_type == EventType.SAFETY_RISK
        assert event.severity == EventSeverity.HIGH
        assert event.confidence == 0.9
        assert event.start_s == 10.0

    def test_from_dict_with_none_severity(self, sample_event_no_severity: Event) -> None:
        """Test Event with null severity."""
        data = sample_event_no_severity.to_dict()
        restored = Event.from_dict(data)

        assert restored.severity is None

    def test_from_dict_with_none_actions(self, sample_event_no_severity: Event) -> None:
        """Test Event with null suggested_actions."""
        data = sample_event_no_severity.to_dict()
        restored = Event.from_dict(data)

        assert restored.suggested_actions is None

    def test_roundtrip(self, sample_event: Event) -> None:
        """Test Event serialization roundtrip."""
        data = sample_event.to_dict()
        restored = Event.from_dict(data)

        assert restored.event_id == sample_event.event_id
        assert restored.event_type == sample_event.event_type
        assert restored.severity == sample_event.severity
        assert restored.confidence == sample_event.confidence
        assert restored.start_s == sample_event.start_s
        assert restored.end_s == sample_event.end_s
        assert restored.title == sample_event.title
        assert restored.summary == sample_event.summary


class TestEventList:
    """Tests for EventList dataclass."""

    def test_to_dict(self, sample_event_list: EventList) -> None:
        """Test EventList to_dict serialization."""
        data = sample_event_list.to_dict()

        assert isinstance(data["events"], list)
        assert len(data["events"]) == 2
        assert data["source_transcript_path"] == "/path/to/transcript.json"
        assert data["extraction_engine"] == "rules"
        assert data["extraction_timestamp"] == "2024-01-15T10:30:00"

    def test_from_dict(self, sample_event_list: EventList) -> None:
        """Test EventList from_dict deserialization."""
        data = sample_event_list.to_dict()
        restored = EventList.from_dict(data)

        assert len(restored.events) == 2
        assert restored.source_transcript_path == sample_event_list.source_transcript_path
        assert restored.extraction_engine == sample_event_list.extraction_engine

    def test_empty_events_list(self) -> None:
        """Test EventList with empty events."""
        event_list = EventList(
            events=(),
            source_transcript_path=None,
            extraction_engine="rules",
            extraction_timestamp="2024-01-01T00:00:00",
        )

        data = event_list.to_dict()
        restored = EventList.from_dict(data)

        assert len(restored.events) == 0

    def test_roundtrip(self, sample_event_list: EventList) -> None:
        """Test EventList serialization roundtrip."""
        data = sample_event_list.to_dict()
        restored = EventList.from_dict(data)

        assert len(restored.events) == len(sample_event_list.events)
        assert restored.source_transcript_path == sample_event_list.source_transcript_path
        assert restored.extraction_engine == sample_event_list.extraction_engine
        assert restored.extraction_timestamp == sample_event_list.extraction_timestamp
