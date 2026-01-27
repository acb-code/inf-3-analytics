"""Tests for rule-based event extraction engine."""

import pytest

from inf3_analytics.engines.event_extraction import get_engine, list_engines
from inf3_analytics.engines.event_extraction.base import EventExtractionConfig
from inf3_analytics.engines.event_extraction.rules import RuleBasedEventEngine
from inf3_analytics.types.event import EventSeverity, EventType
from inf3_analytics.types.transcript import (
    Segment,
    Transcript,
    TranscriptMetadata,
    TranscriptionEngineType,
)


class TestEngineRegistry:
    """Tests for event extraction engine registry."""

    def test_list_engines_returns_rules(self) -> None:
        """Test that rules engine is listed."""
        engines = list_engines()
        assert "rules" in engines

    def test_list_engines_returns_openai(self) -> None:
        """Test that OpenAI engine is listed."""
        engines = list_engines()
        assert "openai" in engines

    def test_list_engines_returns_gemini(self) -> None:
        """Test that Gemini engine is listed."""
        engines = list_engines()
        assert "gemini" in engines

    def test_get_engine_rules(self) -> None:
        """Test getting rules engine by name."""
        engine_class = get_engine("rules")
        assert engine_class == RuleBasedEventEngine

    def test_get_engine_alias(self) -> None:
        """Test getting engine by alias."""
        engine_class = get_engine("rule-based")
        assert engine_class == RuleBasedEventEngine

    def test_get_engine_unknown_raises(self) -> None:
        """Test that unknown engine raises ValueError."""
        with pytest.raises(ValueError, match="Unknown engine"):
            get_engine("unknown-engine")


class TestRuleBasedEngineLifecycle:
    """Tests for engine load/unload lifecycle."""

    def test_engine_starts_unloaded(self) -> None:
        """Test that engine starts in unloaded state."""
        engine = RuleBasedEventEngine()
        assert not engine.is_loaded

    def test_engine_load(self) -> None:
        """Test engine loading."""
        engine = RuleBasedEventEngine()
        engine.load()
        assert engine.is_loaded
        engine.unload()

    def test_engine_unload(self) -> None:
        """Test engine unloading."""
        engine = RuleBasedEventEngine()
        engine.load()
        engine.unload()
        assert not engine.is_loaded

    def test_engine_context_manager(self) -> None:
        """Test engine as context manager."""
        with RuleBasedEventEngine() as engine:
            assert engine.is_loaded
        # After context, should be unloaded
        assert not engine.is_loaded

    def test_engine_double_load_is_safe(self) -> None:
        """Test that loading twice is safe."""
        engine = RuleBasedEventEngine()
        engine.load()
        engine.load()  # Should not raise
        assert engine.is_loaded
        engine.unload()


class TestRuleBasedEngineExtraction:
    """Tests for event extraction behavior."""

    def test_extract_from_inspection_transcript(
        self, inspection_transcript: Transcript
    ) -> None:
        """Test extraction from inspection transcript."""
        with RuleBasedEventEngine() as engine:
            events = engine.extract(inspection_transcript)

        # Should extract multiple events
        assert len(events) > 0

    def test_extract_finds_structural_anomalies(
        self, inspection_transcript: Transcript
    ) -> None:
        """Test that structural anomalies are detected."""
        with RuleBasedEventEngine() as engine:
            events = engine.extract(inspection_transcript)

        structural_events = [
            e for e in events if e.event_type == EventType.STRUCTURAL_ANOMALY
        ]
        assert len(structural_events) >= 1

    def test_extract_finds_maintenance_notes(
        self, inspection_transcript: Transcript
    ) -> None:
        """Test that maintenance notes are detected."""
        with RuleBasedEventEngine() as engine:
            events = engine.extract(inspection_transcript)

        maintenance_events = [
            e for e in events if e.event_type == EventType.MAINTENANCE_NOTE
        ]
        assert len(maintenance_events) >= 1

    def test_extract_empty_transcript(self) -> None:
        """Test extraction from empty transcript."""
        metadata = TranscriptMetadata(
            engine=TranscriptionEngineType.FASTER_WHISPER,
            model_name="base",
            language="en",
            detected_language="en",
            language_probability=0.98,
            duration_s=0.0,
            source_video=None,
            source_audio=None,
        )
        transcript = Transcript(
            full_text="",
            segments=(),
            metadata=metadata,
        )

        with RuleBasedEventEngine() as engine:
            events = engine.extract(transcript)

        assert events == ()

    def test_extract_no_keywords_transcript(self) -> None:
        """Test extraction from transcript with no keyword matches."""
        metadata = TranscriptMetadata(
            engine=TranscriptionEngineType.FASTER_WHISPER,
            model_name="base",
            language="en",
            detected_language="en",
            language_probability=0.98,
            duration_s=5.0,
            source_video=None,
            source_audio=None,
        )
        segment = Segment(
            id=0,
            start_s=0.0,
            end_s=5.0,
            start_ts="00:00:00,000",
            end_ts="00:00:05,000",
            text="Hello this is a normal sentence.",
            words=None,
            avg_logprob=-0.2,
            no_speech_prob=0.01,
        )
        transcript = Transcript(
            full_text="Hello this is a normal sentence.",
            segments=(segment,),
            metadata=metadata,
        )

        with RuleBasedEventEngine() as engine:
            events = engine.extract(transcript)

        assert events == ()

    def test_extract_with_min_confidence_filter(self) -> None:
        """Test that min_confidence filters low confidence events."""
        metadata = TranscriptMetadata(
            engine=TranscriptionEngineType.FASTER_WHISPER,
            model_name="base",
            language="en",
            detected_language="en",
            language_probability=0.98,
            duration_s=5.0,
            source_video=None,
            source_audio=None,
        )
        segment = Segment(
            id=0,
            start_s=0.0,
            end_s=5.0,
            start_ts="00:00:00,000",
            end_ts="00:00:05,000",
            text="The area needs some maintenance.",
            words=None,
            avg_logprob=-0.2,
            no_speech_prob=0.01,
        )
        transcript = Transcript(
            full_text="The area needs some maintenance.",
            segments=(segment,),
            metadata=metadata,
        )

        # With high min_confidence, should filter out low-confidence matches
        config = EventExtractionConfig(min_confidence=0.99)
        with RuleBasedEventEngine(config) as engine:
            events = engine.extract(transcript)

        assert len(events) == 0

    def test_event_has_required_fields(
        self, inspection_transcript: Transcript
    ) -> None:
        """Test that extracted events have all required fields."""
        with RuleBasedEventEngine() as engine:
            events = engine.extract(inspection_transcript)

        assert len(events) > 0
        event = events[0]

        # Check all required fields
        assert event.event_id
        assert event.event_type in EventType
        assert 0.0 <= event.confidence <= 1.0
        assert event.start_s >= 0
        assert event.end_s >= event.start_s
        assert event.start_ts
        assert event.end_ts
        assert event.title
        assert event.summary
        assert event.transcript_ref
        assert event.transcript_ref.segment_ids
        assert event.transcript_ref.excerpt
        assert event.metadata
        assert event.metadata.extractor_engine == "rules"

    def test_event_timestamps_are_aligned(
        self, inspection_transcript: Transcript
    ) -> None:
        """Test that event timestamps align with source segments."""
        with RuleBasedEventEngine() as engine:
            events = engine.extract(inspection_transcript)

        segment_by_id = {s.id: s for s in inspection_transcript.segments}

        for event in events:
            # Get segments referenced by this event
            ref_segments = [
                segment_by_id[sid]
                for sid in event.transcript_ref.segment_ids
                if sid in segment_by_id
            ]

            if ref_segments:
                # Event start should match first segment start
                assert event.start_s == ref_segments[0].start_s
                # Event end should match last segment end
                assert event.end_s == ref_segments[-1].end_s


class TestSeverityDetection:
    """Tests for event severity detection."""

    def test_high_severity_detected(self) -> None:
        """Test that high severity keywords are detected."""
        metadata = TranscriptMetadata(
            engine=TranscriptionEngineType.FASTER_WHISPER,
            model_name="base",
            language="en",
            detected_language="en",
            language_probability=0.98,
            duration_s=5.0,
            source_video=None,
            source_audio=None,
        )
        segment = Segment(
            id=0,
            start_s=0.0,
            end_s=5.0,
            start_ts="00:00:00,000",
            end_ts="00:00:05,000",
            text="There is a severe crack that is dangerous.",
            words=None,
            avg_logprob=-0.2,
            no_speech_prob=0.01,
        )
        transcript = Transcript(
            full_text=segment.text,
            segments=(segment,),
            metadata=metadata,
        )

        with RuleBasedEventEngine() as engine:
            events = engine.extract(transcript)

        # Should have at least one event with HIGH severity
        high_severity = [e for e in events if e.severity == EventSeverity.HIGH]
        assert len(high_severity) >= 1

    def test_medium_severity_detected(self) -> None:
        """Test that medium severity keywords are detected."""
        metadata = TranscriptMetadata(
            engine=TranscriptionEngineType.FASTER_WHISPER,
            model_name="base",
            language="en",
            detected_language="en",
            language_probability=0.98,
            duration_s=5.0,
            source_video=None,
            source_audio=None,
        )
        segment = Segment(
            id=0,
            start_s=0.0,
            end_s=5.0,
            start_ts="00:00:00,000",
            end_ts="00:00:05,000",
            text="There is a noticeable crack visible in the surface.",
            words=None,
            avg_logprob=-0.2,
            no_speech_prob=0.01,
        )
        transcript = Transcript(
            full_text=segment.text,
            segments=(segment,),
            metadata=metadata,
        )

        with RuleBasedEventEngine() as engine:
            events = engine.extract(transcript)

        # Should have at least one event with MEDIUM severity
        medium_severity = [e for e in events if e.severity == EventSeverity.MEDIUM]
        assert len(medium_severity) >= 1

    def test_low_severity_detected(self) -> None:
        """Test that low severity keywords are detected."""
        metadata = TranscriptMetadata(
            engine=TranscriptionEngineType.FASTER_WHISPER,
            model_name="base",
            language="en",
            detected_language="en",
            language_probability=0.98,
            duration_s=5.0,
            source_video=None,
            source_audio=None,
        )
        segment = Segment(
            id=0,
            start_s=0.0,
            end_s=5.0,
            start_ts="00:00:00,000",
            end_ts="00:00:05,000",
            text="There is a minor crack, very slight damage.",
            words=None,
            avg_logprob=-0.2,
            no_speech_prob=0.01,
        )
        transcript = Transcript(
            full_text=segment.text,
            segments=(segment,),
            metadata=metadata,
        )

        with RuleBasedEventEngine() as engine:
            events = engine.extract(transcript)

        # Should have at least one event with LOW severity
        low_severity = [e for e in events if e.severity == EventSeverity.LOW]
        assert len(low_severity) >= 1


class TestSuggestedActions:
    """Tests for suggested action generation."""

    def test_structural_anomaly_has_actions(
        self, inspection_transcript: Transcript
    ) -> None:
        """Test that structural anomaly events have suggested actions."""
        with RuleBasedEventEngine() as engine:
            events = engine.extract(inspection_transcript)

        structural_events = [
            e for e in events if e.event_type == EventType.STRUCTURAL_ANOMALY
        ]
        assert len(structural_events) >= 1

        # Should have suggested actions
        for event in structural_events:
            assert event.suggested_actions is not None
            assert len(event.suggested_actions) > 0

    def test_maintenance_note_has_actions(
        self, inspection_transcript: Transcript
    ) -> None:
        """Test that maintenance note events have suggested actions."""
        with RuleBasedEventEngine() as engine:
            events = engine.extract(inspection_transcript)

        maintenance_events = [
            e for e in events if e.event_type == EventType.MAINTENANCE_NOTE
        ]
        if maintenance_events:
            for event in maintenance_events:
                assert event.suggested_actions is not None
                assert "maintenance" in " ".join(event.suggested_actions).lower()
