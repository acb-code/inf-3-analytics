"""Shared test fixtures."""

from pathlib import Path

import pytest

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
