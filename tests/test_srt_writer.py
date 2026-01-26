"""Tests for SRT writer functionality."""

from pathlib import Path

from inf3_analytics.io.transcript_writer import write_srt
from inf3_analytics.types.transcript import Transcript


class TestWriteSrt:
    """Tests for write_srt function."""

    def test_srt_structure(
        self, sample_transcript: Transcript, tmp_output_dir: Path
    ) -> None:
        """Test that SRT file has correct structure."""
        srt_path = tmp_output_dir / "test.srt"
        write_srt(sample_transcript, srt_path)

        content = srt_path.read_text()
        lines = content.split("\n")

        # First segment
        assert lines[0] == "1"  # 1-based index
        assert lines[1] == "00:00:00,000 --> 00:00:02,500"  # Timestamp line
        assert lines[2] == "Hello, this is a test segment."  # Text
        assert lines[3] == ""  # Blank line

        # Second segment
        assert lines[4] == "2"
        assert lines[5] == "00:00:03,000 --> 00:00:05,500"
        assert lines[6] == "This segment has no word-level timestamps."
        assert lines[7] == ""

    def test_creates_parent_directory(self, sample_transcript: Transcript, tmp_path: Path) -> None:
        """Test that parent directories are created if they don't exist."""
        srt_path = tmp_path / "nested" / "dirs" / "test.srt"
        assert not srt_path.parent.exists()

        write_srt(sample_transcript, srt_path)

        assert srt_path.exists()
        assert srt_path.parent.exists()

    def test_timestamp_format(
        self, sample_transcript: Transcript, tmp_output_dir: Path
    ) -> None:
        """Test that timestamps use SRT format (comma separator)."""
        srt_path = tmp_output_dir / "test.srt"
        write_srt(sample_transcript, srt_path)

        content = srt_path.read_text()

        # SRT uses comma as decimal separator, not period
        assert "00:00:00,000" in content
        assert "00:00:02,500" in content
        assert "00:00:00.000" not in content  # Not period

    def test_one_based_indexing(
        self, sample_transcript: Transcript, tmp_output_dir: Path
    ) -> None:
        """Test that segment indices start at 1, not 0."""
        srt_path = tmp_output_dir / "test.srt"
        write_srt(sample_transcript, srt_path)

        content = srt_path.read_text()
        lines = content.split("\n")

        # First index should be 1
        assert lines[0] == "1"
        # Second index should be 2
        assert lines[4] == "2"

    def test_utf8_encoding(self, tmp_output_dir: Path, sample_metadata: "TranscriptMetadata") -> None:
        """Test that SRT files are written with UTF-8 encoding."""
        from inf3_analytics.types.transcript import Segment, Transcript, TranscriptMetadata

        # Create transcript with non-ASCII characters
        segment = Segment(
            id=0,
            start_s=0.0,
            end_s=1.0,
            start_ts="00:00:00,000",
            end_ts="00:00:01,000",
            text="Caf\u00e9 \u4f60\u597d",  # UTF-8 chars (accent and Chinese)
            words=None,
            avg_logprob=-0.2,
            no_speech_prob=0.01,
        )

        transcript = Transcript(
            full_text=segment.text,
            segments=(segment,),
            metadata=sample_metadata,
        )

        srt_path = tmp_output_dir / "utf8.srt"
        write_srt(transcript, srt_path)

        content = srt_path.read_text(encoding="utf-8")
        assert "Caf\u00e9" in content
        assert "\u4f60\u597d" in content


# Import for type annotation
from inf3_analytics.types.transcript import TranscriptMetadata  # noqa: E402
