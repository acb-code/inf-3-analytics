"""Tests for frame manifest IO roundtrips."""

from pathlib import Path

import pytest

from inf3_analytics.io.frame_manifest_writer import (
    read_event_frames_json,
    read_manifest,
    write_event_frames_json,
    write_manifest,
)
from inf3_analytics.types.frame import (
    EventFrameSet,
    Frame,
    FrameExtractionMetadata,
    FrameExtractionStatus,
    FrameManifest,
)


@pytest.fixture
def sample_frame() -> Frame:
    """Create a sample Frame for testing."""
    return Frame(
        frame_id="000",
        path=Path("frames/000_00-07-14.200.jpg"),
        timestamp_s=434.2,
        timestamp_ts="00:07:14,200",
        width=1920,
        height=1080,
        file_size_bytes=123456,
    )


@pytest.fixture
def sample_event_frame_set(sample_frame: Frame) -> EventFrameSet:
    """Create a sample EventFrameSet for testing."""
    return EventFrameSet(
        event_id="evt_000",
        event_title="Structural anomaly detected",
        start_s=434.0,
        end_s=440.0,
        start_ts="00:07:14,000",
        end_ts="00:07:20,000",
        frames=(sample_frame,),
        status=FrameExtractionStatus.SUCCESS,
        error_message=None,
    )


@pytest.fixture
def sample_metadata() -> FrameExtractionMetadata:
    """Create sample FrameExtractionMetadata for testing."""
    return FrameExtractionMetadata(
        policy_name="nframes",
        policy_params={"n": 5},
        video_path="/path/to/video.mp4",
        video_duration_s=600.0,
        video_fps=30.0,
        video_width=1920,
        video_height=1080,
        events_path="/path/to/events.json",
        extraction_timestamp="2024-01-15T10:30:00",
        jpeg_quality=2,
    )


@pytest.fixture
def sample_manifest(
    sample_event_frame_set: EventFrameSet, sample_metadata: FrameExtractionMetadata
) -> FrameManifest:
    """Create a sample FrameManifest for testing."""
    return FrameManifest(
        event_frame_sets=(sample_event_frame_set,),
        metadata=sample_metadata,
        total_frames=1,
        total_events=1,
        successful_events=1,
        skipped_events=0,
        failed_events=0,
    )


class TestManifestIO:
    """Tests for manifest JSON IO."""

    def test_write_and_read_manifest(
        self, sample_manifest: FrameManifest, tmp_path: Path
    ) -> None:
        """Test that manifest survives JSON roundtrip."""
        manifest_path = tmp_path / "manifest.json"

        write_manifest(sample_manifest, manifest_path)
        loaded = read_manifest(manifest_path)

        assert loaded.total_frames == sample_manifest.total_frames
        assert loaded.total_events == sample_manifest.total_events
        assert loaded.successful_events == sample_manifest.successful_events
        assert loaded.skipped_events == sample_manifest.skipped_events
        assert loaded.failed_events == sample_manifest.failed_events
        assert len(loaded.event_frame_sets) == len(sample_manifest.event_frame_sets)

    def test_manifest_metadata_preserved(
        self, sample_manifest: FrameManifest, tmp_path: Path
    ) -> None:
        """Test that metadata is preserved through roundtrip."""
        manifest_path = tmp_path / "manifest.json"

        write_manifest(sample_manifest, manifest_path)
        loaded = read_manifest(manifest_path)

        assert loaded.metadata.policy_name == sample_manifest.metadata.policy_name
        assert loaded.metadata.policy_params == sample_manifest.metadata.policy_params
        assert loaded.metadata.video_path == sample_manifest.metadata.video_path
        assert loaded.metadata.video_duration_s == sample_manifest.metadata.video_duration_s
        assert loaded.metadata.jpeg_quality == sample_manifest.metadata.jpeg_quality

    def test_manifest_event_frame_sets_preserved(
        self, sample_manifest: FrameManifest, tmp_path: Path
    ) -> None:
        """Test that event frame sets are preserved through roundtrip."""
        manifest_path = tmp_path / "manifest.json"

        write_manifest(sample_manifest, manifest_path)
        loaded = read_manifest(manifest_path)

        for orig, loaded_efs in zip(
            sample_manifest.event_frame_sets, loaded.event_frame_sets, strict=True
        ):
            assert loaded_efs.event_id == orig.event_id
            assert loaded_efs.event_title == orig.event_title
            assert loaded_efs.start_s == orig.start_s
            assert loaded_efs.end_s == orig.end_s
            assert loaded_efs.status == orig.status
            assert len(loaded_efs.frames) == len(orig.frames)

    def test_creates_parent_directory(
        self, sample_manifest: FrameManifest, tmp_path: Path
    ) -> None:
        """Test that write_manifest creates parent directories."""
        nested_path = tmp_path / "nested" / "dirs" / "manifest.json"

        write_manifest(sample_manifest, nested_path)

        assert nested_path.exists()

    def test_empty_manifest(self, sample_metadata: FrameExtractionMetadata, tmp_path: Path) -> None:
        """Test roundtrip with empty manifest."""
        manifest = FrameManifest(
            event_frame_sets=(),
            metadata=sample_metadata,
            total_frames=0,
            total_events=0,
            successful_events=0,
            skipped_events=0,
            failed_events=0,
        )

        manifest_path = tmp_path / "empty_manifest.json"
        write_manifest(manifest, manifest_path)
        loaded = read_manifest(manifest_path)

        assert loaded.event_frame_sets == ()
        assert loaded.total_frames == 0


class TestEventFramesJsonIO:
    """Tests for per-event frames.json IO."""

    def test_write_and_read_event_frames(
        self, sample_event_frame_set: EventFrameSet, tmp_path: Path
    ) -> None:
        """Test that event frame set survives JSON roundtrip."""
        json_path = tmp_path / "frames.json"

        write_event_frames_json(sample_event_frame_set, json_path)
        loaded = read_event_frames_json(json_path)

        assert loaded.event_id == sample_event_frame_set.event_id
        assert loaded.event_title == sample_event_frame_set.event_title
        assert loaded.start_s == sample_event_frame_set.start_s
        assert loaded.end_s == sample_event_frame_set.end_s
        assert loaded.status == sample_event_frame_set.status

    def test_frames_preserved(
        self, sample_event_frame_set: EventFrameSet, tmp_path: Path
    ) -> None:
        """Test that frames are preserved through roundtrip."""
        json_path = tmp_path / "frames.json"

        write_event_frames_json(sample_event_frame_set, json_path)
        loaded = read_event_frames_json(json_path)

        for orig, loaded_frame in zip(
            sample_event_frame_set.frames, loaded.frames, strict=True
        ):
            assert loaded_frame.frame_id == orig.frame_id
            assert loaded_frame.path == orig.path
            assert loaded_frame.timestamp_s == orig.timestamp_s
            assert loaded_frame.timestamp_ts == orig.timestamp_ts
            assert loaded_frame.width == orig.width
            assert loaded_frame.height == orig.height
            assert loaded_frame.file_size_bytes == orig.file_size_bytes

    def test_creates_parent_directory(
        self, sample_event_frame_set: EventFrameSet, tmp_path: Path
    ) -> None:
        """Test that write_event_frames_json creates parent directories."""
        nested_path = tmp_path / "event" / "frames.json"

        write_event_frames_json(sample_event_frame_set, nested_path)

        assert nested_path.exists()

    def test_failed_event_roundtrip(self, tmp_path: Path) -> None:
        """Test roundtrip of failed event with error message."""
        event_frame_set = EventFrameSet(
            event_id="evt_001",
            event_title="Failed extraction",
            start_s=100.0,
            end_s=110.0,
            start_ts="00:01:40,000",
            end_ts="00:01:50,000",
            frames=(),
            status=FrameExtractionStatus.FAILED,
            error_message="All frame extractions failed",
        )

        json_path = tmp_path / "failed_frames.json"
        write_event_frames_json(event_frame_set, json_path)
        loaded = read_event_frames_json(json_path)

        assert loaded.status == FrameExtractionStatus.FAILED
        assert loaded.error_message == "All frame extractions failed"
        assert loaded.frames == ()

    def test_partial_event_roundtrip(self, sample_frame: Frame, tmp_path: Path) -> None:
        """Test roundtrip of partial extraction."""
        event_frame_set = EventFrameSet(
            event_id="evt_002",
            event_title="Partial extraction",
            start_s=200.0,
            end_s=210.0,
            start_ts="00:03:20,000",
            end_ts="00:03:30,000",
            frames=(sample_frame,),
            status=FrameExtractionStatus.PARTIAL,
            error_message="2 of 5 frames failed",
        )

        json_path = tmp_path / "partial_frames.json"
        write_event_frames_json(event_frame_set, json_path)
        loaded = read_event_frames_json(json_path)

        assert loaded.status == FrameExtractionStatus.PARTIAL
        assert loaded.error_message == "2 of 5 frames failed"
        assert len(loaded.frames) == 1
