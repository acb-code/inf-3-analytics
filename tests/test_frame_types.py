"""Tests for frame type serialization roundtrips."""

from pathlib import Path

import pytest

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
def sample_frame_no_dims() -> Frame:
    """Create a sample Frame without dimensions for testing."""
    return Frame(
        frame_id="001",
        path=Path("frames/001_00-07-16.700.jpg"),
        timestamp_s=436.7,
        timestamp_ts="00:07:16,700",
        width=None,
        height=None,
        file_size_bytes=None,
    )


@pytest.fixture
def sample_event_frame_set(sample_frame: Frame, sample_frame_no_dims: Frame) -> EventFrameSet:
    """Create a sample EventFrameSet for testing."""
    return EventFrameSet(
        event_id="evt_000",
        event_title="Structural anomaly detected",
        start_s=434.0,
        end_s=440.0,
        start_ts="00:07:14,000",
        end_ts="00:07:20,000",
        frames=(sample_frame, sample_frame_no_dims),
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
        total_frames=2,
        total_events=1,
        successful_events=1,
        skipped_events=0,
        failed_events=0,
    )


class TestFrameRoundtrip:
    """Tests for Frame serialization."""

    def test_to_dict(self, sample_frame: Frame) -> None:
        """Test Frame to_dict conversion."""
        d = sample_frame.to_dict()
        assert d["frame_id"] == "000"
        assert d["path"] == "frames/000_00-07-14.200.jpg"
        assert d["timestamp_s"] == 434.2
        assert d["timestamp_ts"] == "00:07:14,200"
        assert d["width"] == 1920
        assert d["height"] == 1080
        assert d["file_size_bytes"] == 123456

    def test_from_dict(self, sample_frame: Frame) -> None:
        """Test Frame from_dict conversion."""
        d = sample_frame.to_dict()
        restored = Frame.from_dict(d)
        assert restored.frame_id == sample_frame.frame_id
        assert restored.path == sample_frame.path
        assert restored.timestamp_s == sample_frame.timestamp_s
        assert restored.timestamp_ts == sample_frame.timestamp_ts
        assert restored.width == sample_frame.width
        assert restored.height == sample_frame.height
        assert restored.file_size_bytes == sample_frame.file_size_bytes

    def test_roundtrip_with_none_values(self, sample_frame_no_dims: Frame) -> None:
        """Test Frame roundtrip with None values."""
        d = sample_frame_no_dims.to_dict()
        restored = Frame.from_dict(d)
        assert restored.width is None
        assert restored.height is None
        assert restored.file_size_bytes is None


class TestEventFrameSetRoundtrip:
    """Tests for EventFrameSet serialization."""

    def test_to_dict(self, sample_event_frame_set: EventFrameSet) -> None:
        """Test EventFrameSet to_dict conversion."""
        d = sample_event_frame_set.to_dict()
        assert d["event_id"] == "evt_000"
        assert d["event_title"] == "Structural anomaly detected"
        assert d["start_s"] == 434.0
        assert d["end_s"] == 440.0
        assert d["status"] == "success"
        assert d["error_message"] is None
        assert len(d["frames"]) == 2

    def test_from_dict(self, sample_event_frame_set: EventFrameSet) -> None:
        """Test EventFrameSet from_dict conversion."""
        d = sample_event_frame_set.to_dict()
        restored = EventFrameSet.from_dict(d)
        assert restored.event_id == sample_event_frame_set.event_id
        assert restored.event_title == sample_event_frame_set.event_title
        assert restored.start_s == sample_event_frame_set.start_s
        assert restored.end_s == sample_event_frame_set.end_s
        assert restored.status == sample_event_frame_set.status
        assert len(restored.frames) == len(sample_event_frame_set.frames)

    def test_roundtrip_with_error(self) -> None:
        """Test EventFrameSet roundtrip with error message."""
        efs = EventFrameSet(
            event_id="evt_001",
            event_title="Failed event",
            start_s=100.0,
            end_s=110.0,
            start_ts="00:01:40,000",
            end_ts="00:01:50,000",
            frames=(),
            status=FrameExtractionStatus.FAILED,
            error_message="All frame extractions failed",
        )
        d = efs.to_dict()
        restored = EventFrameSet.from_dict(d)
        assert restored.status == FrameExtractionStatus.FAILED
        assert restored.error_message == "All frame extractions failed"
        assert restored.frames == ()


class TestFrameExtractionMetadataRoundtrip:
    """Tests for FrameExtractionMetadata serialization."""

    def test_to_dict(self, sample_metadata: FrameExtractionMetadata) -> None:
        """Test FrameExtractionMetadata to_dict conversion."""
        d = sample_metadata.to_dict()
        assert d["policy_name"] == "nframes"
        assert d["policy_params"] == {"n": 5}
        assert d["video_path"] == "/path/to/video.mp4"
        assert d["video_duration_s"] == 600.0
        assert d["video_fps"] == 30.0
        assert d["jpeg_quality"] == 2

    def test_from_dict(self, sample_metadata: FrameExtractionMetadata) -> None:
        """Test FrameExtractionMetadata from_dict conversion."""
        d = sample_metadata.to_dict()
        restored = FrameExtractionMetadata.from_dict(d)
        assert restored.policy_name == sample_metadata.policy_name
        assert restored.policy_params == sample_metadata.policy_params
        assert restored.video_path == sample_metadata.video_path
        assert restored.video_duration_s == sample_metadata.video_duration_s

    def test_roundtrip_with_none_values(self) -> None:
        """Test FrameExtractionMetadata roundtrip with None values."""
        metadata = FrameExtractionMetadata(
            policy_name="fps",
            policy_params={"fps": 1.0, "max_frames": 30},
            video_path="/path/to/video.mp4",
            video_duration_s=100.0,
            video_fps=None,
            video_width=None,
            video_height=None,
            events_path="/path/to/events.json",
            extraction_timestamp="2024-01-15T10:30:00",
            jpeg_quality=2,
        )
        d = metadata.to_dict()
        restored = FrameExtractionMetadata.from_dict(d)
        assert restored.video_fps is None
        assert restored.video_width is None
        assert restored.video_height is None


class TestFrameManifestRoundtrip:
    """Tests for FrameManifest serialization."""

    def test_to_dict(self, sample_manifest: FrameManifest) -> None:
        """Test FrameManifest to_dict conversion."""
        d = sample_manifest.to_dict()
        assert len(d["event_frame_sets"]) == 1
        assert d["total_frames"] == 2
        assert d["total_events"] == 1
        assert d["successful_events"] == 1
        assert d["skipped_events"] == 0
        assert d["failed_events"] == 0
        assert "metadata" in d

    def test_from_dict(self, sample_manifest: FrameManifest) -> None:
        """Test FrameManifest from_dict conversion."""
        d = sample_manifest.to_dict()
        restored = FrameManifest.from_dict(d)
        assert restored.total_frames == sample_manifest.total_frames
        assert restored.total_events == sample_manifest.total_events
        assert restored.successful_events == sample_manifest.successful_events
        assert len(restored.event_frame_sets) == len(sample_manifest.event_frame_sets)
        assert restored.metadata.policy_name == sample_manifest.metadata.policy_name

    def test_roundtrip_empty_manifest(self, sample_metadata: FrameExtractionMetadata) -> None:
        """Test FrameManifest roundtrip with no events."""
        manifest = FrameManifest(
            event_frame_sets=(),
            metadata=sample_metadata,
            total_frames=0,
            total_events=0,
            successful_events=0,
            skipped_events=0,
            failed_events=0,
        )
        d = manifest.to_dict()
        restored = FrameManifest.from_dict(d)
        assert restored.event_frame_sets == ()
        assert restored.total_frames == 0
