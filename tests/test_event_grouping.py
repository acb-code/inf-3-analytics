"""Tests for event extraction grouping and merging logic."""

import pytest

from inf3_analytics.engines.event_extraction.base import EventExtractionConfig
from inf3_analytics.engines.event_extraction.rules import (
    RuleBasedEventEngine,
    SegmentWindow,
    TriggerMatch,
)
from inf3_analytics.types.event import EventType
from inf3_analytics.types.transcript import Segment, Transcript


class TestTriggerFinding:
    """Tests for keyword trigger detection."""

    def test_find_triggers_detects_crack(self, inspection_transcript: Transcript) -> None:
        """Test that crack keyword is detected."""
        engine = RuleBasedEventEngine()
        engine.load()

        triggers = engine._find_triggers(inspection_transcript.segments)

        # Should find crack in segments 1 and 2
        crack_triggers = [
            t for t in triggers if EventType.STRUCTURAL_ANOMALY == t.event_type
        ]
        assert len(crack_triggers) >= 1

    def test_find_triggers_detects_corrosion(self, inspection_transcript: Transcript) -> None:
        """Test that corrosion keyword is detected."""
        engine = RuleBasedEventEngine()
        engine.load()

        triggers = engine._find_triggers(inspection_transcript.segments)

        # Should find corrosion in segment 3
        corrosion_triggers = [
            t
            for t in triggers
            if "corrosion" in t.keywords and t.event_type == EventType.STRUCTURAL_ANOMALY
        ]
        assert len(corrosion_triggers) >= 1

    def test_find_triggers_detects_measurement(self, inspection_transcript: Transcript) -> None:
        """Test that measurement keywords are detected."""
        engine = RuleBasedEventEngine()
        engine.load()

        triggers = engine._find_triggers(inspection_transcript.segments)

        # Should find millimeter in segment 2
        measurement_triggers = [
            t for t in triggers if t.event_type == EventType.MEASUREMENT
        ]
        assert len(measurement_triggers) >= 1

    def test_find_triggers_detects_location(self, inspection_transcript: Transcript) -> None:
        """Test that location keywords are detected."""
        engine = RuleBasedEventEngine()
        engine.load()

        triggers = engine._find_triggers(inspection_transcript.segments)

        # Should find section in segments 0 and 5
        location_triggers = [
            t for t in triggers if t.event_type == EventType.LOCATION_REFERENCE
        ]
        assert len(location_triggers) == 0

    def test_find_triggers_empty_segments(self) -> None:
        """Test trigger finding with empty segments."""
        engine = RuleBasedEventEngine()
        engine.load()

        triggers = engine._find_triggers(())

        assert triggers == []

    def test_find_triggers_no_keywords(self) -> None:
        """Test trigger finding with text that has no keywords."""
        engine = RuleBasedEventEngine()
        engine.load()

        segments = (
            Segment(
                id=0,
                start_s=0.0,
                end_s=3.0,
                start_ts="00:00:00,000",
                end_ts="00:00:03,000",
                text="This is a normal sentence with no special words.",
                words=None,
                avg_logprob=-0.2,
                no_speech_prob=0.01,
            ),
        )

        triggers = engine._find_triggers(segments)

        assert triggers == []


class TestConfidenceCalculation:
    """Tests for confidence score calculation."""

    def test_single_keyword_confidence(self) -> None:
        """Test confidence for single keyword match."""
        engine = RuleBasedEventEngine()
        engine.load()

        confidence = engine._calculate_confidence(["repair"], "we need to repair this")

        assert 0.3 <= confidence <= 0.6

    def test_multiple_keywords_increase_confidence(self) -> None:
        """Test that multiple keywords increase confidence."""
        engine = RuleBasedEventEngine()
        engine.load()

        single_conf = engine._calculate_confidence(["repair"], "repair this")
        multi_conf = engine._calculate_confidence(
            ["repair", "replace", "fix"], "repair, replace, or fix this"
        )

        assert multi_conf > single_conf

    def test_high_signal_keyword_boosts_confidence(self) -> None:
        """Test that high-signal keywords boost confidence."""
        engine = RuleBasedEventEngine()
        engine.load()

        normal_conf = engine._calculate_confidence(["repair"], "repair this")
        high_signal_conf = engine._calculate_confidence(["crack"], "crack visible")

        assert high_signal_conf > normal_conf


class TestWindowExpansion:
    """Tests for context window expansion."""

    def test_expand_windows_includes_context(self) -> None:
        """Test that window expansion includes surrounding segments."""
        engine = RuleBasedEventEngine(EventExtractionConfig(context_window=1))
        engine.load()

        segments = tuple(
            Segment(
                id=i,
                start_s=float(i * 3),
                end_s=float((i + 1) * 3),
                start_ts=f"00:00:{i*3:02d},000",
                end_ts=f"00:00:{(i+1)*3:02d},000",
                text=f"Segment {i}",
                words=None,
                avg_logprob=-0.2,
                no_speech_prob=0.01,
            )
            for i in range(5)
        )

        triggers = [
            TriggerMatch(
                segment_id=2,
                event_type=EventType.STRUCTURAL_ANOMALY,
                keywords=("crack",),
                confidence=0.7,
            )
        ]

        windows = engine._expand_windows(triggers, segments)

        assert len(windows) == 1
        # With context_window=1, should include segments 1, 2, 3
        window_ids = [s.id for s in windows[0].segments]
        assert window_ids == [1, 2, 3]

    def test_expand_windows_at_start(self) -> None:
        """Test window expansion at the start of transcript."""
        engine = RuleBasedEventEngine(EventExtractionConfig(context_window=2))
        engine.load()

        segments = tuple(
            Segment(
                id=i,
                start_s=float(i * 3),
                end_s=float((i + 1) * 3),
                start_ts=f"00:00:{i*3:02d},000",
                end_ts=f"00:00:{(i+1)*3:02d},000",
                text=f"Segment {i}",
                words=None,
                avg_logprob=-0.2,
                no_speech_prob=0.01,
            )
            for i in range(5)
        )

        triggers = [
            TriggerMatch(
                segment_id=0,
                event_type=EventType.STRUCTURAL_ANOMALY,
                keywords=("crack",),
                confidence=0.7,
            )
        ]

        windows = engine._expand_windows(triggers, segments)

        assert len(windows) == 1
        # Should include segments 0, 1, 2 (no negative IDs)
        window_ids = [s.id for s in windows[0].segments]
        assert window_ids == [0, 1, 2]

    def test_expand_windows_at_end(self) -> None:
        """Test window expansion at the end of transcript."""
        engine = RuleBasedEventEngine(EventExtractionConfig(context_window=2))
        engine.load()

        segments = tuple(
            Segment(
                id=i,
                start_s=float(i * 3),
                end_s=float((i + 1) * 3),
                start_ts=f"00:00:{i*3:02d},000",
                end_ts=f"00:00:{(i+1)*3:02d},000",
                text=f"Segment {i}",
                words=None,
                avg_logprob=-0.2,
                no_speech_prob=0.01,
            )
            for i in range(5)
        )

        triggers = [
            TriggerMatch(
                segment_id=4,
                event_type=EventType.STRUCTURAL_ANOMALY,
                keywords=("crack",),
                confidence=0.7,
            )
        ]

        windows = engine._expand_windows(triggers, segments)

        assert len(windows) == 1
        # Should include segments 2, 3, 4 (no IDs beyond max)
        window_ids = [s.id for s in windows[0].segments]
        assert window_ids == [2, 3, 4]


class TestWindowMerging:
    """Tests for overlapping window merging."""

    def test_merge_overlapping_same_type(self) -> None:
        """Test that overlapping windows of same type are merged."""
        engine = RuleBasedEventEngine(EventExtractionConfig(merge_gap_s=5.0))
        engine.load()

        seg1 = Segment(
            id=0, start_s=0.0, end_s=3.0, start_ts="00:00:00,000", end_ts="00:00:03,000",
            text="Seg 0", words=None, avg_logprob=-0.2, no_speech_prob=0.01
        )
        seg2 = Segment(
            id=1, start_s=3.0, end_s=6.0, start_ts="00:00:03,000", end_ts="00:00:06,000",
            text="Seg 1", words=None, avg_logprob=-0.2, no_speech_prob=0.01
        )
        seg3 = Segment(
            id=2, start_s=6.0, end_s=9.0, start_ts="00:00:06,000", end_ts="00:00:09,000",
            text="Seg 2", words=None, avg_logprob=-0.2, no_speech_prob=0.01
        )

        windows = [
            SegmentWindow(
                segments=(seg1, seg2),
                event_type=EventType.STRUCTURAL_ANOMALY,
                keywords=("crack",),
                confidence=0.7,
            ),
            SegmentWindow(
                segments=(seg2, seg3),
                event_type=EventType.STRUCTURAL_ANOMALY,
                keywords=("damage",),
                confidence=0.6,
            ),
        ]

        merged = engine._merge_overlapping(windows)

        # Should merge into single window
        assert len(merged) == 1
        # Should have all 3 segments
        assert len(merged[0].segments) == 3
        # Should combine keywords
        assert "crack" in merged[0].keywords
        assert "damage" in merged[0].keywords
        # Should take max confidence
        assert merged[0].confidence == 0.7

    def test_no_merge_different_types(self) -> None:
        """Test that windows of different types are not merged."""
        engine = RuleBasedEventEngine(EventExtractionConfig(merge_gap_s=5.0))
        engine.load()

        seg1 = Segment(
            id=0, start_s=0.0, end_s=3.0, start_ts="00:00:00,000", end_ts="00:00:03,000",
            text="Seg 0", words=None, avg_logprob=-0.2, no_speech_prob=0.01
        )
        seg2 = Segment(
            id=1, start_s=3.0, end_s=6.0, start_ts="00:00:03,000", end_ts="00:00:06,000",
            text="Seg 1", words=None, avg_logprob=-0.2, no_speech_prob=0.01
        )

        windows = [
            SegmentWindow(
                segments=(seg1,),
                event_type=EventType.STRUCTURAL_ANOMALY,
                keywords=("crack",),
                confidence=0.7,
            ),
            SegmentWindow(
                segments=(seg2,),
                event_type=EventType.SAFETY_RISK,
                keywords=("danger",),
                confidence=0.6,
            ),
        ]

        merged = engine._merge_overlapping(windows)

        # Should remain separate
        assert len(merged) == 2

    def test_no_merge_large_gap(self) -> None:
        """Test that windows with large time gap are not merged."""
        engine = RuleBasedEventEngine(EventExtractionConfig(merge_gap_s=5.0))
        engine.load()

        seg1 = Segment(
            id=0, start_s=0.0, end_s=3.0, start_ts="00:00:00,000", end_ts="00:00:03,000",
            text="Seg 0", words=None, avg_logprob=-0.2, no_speech_prob=0.01
        )
        seg2 = Segment(
            id=1, start_s=20.0, end_s=23.0, start_ts="00:00:20,000", end_ts="00:00:23,000",
            text="Seg 1", words=None, avg_logprob=-0.2, no_speech_prob=0.01
        )

        windows = [
            SegmentWindow(
                segments=(seg1,),
                event_type=EventType.STRUCTURAL_ANOMALY,
                keywords=("crack",),
                confidence=0.7,
            ),
            SegmentWindow(
                segments=(seg2,),
                event_type=EventType.STRUCTURAL_ANOMALY,
                keywords=("damage",),
                confidence=0.6,
            ),
        ]

        merged = engine._merge_overlapping(windows)

        # Should remain separate (gap > 5 seconds)
        assert len(merged) == 2


class TestDeterministicEventIds:
    """Tests for deterministic event ID generation."""

    def test_same_inputs_same_id(self) -> None:
        """Test that same inputs produce same ID."""
        engine = RuleBasedEventEngine()
        engine.load()

        id1 = engine._generate_event_id(
            EventType.STRUCTURAL_ANOMALY, 5.0, (1, 2, 3)
        )
        id2 = engine._generate_event_id(
            EventType.STRUCTURAL_ANOMALY, 5.0, (1, 2, 3)
        )

        assert id1 == id2

    def test_different_type_different_id(self) -> None:
        """Test that different event types produce different IDs."""
        engine = RuleBasedEventEngine()
        engine.load()

        id1 = engine._generate_event_id(
            EventType.STRUCTURAL_ANOMALY, 5.0, (1, 2, 3)
        )
        id2 = engine._generate_event_id(
            EventType.SAFETY_RISK, 5.0, (1, 2, 3)
        )

        assert id1 != id2

    def test_different_time_different_id(self) -> None:
        """Test that different start times produce different IDs."""
        engine = RuleBasedEventEngine()
        engine.load()

        id1 = engine._generate_event_id(
            EventType.STRUCTURAL_ANOMALY, 5.0, (1, 2, 3)
        )
        id2 = engine._generate_event_id(
            EventType.STRUCTURAL_ANOMALY, 10.0, (1, 2, 3)
        )

        assert id1 != id2

    def test_different_segments_different_id(self) -> None:
        """Test that different segment IDs produce different IDs."""
        engine = RuleBasedEventEngine()
        engine.load()

        id1 = engine._generate_event_id(
            EventType.STRUCTURAL_ANOMALY, 5.0, (1, 2, 3)
        )
        id2 = engine._generate_event_id(
            EventType.STRUCTURAL_ANOMALY, 5.0, (1, 2, 4)
        )

        assert id1 != id2

    def test_id_format(self) -> None:
        """Test that event ID has expected format."""
        engine = RuleBasedEventEngine()
        engine.load()

        event_id = engine._generate_event_id(
            EventType.STRUCTURAL_ANOMALY, 5.123, (1, 2)
        )

        # Should be: {type}_{start_ms}_{hash}
        parts = event_id.split("_")
        assert parts[0] == "structural"
        assert parts[1] == "anomaly"
        assert parts[2] == "5123"  # milliseconds
        assert len(parts[3]) == 8  # hash suffix
