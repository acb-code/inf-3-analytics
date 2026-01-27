"""Tests for event JSON serialization and output formats."""

from pathlib import Path

import pytest

from inf3_analytics.io.event_writer import (
    read_json,
    write_json,
    write_markdown,
    write_ndjson,
)
from inf3_analytics.types.event import Event, EventList


class TestEventJsonRoundtrip:
    """Tests for JSON serialization roundtrip."""

    def test_full_roundtrip(
        self, sample_event_list: EventList, tmp_output_dir: Path
    ) -> None:
        """Test that full event list survives JSON roundtrip."""
        json_path = tmp_output_dir / "test_events.json"

        write_json(sample_event_list, json_path)
        loaded = read_json(json_path)

        assert len(loaded.events) == len(sample_event_list.events)
        assert loaded.source_transcript_path == sample_event_list.source_transcript_path
        assert loaded.extraction_engine == sample_event_list.extraction_engine
        assert loaded.extraction_timestamp == sample_event_list.extraction_timestamp

    def test_events_preserved(
        self, sample_event_list: EventList, tmp_output_dir: Path
    ) -> None:
        """Test that event data is preserved through roundtrip."""
        json_path = tmp_output_dir / "test_events.json"

        write_json(sample_event_list, json_path)
        loaded = read_json(json_path)

        for orig, loaded_event in zip(
            sample_event_list.events, loaded.events, strict=True
        ):
            assert loaded_event.event_id == orig.event_id
            assert loaded_event.event_type == orig.event_type
            assert loaded_event.severity == orig.severity
            assert loaded_event.confidence == orig.confidence
            assert loaded_event.start_s == orig.start_s
            assert loaded_event.end_s == orig.end_s
            assert loaded_event.start_ts == orig.start_ts
            assert loaded_event.end_ts == orig.end_ts
            assert loaded_event.title == orig.title
            assert loaded_event.summary == orig.summary

    def test_transcript_reference_preserved(
        self, sample_event_list: EventList, tmp_output_dir: Path
    ) -> None:
        """Test that transcript references are preserved."""
        json_path = tmp_output_dir / "test_events.json"

        write_json(sample_event_list, json_path)
        loaded = read_json(json_path)

        for orig, loaded_event in zip(
            sample_event_list.events, loaded.events, strict=True
        ):
            assert loaded_event.transcript_ref.segment_ids == orig.transcript_ref.segment_ids
            assert loaded_event.transcript_ref.excerpt == orig.transcript_ref.excerpt
            assert loaded_event.transcript_ref.keywords == orig.transcript_ref.keywords

    def test_metadata_preserved(
        self, sample_event_list: EventList, tmp_output_dir: Path
    ) -> None:
        """Test that event metadata is preserved."""
        json_path = tmp_output_dir / "test_events.json"

        write_json(sample_event_list, json_path)
        loaded = read_json(json_path)

        for orig, loaded_event in zip(
            sample_event_list.events, loaded.events, strict=True
        ):
            assert (
                loaded_event.metadata.extractor_engine
                == orig.metadata.extractor_engine
            )
            assert (
                loaded_event.metadata.extractor_version
                == orig.metadata.extractor_version
            )
            assert loaded_event.metadata.created_at == orig.metadata.created_at

    def test_empty_event_list(self, tmp_output_dir: Path) -> None:
        """Test roundtrip with empty event list."""
        event_list = EventList(
            events=(),
            source_transcript_path=None,
            extraction_engine="rules",
            extraction_timestamp="2024-01-01T00:00:00",
        )

        json_path = tmp_output_dir / "empty_events.json"
        write_json(event_list, json_path)
        loaded = read_json(json_path)

        assert len(loaded.events) == 0
        assert loaded.source_transcript_path is None

    def test_creates_parent_directory(self, tmp_output_dir: Path) -> None:
        """Test that write_json creates parent directories."""
        event_list = EventList(
            events=(),
            source_transcript_path=None,
            extraction_engine="rules",
            extraction_timestamp="2024-01-01T00:00:00",
        )

        nested_path = tmp_output_dir / "nested" / "dirs" / "events.json"
        write_json(event_list, nested_path)

        assert nested_path.exists()


class TestEventMarkdownWriter:
    """Tests for Markdown output format."""

    def test_write_markdown_creates_file(
        self, sample_event_list: EventList, tmp_output_dir: Path
    ) -> None:
        """Test that write_markdown creates a file."""
        md_path = tmp_output_dir / "events.md"

        write_markdown(sample_event_list, md_path)

        assert md_path.exists()

    def test_markdown_contains_header(
        self, sample_event_list: EventList, tmp_output_dir: Path
    ) -> None:
        """Test that Markdown has proper header."""
        md_path = tmp_output_dir / "events.md"

        write_markdown(sample_event_list, md_path)
        content = md_path.read_text()

        assert "# Event Extraction Summary" in content

    def test_markdown_contains_metadata(
        self, sample_event_list: EventList, tmp_output_dir: Path
    ) -> None:
        """Test that Markdown contains metadata."""
        md_path = tmp_output_dir / "events.md"

        write_markdown(sample_event_list, md_path)
        content = md_path.read_text()

        assert "**Source:**" in content
        assert "**Engine:**" in content
        assert "**Total Events:**" in content
        assert "rules" in content

    def test_markdown_contains_events(
        self, sample_event_list: EventList, tmp_output_dir: Path
    ) -> None:
        """Test that Markdown contains event details."""
        md_path = tmp_output_dir / "events.md"

        write_markdown(sample_event_list, md_path)
        content = md_path.read_text()

        # Should contain event titles
        for event in sample_event_list.events:
            assert event.title in content

    def test_markdown_contains_severity_badge(
        self, sample_event: Event, tmp_output_dir: Path
    ) -> None:
        """Test that Markdown shows severity badge for events with severity."""
        event_list = EventList(
            events=(sample_event,),
            source_transcript_path=None,
            extraction_engine="rules",
            extraction_timestamp="2024-01-01T00:00:00",
        )

        md_path = tmp_output_dir / "events.md"
        write_markdown(event_list, md_path)
        content = md_path.read_text()

        assert "[MEDIUM]" in content

    def test_markdown_contains_timestamps(
        self, sample_event_list: EventList, tmp_output_dir: Path
    ) -> None:
        """Test that Markdown contains timestamps."""
        md_path = tmp_output_dir / "events.md"

        write_markdown(sample_event_list, md_path)
        content = md_path.read_text()

        assert "**Time:**" in content

    def test_markdown_contains_suggested_actions(
        self, sample_event: Event, tmp_output_dir: Path
    ) -> None:
        """Test that Markdown shows suggested actions."""
        event_list = EventList(
            events=(sample_event,),
            source_transcript_path=None,
            extraction_engine="rules",
            extraction_timestamp="2024-01-01T00:00:00",
        )

        md_path = tmp_output_dir / "events.md"
        write_markdown(event_list, md_path)
        content = md_path.read_text()

        assert "**Suggested Actions:**" in content
        assert "Schedule detailed inspection" in content

    def test_markdown_empty_events(self, tmp_output_dir: Path) -> None:
        """Test Markdown output with no events."""
        event_list = EventList(
            events=(),
            source_transcript_path=None,
            extraction_engine="rules",
            extraction_timestamp="2024-01-01T00:00:00",
        )

        md_path = tmp_output_dir / "empty_events.md"
        write_markdown(event_list, md_path)
        content = md_path.read_text()

        assert "Total Events:** 0" in content
        assert "No events detected" in content


class TestEventNdjsonWriter:
    """Tests for NDJSON output format."""

    def test_write_ndjson_creates_file(
        self, sample_event_list: EventList, tmp_output_dir: Path
    ) -> None:
        """Test that write_ndjson creates a file."""
        ndjson_path = tmp_output_dir / "events.ndjson"

        write_ndjson(sample_event_list, ndjson_path)

        assert ndjson_path.exists()

    def test_ndjson_one_line_per_event(
        self, sample_event_list: EventList, tmp_output_dir: Path
    ) -> None:
        """Test that NDJSON has one line per event."""
        ndjson_path = tmp_output_dir / "events.ndjson"

        write_ndjson(sample_event_list, ndjson_path)

        lines = ndjson_path.read_text().strip().split("\n")
        assert len(lines) == len(sample_event_list.events)

    def test_ndjson_valid_json_lines(
        self, sample_event_list: EventList, tmp_output_dir: Path
    ) -> None:
        """Test that each NDJSON line is valid JSON."""
        import json

        ndjson_path = tmp_output_dir / "events.ndjson"

        write_ndjson(sample_event_list, ndjson_path)

        lines = ndjson_path.read_text().strip().split("\n")
        for line in lines:
            data = json.loads(line)  # Should not raise
            assert "event_id" in data
            assert "event_type" in data

    def test_ndjson_empty_events(self, tmp_output_dir: Path) -> None:
        """Test NDJSON output with no events."""
        event_list = EventList(
            events=(),
            source_transcript_path=None,
            extraction_engine="rules",
            extraction_timestamp="2024-01-01T00:00:00",
        )

        ndjson_path = tmp_output_dir / "empty_events.ndjson"
        write_ndjson(event_list, ndjson_path)

        content = ndjson_path.read_text()
        assert content == ""
