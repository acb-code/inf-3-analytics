"""Tests for transcript JSON serialization roundtrip."""

from pathlib import Path

from inf3_analytics.io.transcript_writer import read_json, write_json
from inf3_analytics.types.transcript import (
    Segment,
    Transcript,
    TranscriptMetadata,
    TranscriptionEngineType,
    Word,
)


class TestJsonRoundtrip:
    """Tests for JSON serialization and deserialization."""

    def test_full_roundtrip(self, sample_transcript: Transcript, tmp_output_dir: Path) -> None:
        """Test that full transcript survives JSON roundtrip."""
        json_path = tmp_output_dir / "test.json"

        write_json(sample_transcript, json_path)
        loaded = read_json(json_path)

        assert loaded.full_text == sample_transcript.full_text
        assert len(loaded.segments) == len(sample_transcript.segments)

    def test_segments_preserved(self, sample_transcript: Transcript, tmp_output_dir: Path) -> None:
        """Test that segment data is preserved through roundtrip."""
        json_path = tmp_output_dir / "test.json"

        write_json(sample_transcript, json_path)
        loaded = read_json(json_path)

        for orig, loaded_seg in zip(sample_transcript.segments, loaded.segments, strict=True):
            assert loaded_seg.id == orig.id
            assert loaded_seg.start_s == orig.start_s
            assert loaded_seg.end_s == orig.end_s
            assert loaded_seg.start_ts == orig.start_ts
            assert loaded_seg.end_ts == orig.end_ts
            assert loaded_seg.text == orig.text
            assert loaded_seg.avg_logprob == orig.avg_logprob
            assert loaded_seg.no_speech_prob == orig.no_speech_prob

    def test_metadata_preserved(self, sample_transcript: Transcript, tmp_output_dir: Path) -> None:
        """Test that metadata is preserved through roundtrip."""
        json_path = tmp_output_dir / "test.json"

        write_json(sample_transcript, json_path)
        loaded = read_json(json_path)

        orig_meta = sample_transcript.metadata
        loaded_meta = loaded.metadata

        assert loaded_meta.engine == orig_meta.engine
        assert loaded_meta.model_name == orig_meta.model_name
        assert loaded_meta.language == orig_meta.language
        assert loaded_meta.detected_language == orig_meta.detected_language
        assert loaded_meta.language_probability == orig_meta.language_probability
        assert loaded_meta.duration_s == orig_meta.duration_s
        # Paths are converted to strings and back
        assert str(loaded_meta.source_video) == str(orig_meta.source_video)
        assert str(loaded_meta.source_audio) == str(orig_meta.source_audio)

    def test_words_preserved(self, sample_transcript: Transcript, tmp_output_dir: Path) -> None:
        """Test that word-level data is preserved through roundtrip."""
        json_path = tmp_output_dir / "test.json"

        write_json(sample_transcript, json_path)
        loaded = read_json(json_path)

        # First segment has words
        orig_words = sample_transcript.segments[0].words
        loaded_words = loaded.segments[0].words

        assert orig_words is not None
        assert loaded_words is not None
        assert len(loaded_words) == len(orig_words)

        for orig_word, loaded_word in zip(orig_words, loaded_words, strict=True):
            assert loaded_word.word == orig_word.word
            assert loaded_word.start_s == orig_word.start_s
            assert loaded_word.end_s == orig_word.end_s
            assert loaded_word.probability == orig_word.probability

    def test_none_words_preserved(
        self, sample_transcript: Transcript, tmp_output_dir: Path
    ) -> None:
        """Test that segments without words preserve None through roundtrip."""
        json_path = tmp_output_dir / "test.json"

        write_json(sample_transcript, json_path)
        loaded = read_json(json_path)

        # Second segment has no words
        assert sample_transcript.segments[1].words is None
        assert loaded.segments[1].words is None

    def test_creates_parent_directory(self, sample_transcript: Transcript, tmp_path: Path) -> None:
        """Test that parent directories are created for JSON output."""
        json_path = tmp_path / "nested" / "dirs" / "test.json"
        assert not json_path.parent.exists()

        write_json(sample_transcript, json_path)

        assert json_path.exists()

    def test_none_optional_fields(self, tmp_output_dir: Path) -> None:
        """Test roundtrip with None optional fields in metadata."""
        metadata = TranscriptMetadata(
            engine=TranscriptionEngineType.FASTER_WHISPER,
            model_name="base",
            language=None,
            detected_language=None,
            language_probability=None,
            duration_s=10.0,
            source_video=None,
            source_audio=None,
        )

        segment = Segment(
            id=0,
            start_s=0.0,
            end_s=1.0,
            start_ts="00:00:00,000",
            end_ts="00:00:01,000",
            text="Test",
            words=None,
            avg_logprob=-0.2,
            no_speech_prob=0.01,
        )

        transcript = Transcript(
            full_text="Test",
            segments=(segment,),
            metadata=metadata,
        )

        json_path = tmp_output_dir / "test_none.json"
        write_json(transcript, json_path)
        loaded = read_json(json_path)

        assert loaded.metadata.language is None
        assert loaded.metadata.detected_language is None
        assert loaded.metadata.language_probability is None
        assert loaded.metadata.source_video is None
        assert loaded.metadata.source_audio is None
