"""Tests for hardhat color classification (mock-based, no GPU required)."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from inf3_analytics.types.detection import BoundingBox, HardhatColor


def _cv2_available() -> bool:
    """Check if opencv-python is installed."""
    try:
        import cv2  # noqa: F401

        return True
    except ImportError:
        return False


_skip_no_cv2 = pytest.mark.skipif(not _cv2_available(), reason="opencv-python not installed")


@pytest.fixture
def sample_bbox() -> BoundingBox:
    """Bounding box in the center of the image."""
    return BoundingBox(x=0.3, y=0.3, w=0.2, h=0.2)


class TestClassifyColorHistogram:
    """Tests for HSV histogram-based color classification."""

    def _make_solid_image(self, tmp_path: Path, bgr: tuple[int, int, int]) -> Path:
        """Create a solid-color test image."""
        import cv2
        import numpy as np

        img = np.full((100, 100, 3), bgr, dtype=np.uint8)
        path = tmp_path / "test.jpg"
        cv2.imwrite(str(path), img)
        return path

    @_skip_no_cv2
    def test_white_hardhat(self, tmp_path: Path, sample_bbox: BoundingBox) -> None:
        """White image should classify as WHITE."""
        from inf3_analytics.frame_analytics.color_classify import classify_color_histogram

        img_path = self._make_solid_image(tmp_path, (255, 255, 255))
        result = classify_color_histogram(img_path, sample_bbox)
        assert result == HardhatColor.WHITE

    @_skip_no_cv2
    def test_yellow_hardhat(self, tmp_path: Path, sample_bbox: BoundingBox) -> None:
        """Yellow image should classify as YELLOW."""
        from inf3_analytics.frame_analytics.color_classify import classify_color_histogram

        img_path = self._make_solid_image(tmp_path, (0, 255, 255))
        result = classify_color_histogram(img_path, sample_bbox)
        assert result == HardhatColor.YELLOW

    @_skip_no_cv2
    def test_blue_hardhat(self, tmp_path: Path, sample_bbox: BoundingBox) -> None:
        """Blue image should classify as BLUE."""
        from inf3_analytics.frame_analytics.color_classify import classify_color_histogram

        img_path = self._make_solid_image(tmp_path, (255, 0, 0))
        result = classify_color_histogram(img_path, sample_bbox)
        assert result == HardhatColor.BLUE

    @_skip_no_cv2
    def test_invalid_image_returns_other(self, sample_bbox: BoundingBox) -> None:
        """Non-existent image should return OTHER."""
        from inf3_analytics.frame_analytics.color_classify import classify_color_histogram

        result = classify_color_histogram(Path("/nonexistent.jpg"), sample_bbox)
        assert result == HardhatColor.OTHER

    @_skip_no_cv2
    def test_zero_size_bbox_returns_other(self, tmp_path: Path) -> None:
        """Zero-sized bbox should return OTHER."""
        from inf3_analytics.frame_analytics.color_classify import classify_color_histogram

        img_path = self._make_solid_image(tmp_path, (255, 255, 255))
        zero_bbox = BoundingBox(x=0.5, y=0.5, w=0.0, h=0.0)
        result = classify_color_histogram(img_path, zero_bbox)
        assert result == HardhatColor.OTHER


class TestClassifyColorVLM:
    """Tests for VLM-based color classification."""

    @_skip_no_cv2
    def test_vlm_returns_yellow(self, tmp_path: Path, sample_bbox: BoundingBox) -> None:
        """VLM returning 'yellow' should map to HardhatColor.YELLOW."""
        from inf3_analytics.frame_analytics.color_classify import classify_color_vlm

        import cv2
        import numpy as np

        img = np.full((100, 100, 3), (0, 255, 255), dtype=np.uint8)
        img_path = tmp_path / "test.jpg"
        cv2.imwrite(str(img_path), img)

        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.text = "yellow"
        mock_client.models.generate_content.return_value = mock_response

        result = classify_color_vlm(img_path, sample_bbox, client=mock_client)
        assert result == HardhatColor.YELLOW

    @_skip_no_cv2
    def test_vlm_returns_unknown(self, tmp_path: Path, sample_bbox: BoundingBox) -> None:
        """VLM returning unrecognized text should map to OTHER."""
        from inf3_analytics.frame_analytics.color_classify import classify_color_vlm

        import cv2
        import numpy as np

        img = np.full((100, 100, 3), (128, 128, 128), dtype=np.uint8)
        img_path = tmp_path / "test.jpg"
        cv2.imwrite(str(img_path), img)

        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.text = "purple"
        mock_client.models.generate_content.return_value = mock_response

        result = classify_color_vlm(img_path, sample_bbox, client=mock_client)
        assert result == HardhatColor.OTHER

    @_skip_no_cv2
    def test_vlm_api_failure_returns_other(
        self, tmp_path: Path, sample_bbox: BoundingBox
    ) -> None:
        """API failure should return OTHER gracefully."""
        from inf3_analytics.frame_analytics.color_classify import classify_color_vlm

        import cv2
        import numpy as np

        img = np.full((100, 100, 3), (128, 128, 128), dtype=np.uint8)
        img_path = tmp_path / "test.jpg"
        cv2.imwrite(str(img_path), img)

        mock_client = MagicMock()
        mock_client.models.generate_content.side_effect = RuntimeError("API error")

        result = classify_color_vlm(img_path, sample_bbox, client=mock_client)
        assert result == HardhatColor.OTHER

    @_skip_no_cv2
    def test_vlm_invalid_image_returns_other(self, sample_bbox: BoundingBox) -> None:
        """Non-existent image should return OTHER."""
        from inf3_analytics.frame_analytics.color_classify import classify_color_vlm

        mock_client = MagicMock()
        result = classify_color_vlm(
            Path("/nonexistent.jpg"), sample_bbox, client=mock_client
        )
        assert result == HardhatColor.OTHER


class TestSiteCountAggregation:
    """Tests for construction site count aggregation."""

    def test_aggregate_empty(self) -> None:
        """Empty results produce empty time series."""
        from inf3_analytics.frame_analytics.aggregate import aggregate_site_counts
        from inf3_analytics.types.detection import EngineInfo

        engine_info = EngineInfo(
            name="yolo_world", provider=None, model="test",
            prompt_version=None, version="0.1.0", config={},
        )
        ts = aggregate_site_counts([], engine_info)
        assert ts.summary.total_frames == 0
        assert ts.summary.peak_persons == 0
        assert len(ts.frames) == 0

    def test_aggregate_single_frame(self) -> None:
        """Single frame with detections produces correct counts."""
        from inf3_analytics.frame_analytics.aggregate import aggregate_site_counts
        from inf3_analytics.types.detection import (
            Detection,
            DetectionAttributes,
            DetectionType,
            EngineInfo,
            EquipmentClass,
            FrameAnalyticsResult,
            HardhatColor,
        )

        engine_info = EngineInfo(
            name="yolo_world", provider=None, model="test",
            prompt_version=None, version="0.1.0", config={},
        )

        result = FrameAnalyticsResult(
            event_id="test",
            frame_idx=0,
            timestamp_s=1.0,
            timestamp_ts="00:00:01,000",
            image_path="frame.jpg",
            engine=engine_info,
            detections=(
                Detection(
                    detection_type=DetectionType.CONSTRUCTION_EQUIPMENT,
                    label="excavator",
                    confidence=0.9,
                    bbox=None,
                    attributes=DetectionAttributes(
                        severity=None, materials=None, location_hint=None,
                        notes=None, equipment_class=EquipmentClass.EXCAVATOR,
                    ),
                ),
                Detection(
                    detection_type=DetectionType.PERSON,
                    label="person",
                    confidence=0.85,
                    bbox=None,
                    attributes=DetectionAttributes(
                        severity=None, materials=None, location_hint=None, notes=None,
                    ),
                ),
                Detection(
                    detection_type=DetectionType.HARDHAT,
                    label="yellow hardhat",
                    confidence=0.8,
                    bbox=None,
                    attributes=DetectionAttributes(
                        severity=None, materials=None, location_hint=None,
                        notes=None, hardhat_color=HardhatColor.YELLOW,
                    ),
                ),
            ),
            scene_summary="Test",
            qa=None,
            raw_model_output=None,
            error=None,
        )

        ts = aggregate_site_counts([result], engine_info)
        assert ts.summary.total_frames == 1
        assert ts.summary.peak_persons == 1
        assert ts.summary.peak_equipment == {"excavator": 1}
        assert ts.summary.peak_hardhats == {"yellow": 1}
        assert ts.summary.avg_persons == 1.0

    def test_aggregate_multiple_frames_peak(self) -> None:
        """Peak counts track the maximum across frames."""
        from inf3_analytics.frame_analytics.aggregate import aggregate_site_counts
        from inf3_analytics.types.detection import (
            Detection,
            DetectionAttributes,
            DetectionType,
            EngineInfo,
            FrameAnalyticsResult,
        )

        engine_info = EngineInfo(
            name="yolo_world", provider=None, model="test",
            prompt_version=None, version="0.1.0", config={},
        )

        def _make_result(frame_idx: int, person_count: int) -> FrameAnalyticsResult:
            persons = tuple(
                Detection(
                    detection_type=DetectionType.PERSON,
                    label="person",
                    confidence=0.9,
                    bbox=None,
                    attributes=DetectionAttributes(
                        severity=None, materials=None, location_hint=None, notes=None,
                    ),
                )
                for _ in range(person_count)
            )
            return FrameAnalyticsResult(
                event_id="test",
                frame_idx=frame_idx,
                timestamp_s=float(frame_idx),
                timestamp_ts=f"00:00:{frame_idx:02d},000",
                image_path=f"frame_{frame_idx}.jpg",
                engine=engine_info,
                detections=persons,
                scene_summary="Test",
                qa=None,
                raw_model_output=None,
                error=None,
            )

        results = [_make_result(0, 2), _make_result(1, 5), _make_result(2, 3)]
        ts = aggregate_site_counts(results, engine_info)

        assert ts.summary.peak_persons == 5
        assert ts.summary.avg_persons == pytest.approx(10 / 3, rel=0.01)
        assert ts.summary.total_frames == 3

    def test_aggregate_skips_errors(self) -> None:
        """Error results are excluded from aggregation."""
        from inf3_analytics.frame_analytics.aggregate import aggregate_site_counts
        from inf3_analytics.types.detection import EngineInfo, FrameAnalyticsResult

        engine_info = EngineInfo(
            name="yolo_world", provider=None, model="test",
            prompt_version=None, version="0.1.0", config={},
        )

        error_result = FrameAnalyticsResult(
            event_id="test",
            frame_idx=0,
            timestamp_s=0.0,
            timestamp_ts="00:00:00,000",
            image_path="frame.jpg",
            engine=engine_info,
            detections=(),
            scene_summary="",
            qa=None,
            raw_model_output=None,
            error="YOLO inference failed",
        )

        ts = aggregate_site_counts([error_result], engine_info)
        assert ts.summary.total_frames == 0


class TestFrameCountSerialization:
    """Tests for FrameCount and SiteCountTimeSeries serialization."""

    def test_frame_count_roundtrip(self) -> None:
        """FrameCount serializes and deserializes correctly."""
        from inf3_analytics.frame_analytics.aggregate import FrameCount

        original = FrameCount(
            frame_idx=5,
            timestamp_s=10.0,
            timestamp_ts="00:00:10,000",
            equipment_counts={"excavator": 2, "crane": 1},
            person_count=3,
            hardhat_counts={"yellow": 2, "white": 1},
        )
        restored = FrameCount.from_dict(original.to_dict())
        assert restored.frame_idx == original.frame_idx
        assert restored.equipment_counts == original.equipment_counts
        assert restored.person_count == original.person_count
        assert restored.hardhat_counts == original.hardhat_counts

    def test_site_count_summary_roundtrip(self) -> None:
        """SiteCountSummary serializes and deserializes correctly."""
        from inf3_analytics.frame_analytics.aggregate import SiteCountSummary

        original = SiteCountSummary(
            peak_equipment={"excavator": 3},
            peak_persons=5,
            peak_hardhats={"yellow": 4},
            avg_persons=2.5,
            total_frames=10,
        )
        restored = SiteCountSummary.from_dict(original.to_dict())
        assert restored.peak_equipment == original.peak_equipment
        assert restored.peak_persons == original.peak_persons
        assert restored.avg_persons == original.avg_persons

    def test_time_series_roundtrip(self) -> None:
        """SiteCountTimeSeries serializes and deserializes correctly."""
        from inf3_analytics.frame_analytics.aggregate import (
            FrameCount,
            SiteCountSummary,
            SiteCountTimeSeries,
        )
        from inf3_analytics.types.detection import EngineInfo

        engine_info = EngineInfo(
            name="yolo_world", provider=None, model="test",
            prompt_version=None, version="0.1.0", config={},
        )

        original = SiteCountTimeSeries(
            engine=engine_info,
            frames=(
                FrameCount(
                    frame_idx=0, timestamp_s=0.0, timestamp_ts="00:00:00,000",
                    equipment_counts={"crane": 1}, person_count=2,
                    hardhat_counts={"white": 1},
                ),
            ),
            summary=SiteCountSummary(
                peak_equipment={"crane": 1},
                peak_persons=2,
                peak_hardhats={"white": 1},
                avg_persons=2.0,
                total_frames=1,
            ),
        )
        data = original.to_dict()
        restored = SiteCountTimeSeries.from_dict(data)
        assert len(restored.frames) == 1
        assert restored.summary.peak_persons == 2


class TestDetectionAttributesExtended:
    """Tests for extended DetectionAttributes with equipment_class and hardhat_color."""

    def test_equipment_class_serialization(self) -> None:
        """equipment_class round-trips through to_dict/from_dict."""
        from inf3_analytics.types.detection import (
            DetectionAttributes,
            EquipmentClass,
        )

        attrs = DetectionAttributes(
            severity=None, materials=None, location_hint=None, notes=None,
            equipment_class=EquipmentClass.CRANE,
        )
        data = attrs.to_dict()
        assert data["equipment_class"] == "crane"

        restored = DetectionAttributes.from_dict(data)
        assert restored.equipment_class == EquipmentClass.CRANE

    def test_hardhat_color_serialization(self) -> None:
        """hardhat_color round-trips through to_dict/from_dict."""
        from inf3_analytics.types.detection import (
            DetectionAttributes,
            HardhatColor,
        )

        attrs = DetectionAttributes(
            severity=None, materials=None, location_hint=None, notes=None,
            hardhat_color=HardhatColor.ORANGE,
        )
        data = attrs.to_dict()
        assert data["hardhat_color"] == "orange"

        restored = DetectionAttributes.from_dict(data)
        assert restored.hardhat_color == HardhatColor.ORANGE

    def test_none_fields_omitted(self) -> None:
        """None equipment_class and hardhat_color are omitted from dict."""
        from inf3_analytics.types.detection import DetectionAttributes

        attrs = DetectionAttributes(
            severity=None, materials=None, location_hint=None, notes=None,
        )
        data = attrs.to_dict()
        assert "equipment_class" not in data
        assert "hardhat_color" not in data

    def test_backward_compatible_from_dict(self) -> None:
        """Old dicts without equipment_class/hardhat_color still parse."""
        from inf3_analytics.types.detection import DetectionAttributes

        data = {"severity": "low", "materials": None, "location_hint": None, "notes": None}
        attrs = DetectionAttributes.from_dict(data)
        assert attrs.equipment_class is None
        assert attrs.hardhat_color is None
