"""Tests for detection data types."""

import pytest

from inf3_analytics.types.detection import (
    AggregatedConfidence,
    AnalyticsManifest,
    BoundingBox,
    Detection,
    DetectionAttributes,
    DetectionType,
    EngineInfo,
    EventAnalyticsSummary,
    Finding,
    FrameAnalyticsResult,
    FrameMeta,
    QAPair,
    RepresentativeFrame,
    Severity,
    TimeRange,
)


class TestBoundingBox:
    """Tests for BoundingBox type."""

    def test_to_dict(self) -> None:
        bbox = BoundingBox(x=0.1, y=0.2, w=0.3, h=0.4)
        result = bbox.to_dict()
        assert result == {"x": 0.1, "y": 0.2, "w": 0.3, "h": 0.4}

    def test_from_dict(self) -> None:
        data = {"x": 0.5, "y": 0.6, "w": 0.2, "h": 0.1}
        bbox = BoundingBox.from_dict(data)
        assert bbox.x == 0.5
        assert bbox.y == 0.6
        assert bbox.w == 0.2
        assert bbox.h == 0.1

    def test_roundtrip(self) -> None:
        original = BoundingBox(x=0.25, y=0.75, w=0.5, h=0.25)
        restored = BoundingBox.from_dict(original.to_dict())
        assert restored == original


class TestDetectionAttributes:
    """Tests for DetectionAttributes type."""

    def test_to_dict_full(self) -> None:
        attrs = DetectionAttributes(
            severity=Severity.HIGH,
            materials=("concrete", "steel"),
            location_hint="upper left",
            notes="Visible damage",
        )
        result = attrs.to_dict()
        assert result["severity"] == "high"
        assert result["materials"] == ["concrete", "steel"]
        assert result["location_hint"] == "upper left"
        assert result["notes"] == "Visible damage"

    def test_to_dict_nulls(self) -> None:
        attrs = DetectionAttributes(
            severity=None,
            materials=None,
            location_hint=None,
            notes=None,
        )
        result = attrs.to_dict()
        assert result["severity"] is None
        assert result["materials"] is None

    def test_from_dict(self) -> None:
        data = {
            "severity": "medium",
            "materials": ["rust", "metal"],
            "location_hint": "center",
            "notes": "test",
        }
        attrs = DetectionAttributes.from_dict(data)
        assert attrs.severity == Severity.MEDIUM
        assert attrs.materials == ("rust", "metal")

    def test_roundtrip(self) -> None:
        original = DetectionAttributes(
            severity=Severity.LOW,
            materials=("wood",),
            location_hint="bottom",
            notes="Minor issue",
        )
        restored = DetectionAttributes.from_dict(original.to_dict())
        assert restored == original


class TestDetection:
    """Tests for Detection type."""

    def test_to_dict(self) -> None:
        detection = Detection(
            detection_type=DetectionType.CRACK,
            label="Hairline crack",
            confidence=0.85,
            bbox=BoundingBox(x=0.1, y=0.2, w=0.3, h=0.1),
            attributes=DetectionAttributes(
                severity=Severity.MEDIUM,
                materials=None,
                location_hint=None,
                notes=None,
            ),
        )
        result = detection.to_dict()
        assert result["type"] == "crack"
        assert result["label"] == "Hairline crack"
        assert result["confidence"] == 0.85
        assert result["bbox"] is not None

    def test_from_dict(self) -> None:
        data = {
            "type": "corrosion",
            "label": "Surface rust",
            "confidence": 0.72,
            "bbox": None,
            "attributes": {"severity": "low", "materials": None, "location_hint": None, "notes": None},
        }
        detection = Detection.from_dict(data)
        assert detection.detection_type == DetectionType.CORROSION
        assert detection.label == "Surface rust"
        assert detection.confidence == 0.72
        assert detection.bbox is None

    def test_roundtrip(self) -> None:
        original = Detection(
            detection_type=DetectionType.STRUCTURAL_ANOMALY,
            label="Deformation",
            confidence=0.9,
            bbox=None,
            attributes=DetectionAttributes(
                severity=Severity.HIGH,
                materials=("steel",),
                location_hint="beam joint",
                notes="Requires immediate attention",
            ),
        )
        restored = Detection.from_dict(original.to_dict())
        assert restored == original


class TestQAPair:
    """Tests for QAPair type."""

    def test_to_dict(self) -> None:
        qa = QAPair(question="Is there cracking?", answer="Yes, visible crack")
        result = qa.to_dict()
        assert result == {"q": "Is there cracking?", "a": "Yes, visible crack"}

    def test_from_dict(self) -> None:
        data = {"q": "Is rust present?", "a": "No"}
        qa = QAPair.from_dict(data)
        assert qa.question == "Is rust present?"
        assert qa.answer == "No"


class TestEngineInfo:
    """Tests for EngineInfo type."""

    def test_vlm_engine_info(self) -> None:
        info = EngineInfo(
            name="vlm",
            provider="openai",
            model="gpt-5-mini",
            prompt_version="v1",
            version="0.1.0",
            config={"temperature": 0.2},
        )
        result = info.to_dict()
        assert result["name"] == "vlm"
        assert result["provider"] == "openai"
        assert result["model"] == "gpt-5-mini"
        assert result["prompt_version"] == "v1"

    def test_baseline_engine_info(self) -> None:
        info = EngineInfo(
            name="baseline_quality",
            provider=None,
            model=None,
            prompt_version=None,
            version="0.1.0",
            config={"blur_threshold": 100.0},
        )
        result = info.to_dict()
        assert result["provider"] is None
        assert result["model"] is None

    def test_roundtrip(self) -> None:
        original = EngineInfo(
            name="vlm",
            provider="gemini",
            model="gemini-3-flash-preview",
            prompt_version="v1",
            version="0.1.0",
            config={"max_tokens": 2048},
        )
        restored = EngineInfo.from_dict(original.to_dict())
        assert restored == original


class TestFrameMeta:
    """Tests for FrameMeta type."""

    def test_full_meta(self) -> None:
        meta = FrameMeta(
            frame_idx=0,
            timestamp_s=10.5,
            timestamp_ts="00:00:10,500",
            image_path="frames/000.jpg",
            event_id="evt_001",
            event_title="Crack detected",
            event_summary="Visible crack in concrete",
            transcript_excerpt="I can see a crack here",
        )
        result = meta.to_dict()
        assert result["frame_idx"] == 0
        assert result["timestamp_s"] == 10.5
        assert result["event_id"] == "evt_001"

    def test_minimal_meta(self) -> None:
        meta = FrameMeta(
            frame_idx=1,
            timestamp_s=20.0,
            timestamp_ts="00:00:20,000",
            image_path="frames/001.jpg",
            event_id="evt_002",
            event_title=None,
            event_summary=None,
            transcript_excerpt=None,
        )
        result = meta.to_dict()
        assert result["event_title"] is None
        assert result["transcript_excerpt"] is None

    def test_roundtrip(self) -> None:
        original = FrameMeta(
            frame_idx=5,
            timestamp_s=55.5,
            timestamp_ts="00:00:55,500",
            image_path="frames/005.jpg",
            event_id="evt_003",
            event_title="Test event",
            event_summary="Test summary",
            transcript_excerpt="Test excerpt",
        )
        restored = FrameMeta.from_dict(original.to_dict())
        assert restored == original


class TestFrameAnalyticsResult:
    """Tests for FrameAnalyticsResult type."""

    @pytest.fixture
    def sample_engine_info(self) -> EngineInfo:
        return EngineInfo(
            name="vlm",
            provider="openai",
            model="gpt-5-mini",
            prompt_version="v1",
            version="0.1.0",
            config={},
        )

    @pytest.fixture
    def sample_detection(self) -> Detection:
        return Detection(
            detection_type=DetectionType.CRACK,
            label="Crack",
            confidence=0.8,
            bbox=None,
            attributes=DetectionAttributes(
                severity=Severity.MEDIUM,
                materials=None,
                location_hint=None,
                notes=None,
            ),
        )

    def test_success_result(
        self, sample_engine_info: EngineInfo, sample_detection: Detection
    ) -> None:
        result = FrameAnalyticsResult(
            event_id="evt_001",
            frame_idx=0,
            timestamp_s=10.0,
            timestamp_ts="00:00:10,000",
            image_path="frames/000.jpg",
            engine=sample_engine_info,
            detections=(sample_detection,),
            scene_summary="Concrete surface with visible crack",
            qa=(QAPair(question="Is there cracking?", answer="Yes"),),
            raw_model_output=None,
            error=None,
        )
        data = result.to_dict()
        assert len(data["detections"]) == 1
        assert data["error"] is None

    def test_error_result(self, sample_engine_info: EngineInfo) -> None:
        result = FrameAnalyticsResult(
            event_id="evt_001",
            frame_idx=0,
            timestamp_s=10.0,
            timestamp_ts="00:00:10,000",
            image_path="frames/000.jpg",
            engine=sample_engine_info,
            detections=(),
            scene_summary="",
            qa=None,
            raw_model_output=None,
            error="API call failed",
        )
        data = result.to_dict()
        assert data["error"] == "API call failed"
        assert len(data["detections"]) == 0

    def test_roundtrip(
        self, sample_engine_info: EngineInfo, sample_detection: Detection
    ) -> None:
        original = FrameAnalyticsResult(
            event_id="evt_001",
            frame_idx=0,
            timestamp_s=10.0,
            timestamp_ts="00:00:10,000",
            image_path="frames/000.jpg",
            engine=sample_engine_info,
            detections=(sample_detection,),
            scene_summary="Test scene",
            qa=(QAPair(question="Q?", answer="A"),),
            raw_model_output={"test": "data"},
            error=None,
        )
        restored = FrameAnalyticsResult.from_dict(original.to_dict())
        assert restored.event_id == original.event_id
        assert restored.frame_idx == original.frame_idx
        assert len(restored.detections) == len(original.detections)


class TestEventAnalyticsSummary:
    """Tests for EventAnalyticsSummary type."""

    @pytest.fixture
    def sample_summary(self) -> EventAnalyticsSummary:
        return EventAnalyticsSummary(
            event_id="evt_001",
            engine=EngineInfo(
                name="vlm",
                provider="gemini",
                model="gemini-3-flash-preview",
                prompt_version="v1",
                version="0.1.0",
                config={},
            ),
            frame_count=5,
            analyzed_count=5,
            failed_count=0,
            time_range=TimeRange(start_s=10.0, end_s=20.0),
            top_findings=(
                Finding(
                    detection_type=DetectionType.CRACK,
                    label="Crack",
                    max_confidence=0.9,
                    frame_count=3,
                    severity=Severity.HIGH,
                ),
            ),
            aggregated_confidence=AggregatedConfidence(by_type={"crack": 0.9}),
            representative_frame=RepresentativeFrame(
                frame_idx=2,
                image_path="frames/002.jpg",
                timestamp_s=15.0,
            ),
            created_at="2024-01-15T10:00:00",
            source_manifest="/path/to/manifest.json",
        )

    def test_to_dict(self, sample_summary: EventAnalyticsSummary) -> None:
        data = sample_summary.to_dict()
        assert data["event_id"] == "evt_001"
        assert data["frame_count"] == 5
        assert len(data["top_findings"]) == 1
        assert data["representative_frame"] is not None

    def test_roundtrip(self, sample_summary: EventAnalyticsSummary) -> None:
        restored = EventAnalyticsSummary.from_dict(sample_summary.to_dict())
        assert restored.event_id == sample_summary.event_id
        assert restored.frame_count == sample_summary.frame_count
        assert len(restored.top_findings) == len(sample_summary.top_findings)


class TestAnalyticsManifest:
    """Tests for AnalyticsManifest type."""

    def test_manifest(self) -> None:
        manifest = AnalyticsManifest(
            run_id="run_20240115_100000_abc12345",
            engine=EngineInfo(
                name="vlm",
                provider="openai",
                model="gpt-5-mini",
                prompt_version="v1",
                version="0.1.0",
                config={},
            ),
            source_event_frames_manifest="/path/to/manifest.json",
            events_file="/path/to/events.json",
            total_events=10,
            total_frames=50,
            analyzed_frames=48,
            failed_frames=2,
            created_at="2024-01-15T10:00:00",
            event_summaries=("evt_001/summary.json", "evt_002/summary.json"),
        )
        data = manifest.to_dict()
        assert data["run_id"] == "run_20240115_100000_abc12345"
        assert data["total_events"] == 10
        assert len(data["event_summaries"]) == 2

    def test_roundtrip(self) -> None:
        original = AnalyticsManifest(
            run_id="run_test",
            engine=EngineInfo(
                name="baseline_quality",
                provider=None,
                model=None,
                prompt_version=None,
                version="0.1.0",
                config={},
            ),
            source_event_frames_manifest="manifest.json",
            events_file=None,
            total_events=5,
            total_frames=25,
            analyzed_frames=25,
            failed_frames=0,
            created_at="2024-01-15T10:00:00",
            event_summaries=(),
        )
        restored = AnalyticsManifest.from_dict(original.to_dict())
        assert restored.run_id == original.run_id
        assert restored.events_file is None
