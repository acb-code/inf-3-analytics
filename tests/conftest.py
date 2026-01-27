"""Shared test fixtures."""

from pathlib import Path

import pytest

from inf3_analytics.types.event import (
    Event,
    EventList,
    EventMetadata,
    EventSeverity,
    EventType,
    RuleEventCorrelation,
    TranscriptReference,
)
from inf3_analytics.types.transcript import (
    Segment,
    Transcript,
    TranscriptMetadata,
    TranscriptionEngineType,
    Word,
)


@pytest.fixture
def sample_word() -> Word:
    """Create a sample Word for testing."""
    return Word(
        word="Hello",
        start_s=0.0,
        end_s=0.5,
        probability=0.95,
    )


@pytest.fixture
def sample_segment() -> Segment:
    """Create a sample Segment for testing."""
    return Segment(
        id=0,
        start_s=0.0,
        end_s=2.5,
        start_ts="00:00:00,000",
        end_ts="00:00:02,500",
        text="Hello, this is a test segment.",
        words=(
            Word(word="Hello,", start_s=0.0, end_s=0.4, probability=0.98),
            Word(word="this", start_s=0.5, end_s=0.7, probability=0.95),
            Word(word="is", start_s=0.8, end_s=0.9, probability=0.97),
            Word(word="a", start_s=1.0, end_s=1.1, probability=0.99),
            Word(word="test", start_s=1.2, end_s=1.5, probability=0.96),
            Word(word="segment.", start_s=1.6, end_s=2.5, probability=0.94),
        ),
        avg_logprob=-0.25,
        no_speech_prob=0.01,
    )


@pytest.fixture
def sample_segment_no_words() -> Segment:
    """Create a sample Segment without word timestamps."""
    return Segment(
        id=1,
        start_s=3.0,
        end_s=5.5,
        start_ts="00:00:03,000",
        end_ts="00:00:05,500",
        text="This segment has no word-level timestamps.",
        words=None,
        avg_logprob=-0.30,
        no_speech_prob=0.02,
    )


@pytest.fixture
def sample_metadata() -> TranscriptMetadata:
    """Create sample TranscriptMetadata for testing."""
    return TranscriptMetadata(
        engine=TranscriptionEngineType.FASTER_WHISPER,
        model_name="base",
        language="en",
        detected_language="en",
        language_probability=0.98,
        duration_s=10.0,
        source_video=Path("/path/to/video.mp4"),
        source_audio=Path("/path/to/audio.wav"),
    )


@pytest.fixture
def sample_transcript(
    sample_segment: Segment,
    sample_segment_no_words: Segment,
    sample_metadata: TranscriptMetadata,
) -> Transcript:
    """Create a sample Transcript with 2 segments for testing."""
    return Transcript(
        full_text="Hello, this is a test segment. This segment has no word-level timestamps.",
        segments=(sample_segment, sample_segment_no_words),
        metadata=sample_metadata,
    )


@pytest.fixture
def tmp_output_dir(tmp_path: Path) -> Path:
    """Create a temporary output directory."""
    output_dir = tmp_path / "outputs"
    output_dir.mkdir()
    return output_dir


# Event-related fixtures


@pytest.fixture
def sample_transcript_reference() -> TranscriptReference:
    """Create a sample TranscriptReference for testing."""
    return TranscriptReference(
        segment_ids=(2, 3),
        excerpt="There's a crack visible here in the concrete",
        keywords=("crack", "concrete"),
    )


@pytest.fixture
def sample_event_metadata() -> EventMetadata:
    """Create a sample EventMetadata for testing."""
    return EventMetadata(
        extractor_engine="rules",
        extractor_version="1.0.0",
        created_at="2024-01-15T10:30:00",
        source_transcript_path="/path/to/transcript.json",
    )


@pytest.fixture
def sample_event(
    sample_transcript_reference: TranscriptReference,
    sample_event_metadata: EventMetadata,
) -> Event:
    """Create a sample Event for testing."""
    return Event(
        event_id="structural_anomaly_5000_abc12345",
        event_type=EventType.STRUCTURAL_ANOMALY,
        severity=EventSeverity.MEDIUM,
        confidence=0.75,
        start_s=5.0,
        end_s=10.0,
        start_ts="00:00:05,000",
        end_ts="00:00:10,000",
        title="Crack detected",
        summary="Inspector mentions visible crack in concrete surface.",
        transcript_ref=sample_transcript_reference,
        suggested_actions=("Schedule detailed inspection",),
        metadata=sample_event_metadata,
    )


@pytest.fixture
def sample_event_no_severity() -> Event:
    """Create a sample Event without severity for testing."""
    return Event(
        event_id="measurement_15000_def67890",
        event_type=EventType.MEASUREMENT,
        severity=None,
        confidence=0.6,
        start_s=15.0,
        end_s=18.0,
        start_ts="00:00:15,000",
        end_ts="00:00:18,000",
        title="Measurement",
        summary="Inspector reports measurement of 5 millimeters.",
        transcript_ref=TranscriptReference(
            segment_ids=(5,),
            excerpt="The depth here is about 5 millimeters",
            keywords=("millimeter",),
        ),
        suggested_actions=None,
        metadata=EventMetadata(
            extractor_engine="rules",
            extractor_version="1.0.0",
            created_at="2024-01-15T10:30:00",
            source_transcript_path=None,
        ),
    )


@pytest.fixture
def sample_event_list(
    sample_event: Event,
    sample_event_no_severity: Event,
) -> EventList:
    """Create a sample EventList for testing."""
    return EventList(
        events=(sample_event, sample_event_no_severity),
        source_transcript_path="/path/to/transcript.json",
        extraction_engine="rules",
        extraction_timestamp="2024-01-15T10:30:00",
    )


@pytest.fixture
def inspection_transcript() -> Transcript:
    """Create a transcript with inspection-related content for testing event extraction."""
    segments = (
        Segment(
            id=0,
            start_s=0.0,
            end_s=3.0,
            start_ts="00:00:00,000",
            end_ts="00:00:03,000",
            text="Starting inspection of the north section.",
            words=None,
            avg_logprob=-0.2,
            no_speech_prob=0.01,
        ),
        Segment(
            id=1,
            start_s=3.5,
            end_s=7.0,
            start_ts="00:00:03,500",
            end_ts="00:00:07,000",
            text="I can see a crack in the concrete here.",
            words=None,
            avg_logprob=-0.25,
            no_speech_prob=0.02,
        ),
        Segment(
            id=2,
            start_s=7.5,
            end_s=11.0,
            start_ts="00:00:07,500",
            end_ts="00:00:11,000",
            text="The crack appears to be about 5 millimeters wide.",
            words=None,
            avg_logprob=-0.22,
            no_speech_prob=0.01,
        ),
        Segment(
            id=3,
            start_s=12.0,
            end_s=16.0,
            start_ts="00:00:12,000",
            end_ts="00:00:16,000",
            text="There's also some corrosion on the steel beam.",
            words=None,
            avg_logprob=-0.28,
            no_speech_prob=0.03,
        ),
        Segment(
            id=4,
            start_s=17.0,
            end_s=21.0,
            start_ts="00:00:17,000",
            end_ts="00:00:21,000",
            text="I recommend this area be scheduled for repair.",
            words=None,
            avg_logprob=-0.20,
            no_speech_prob=0.01,
        ),
        Segment(
            id=5,
            start_s=22.0,
            end_s=25.0,
            start_ts="00:00:22,000",
            end_ts="00:00:25,000",
            text="Moving to the east section now.",
            words=None,
            avg_logprob=-0.18,
            no_speech_prob=0.01,
        ),
    )

    metadata = TranscriptMetadata(
        engine=TranscriptionEngineType.FASTER_WHISPER,
        model_name="base",
        language="en",
        detected_language="en",
        language_probability=0.98,
        duration_s=25.0,
        source_video=Path("/path/to/inspection.mp4"),
        source_audio=Path("/path/to/inspection.wav"),
    )

    return Transcript(
        full_text=" ".join(s.text for s in segments),
        segments=segments,
        metadata=metadata,
    )
