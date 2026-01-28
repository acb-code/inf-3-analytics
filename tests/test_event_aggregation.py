"""Tests for event-level analytics aggregation."""

import pytest

from inf3_analytics.frame_analytics.aggregate import (
    aggregate_event_results,
    select_representative_frame,
)
from inf3_analytics.types.detection import (
    Detection,
    DetectionAttributes,
    DetectionType,
    EngineInfo,
    FrameAnalyticsResult,
    QAPair,
    Severity,
)


@pytest.fixture
def sample_engine_info() -> EngineInfo:
    """Create sample engine info for tests."""
    return EngineInfo(
        name="vlm",
        provider="openai",
        model="gpt-5-mini",
        prompt_version="v1",
        version="0.1.0",
        config={},
    )


def make_detection(
    dtype: DetectionType = DetectionType.CRACK,
    label: str = "Test detection",
    confidence: float = 0.8,
    severity: Severity | None = Severity.MEDIUM,
) -> Detection:
    """Helper to create a detection."""
    return Detection(
        detection_type=dtype,
        label=label,
        confidence=confidence,
        bbox=None,
        attributes=DetectionAttributes(
            severity=severity,
            materials=None,
            location_hint=None,
            notes=None,
        ),
    )


def make_result(
    frame_idx: int,
    timestamp_s: float,
    detections: tuple[Detection, ...] = (),
    error: str | None = None,
    engine_info: EngineInfo | None = None,
) -> FrameAnalyticsResult:
    """Helper to create a frame result."""
    if engine_info is None:
        engine_info = EngineInfo(
            name="vlm",
            provider="openai",
            model="gpt-5-mini",
            prompt_version="v1",
            version="0.1.0",
            config={},
        )

    return FrameAnalyticsResult(
        event_id="evt_001",
        frame_idx=frame_idx,
        timestamp_s=timestamp_s,
        timestamp_ts=f"00:00:{int(timestamp_s):02d},000",
        image_path=f"frames/{frame_idx:03d}.jpg",
        engine=engine_info,
        detections=detections,
        scene_summary="Test scene",
        qa=(QAPair(question="Test?", answer="Yes"),),
        raw_model_output=None,
        error=error,
    )


class TestAggregateEventResults:
    """Tests for aggregate_event_results function."""

    def test_empty_results(self, sample_engine_info: EngineInfo) -> None:
        """Test aggregation with no results."""
        summary = aggregate_event_results(
            results=[],
            event_id="evt_001",
            engine_info=sample_engine_info,
            source_manifest="/path/manifest.json",
        )

        assert summary.event_id == "evt_001"
        assert summary.frame_count == 0
        assert summary.analyzed_count == 0
        assert summary.failed_count == 0
        assert len(summary.top_findings) == 0
        assert summary.representative_frame is None

    def test_single_result_no_detections(self, sample_engine_info: EngineInfo) -> None:
        """Test aggregation with single result, no detections."""
        results = [make_result(0, 10.0)]

        summary = aggregate_event_results(
            results=results,
            event_id="evt_001",
            engine_info=sample_engine_info,
            source_manifest="/path/manifest.json",
        )

        assert summary.frame_count == 1
        assert summary.analyzed_count == 1
        assert summary.failed_count == 0
        assert len(summary.top_findings) == 0

    def test_single_result_with_detections(self, sample_engine_info: EngineInfo) -> None:
        """Test aggregation with single result containing detections."""
        detection = make_detection(
            dtype=DetectionType.CRACK,
            label="Crack in concrete",
            confidence=0.9,
            severity=Severity.HIGH,
        )
        results = [make_result(0, 10.0, detections=(detection,))]

        summary = aggregate_event_results(
            results=results,
            event_id="evt_001",
            engine_info=sample_engine_info,
            source_manifest="/path/manifest.json",
        )

        assert summary.frame_count == 1
        assert len(summary.top_findings) == 1
        assert summary.top_findings[0].detection_type == DetectionType.CRACK
        assert summary.top_findings[0].max_confidence == 0.9
        assert summary.top_findings[0].frame_count == 1
        assert summary.top_findings[0].severity == Severity.HIGH

    def test_multiple_results_same_type(self, sample_engine_info: EngineInfo) -> None:
        """Test aggregation aggregates same detection type across frames."""
        results = [
            make_result(0, 10.0, detections=(
                make_detection(DetectionType.CRACK, "Crack 1", 0.8),
            )),
            make_result(1, 11.0, detections=(
                make_detection(DetectionType.CRACK, "Crack 2", 0.9),
            )),
            make_result(2, 12.0, detections=(
                make_detection(DetectionType.CRACK, "Crack 3", 0.7),
            )),
        ]

        summary = aggregate_event_results(
            results=results,
            event_id="evt_001",
            engine_info=sample_engine_info,
            source_manifest="/path/manifest.json",
        )

        assert summary.frame_count == 3
        assert len(summary.top_findings) == 1
        assert summary.top_findings[0].detection_type == DetectionType.CRACK
        assert summary.top_findings[0].max_confidence == 0.9  # Max across frames
        assert summary.top_findings[0].frame_count == 3

    def test_multiple_detection_types(self, sample_engine_info: EngineInfo) -> None:
        """Test aggregation handles multiple detection types."""
        results = [
            make_result(0, 10.0, detections=(
                make_detection(DetectionType.CRACK, "Crack", 0.9),
                make_detection(DetectionType.CORROSION, "Rust", 0.7),
            )),
            make_result(1, 11.0, detections=(
                make_detection(DetectionType.LEAK, "Water stain", 0.8),
            )),
        ]

        summary = aggregate_event_results(
            results=results,
            event_id="evt_001",
            engine_info=sample_engine_info,
            source_manifest="/path/manifest.json",
        )

        assert len(summary.top_findings) == 3
        # Should be sorted by confidence
        assert summary.top_findings[0].detection_type == DetectionType.CRACK
        assert summary.top_findings[0].max_confidence == 0.9

    def test_failed_results_counted(self, sample_engine_info: EngineInfo) -> None:
        """Test failed results are counted separately."""
        results = [
            make_result(0, 10.0, detections=()),
            make_result(1, 11.0, error="API error"),
            make_result(2, 12.0, detections=()),
        ]

        summary = aggregate_event_results(
            results=results,
            event_id="evt_001",
            engine_info=sample_engine_info,
            source_manifest="/path/manifest.json",
        )

        assert summary.frame_count == 3
        assert summary.analyzed_count == 2
        assert summary.failed_count == 1

    def test_time_range_calculated(self, sample_engine_info: EngineInfo) -> None:
        """Test time range is correctly calculated."""
        results = [
            make_result(0, 10.5),
            make_result(1, 15.0),
            make_result(2, 12.3),
        ]

        summary = aggregate_event_results(
            results=results,
            event_id="evt_001",
            engine_info=sample_engine_info,
            source_manifest="/path/manifest.json",
        )

        assert summary.time_range.start_s == 10.5
        assert summary.time_range.end_s == 15.0

    def test_aggregated_confidence_by_type(self, sample_engine_info: EngineInfo) -> None:
        """Test confidence is aggregated by detection type."""
        results = [
            make_result(0, 10.0, detections=(
                make_detection(DetectionType.CRACK, confidence=0.8),
            )),
            make_result(1, 11.0, detections=(
                make_detection(DetectionType.CRACK, confidence=0.9),
                make_detection(DetectionType.CORROSION, confidence=0.6),
            )),
        ]

        summary = aggregate_event_results(
            results=results,
            event_id="evt_001",
            engine_info=sample_engine_info,
            source_manifest="/path/manifest.json",
        )

        assert summary.aggregated_confidence.by_type["crack"] == 0.9
        assert summary.aggregated_confidence.by_type["corrosion"] == 0.6

    def test_representative_frame_selected(self, sample_engine_info: EngineInfo) -> None:
        """Test representative frame is the one with highest detection confidence."""
        results = [
            make_result(0, 10.0, detections=(
                make_detection(confidence=0.6),
            )),
            make_result(1, 11.0, detections=(
                make_detection(confidence=0.9),
                make_detection(confidence=0.8),
            )),
            make_result(2, 12.0, detections=(
                make_detection(confidence=0.7),
            )),
        ]

        summary = aggregate_event_results(
            results=results,
            event_id="evt_001",
            engine_info=sample_engine_info,
            source_manifest="/path/manifest.json",
        )

        # Frame 1 has highest total confidence (0.9 + 0.8 = 1.7)
        assert summary.representative_frame is not None
        assert summary.representative_frame.frame_idx == 1
        assert summary.representative_frame.timestamp_s == 11.0

    def test_severity_aggregation(self, sample_engine_info: EngineInfo) -> None:
        """Test highest severity is selected for each finding type."""
        results = [
            make_result(0, 10.0, detections=(
                make_detection(DetectionType.CRACK, severity=Severity.LOW),
            )),
            make_result(1, 11.0, detections=(
                make_detection(DetectionType.CRACK, severity=Severity.HIGH),
            )),
            make_result(2, 12.0, detections=(
                make_detection(DetectionType.CRACK, severity=Severity.MEDIUM),
            )),
        ]

        summary = aggregate_event_results(
            results=results,
            event_id="evt_001",
            engine_info=sample_engine_info,
            source_manifest="/path/manifest.json",
        )

        assert summary.top_findings[0].severity == Severity.HIGH

    def test_top_findings_limited(self, sample_engine_info: EngineInfo) -> None:
        """Test top findings are limited to 10."""
        # Create results with many detection types
        detections = tuple(
            make_detection(
                dtype=DetectionType.OTHER,
                label=f"Detection {i}",
                confidence=0.5 + i * 0.01,
            )
            for i in range(15)
        )
        results = [make_result(0, 10.0, detections=detections)]

        summary = aggregate_event_results(
            results=results,
            event_id="evt_001",
            engine_info=sample_engine_info,
            source_manifest="/path/manifest.json",
        )

        assert len(summary.top_findings) <= 10


class TestSelectRepresentativeFrame:
    """Tests for select_representative_frame function."""

    def test_empty_results(self) -> None:
        """Test with no results."""
        result = select_representative_frame([])
        assert result is None

    def test_all_errors(self) -> None:
        """Test with all error results."""
        results = [
            make_result(0, 10.0, error="Error 1"),
            make_result(1, 11.0, error="Error 2"),
        ]

        result = select_representative_frame(results)
        assert result is None

    def test_prefers_frames_with_detections(self) -> None:
        """Test frames with detections are preferred."""
        results = [
            make_result(0, 10.0, detections=()),  # No detections
            make_result(1, 11.0, detections=(make_detection(confidence=0.5),)),
            make_result(2, 12.0, detections=()),  # No detections
        ]

        result = select_representative_frame(results)

        assert result is not None
        assert result.frame_idx == 1

    def test_highest_confidence_selected(self) -> None:
        """Test frame with highest total confidence is selected."""
        results = [
            make_result(0, 10.0, detections=(make_detection(confidence=0.5),)),
            make_result(1, 11.0, detections=(
                make_detection(confidence=0.4),
                make_detection(confidence=0.5),
            )),  # Total: 0.9
            make_result(2, 12.0, detections=(make_detection(confidence=0.6),)),
        ]

        result = select_representative_frame(results)

        assert result is not None
        assert result.frame_idx == 1  # Highest total confidence

    def test_error_results_excluded(self) -> None:
        """Test error results are excluded from selection."""
        results = [
            make_result(0, 10.0, detections=(make_detection(confidence=0.9),), error="Error"),
            make_result(1, 11.0, detections=(make_detection(confidence=0.5),)),
        ]

        result = select_representative_frame(results)

        assert result is not None
        assert result.frame_idx == 1  # Only valid result

    def test_returns_correct_fields(self) -> None:
        """Test returned RepresentativeFrame has correct fields."""
        results = [
            make_result(3, 25.5, detections=(make_detection(confidence=0.8),)),
        ]

        result = select_representative_frame(results)

        assert result is not None
        assert result.frame_idx == 3
        assert result.timestamp_s == 25.5
        assert result.image_path == "frames/003.jpg"
