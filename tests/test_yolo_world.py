"""Tests for YOLO-World engine (mock-based, no GPU required)."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from inf3_analytics.frame_analytics.yolo_world import (
    DEFAULT_CLASSES,
    YOLOWorldEngine,
    _classify_detection,
)
from inf3_analytics.types.detection import (
    DetectionType,
    EquipmentClass,
    FrameMeta,
    HardhatColor,
)


@pytest.fixture
def sample_frame_meta() -> FrameMeta:
    """Create sample frame metadata for tests."""
    return FrameMeta(
        frame_idx=0,
        timestamp_s=10.5,
        timestamp_ts="00:00:10,500",
        image_path="frames/000.jpg",
        event_id="site_001",
        event_title="site_analytics",
        event_summary=None,
        transcript_excerpt=None,
    )


class TestClassifyDetection:
    """Tests for _classify_detection label mapping."""

    def test_excavator(self) -> None:
        dtype, attrs = _classify_detection("excavator")
        assert dtype == DetectionType.CONSTRUCTION_EQUIPMENT
        assert attrs.equipment_class == EquipmentClass.EXCAVATOR

    def test_crane(self) -> None:
        dtype, attrs = _classify_detection("construction crane")
        assert dtype == DetectionType.CONSTRUCTION_EQUIPMENT
        assert attrs.equipment_class == EquipmentClass.CRANE

    def test_dump_truck(self) -> None:
        dtype, attrs = _classify_detection("dump truck")
        assert dtype == DetectionType.CONSTRUCTION_EQUIPMENT
        assert attrs.equipment_class == EquipmentClass.DUMP_TRUCK

    def test_concrete_mixer(self) -> None:
        dtype, attrs = _classify_detection("concrete mixer")
        assert dtype == DetectionType.CONSTRUCTION_EQUIPMENT
        assert attrs.equipment_class == EquipmentClass.CONCRETE_MIXER

    def test_bulldozer(self) -> None:
        dtype, attrs = _classify_detection("bulldozer")
        assert dtype == DetectionType.CONSTRUCTION_EQUIPMENT
        assert attrs.equipment_class == EquipmentClass.BULLDOZER

    def test_loader(self) -> None:
        dtype, attrs = _classify_detection("loader")
        assert dtype == DetectionType.CONSTRUCTION_EQUIPMENT
        assert attrs.equipment_class == EquipmentClass.LOADER

    def test_scaffolding(self) -> None:
        dtype, attrs = _classify_detection("scaffolding")
        assert dtype == DetectionType.CONSTRUCTION_EQUIPMENT
        assert attrs.equipment_class == EquipmentClass.SCAFFOLDING

    def test_person(self) -> None:
        dtype, attrs = _classify_detection("person")
        assert dtype == DetectionType.PERSON
        assert attrs.equipment_class is None
        assert attrs.hardhat_color is None

    def test_yellow_hardhat(self) -> None:
        dtype, attrs = _classify_detection("yellow hardhat")
        assert dtype == DetectionType.HARDHAT
        assert attrs.hardhat_color == HardhatColor.YELLOW

    def test_white_hardhat(self) -> None:
        dtype, attrs = _classify_detection("white hardhat")
        assert dtype == DetectionType.HARDHAT
        assert attrs.hardhat_color == HardhatColor.WHITE

    def test_red_hardhat(self) -> None:
        dtype, attrs = _classify_detection("red hardhat")
        assert dtype == DetectionType.HARDHAT
        assert attrs.hardhat_color == HardhatColor.RED

    def test_blue_hardhat(self) -> None:
        dtype, attrs = _classify_detection("blue hardhat")
        assert dtype == DetectionType.HARDHAT
        assert attrs.hardhat_color == HardhatColor.BLUE

    def test_unknown_label(self) -> None:
        dtype, attrs = _classify_detection("forklift")
        assert dtype == DetectionType.OTHER
        assert attrs.notes == "forklift"

    def test_case_insensitive(self) -> None:
        dtype, attrs = _classify_detection("Excavator")
        assert dtype == DetectionType.CONSTRUCTION_EQUIPMENT
        assert attrs.equipment_class == EquipmentClass.EXCAVATOR

    def test_whitespace_handling(self) -> None:
        dtype, attrs = _classify_detection("  construction crane  ")
        assert dtype == DetectionType.CONSTRUCTION_EQUIPMENT
        assert attrs.equipment_class == EquipmentClass.CRANE


class TestYOLOWorldEngine:
    """Tests for YOLOWorldEngine lifecycle and configuration."""

    def test_default_classes(self) -> None:
        """Default classes include equipment, person, and hardhat variants."""
        assert "excavator" in DEFAULT_CLASSES
        assert "construction crane" in DEFAULT_CLASSES
        assert "person" in DEFAULT_CLASSES
        assert "yellow hardhat" in DEFAULT_CLASSES
        assert "white hardhat" in DEFAULT_CLASSES

    def test_engine_not_loaded_raises(self) -> None:
        """Analyze raises if engine not loaded."""
        engine = YOLOWorldEngine()
        assert not engine.is_loaded

        with pytest.raises(RuntimeError, match="not loaded"):
            engine.analyze(
                image_path=Path("/fake/path.jpg"),
                event=None,
                frame_meta=MagicMock(),
            )

    def test_get_engine_info(self) -> None:
        """Engine info contains correct metadata."""
        from inf3_analytics.frame_analytics import AnalyticsConfig

        config = AnalyticsConfig(model_name="yolov8s-worldv2")
        engine = YOLOWorldEngine(config=config, confidence_threshold=0.25)

        info = engine.get_engine_info()
        assert info.name == "yolo_world"
        assert info.provider is None
        assert info.model == "yolov8s-worldv2"
        assert info.prompt_version is None
        assert info.config["confidence_threshold"] == 0.25
        assert "classes" in info.config

    def test_custom_classes(self) -> None:
        """Custom classes are stored correctly."""
        custom = ("excavator", "crane", "person")
        engine = YOLOWorldEngine(classes=custom)
        info = engine.get_engine_info()
        assert info.config["classes"] == ["excavator", "crane", "person"]

    def test_load_without_ultralytics_raises(self) -> None:
        """Load raises ImportError if ultralytics not installed."""
        engine = YOLOWorldEngine()

        with patch.dict("sys.modules", {"ultralytics": None}):
            with pytest.raises(ImportError, match="ultralytics"):
                engine.load()

    def test_analyze_with_mock_model(
        self, sample_frame_meta: FrameMeta, tmp_path: Path
    ) -> None:
        """Test analyze with a fully mocked YOLO model."""
        # Create a fake image file
        img_path = tmp_path / "test.jpg"
        img_path.write_bytes(b"\xff\xd8\xff\xe0" + b"\x00" * 100)

        # Mock prediction results
        import numpy as np

        mock_result = MagicMock()
        mock_result.orig_shape = (480, 640)
        mock_result.names = {0: "excavator", 1: "person", 2: "yellow hardhat"}

        mock_boxes = MagicMock()
        mock_boxes.conf = np.array([0.85, 0.92, 0.78])
        mock_boxes.cls = np.array([0, 1, 2])
        mock_boxes.xyxy = np.array([
            [100.0, 200.0, 300.0, 400.0],  # excavator
            [50.0, 100.0, 100.0, 250.0],   # person
            [55.0, 95.0, 85.0, 115.0],     # yellow hardhat
        ])
        mock_boxes.__len__ = lambda self: 3
        mock_result.boxes = mock_boxes

        mock_model = MagicMock()
        mock_model.predict.return_value = [mock_result]

        # Create and run engine (bypass actual model loading)
        engine = YOLOWorldEngine(confidence_threshold=0.1)
        engine._model = mock_model
        engine._loaded = True

        result = engine.analyze(
            image_path=img_path,
            event=None,
            frame_meta=sample_frame_meta,
        )

        assert result.error is None
        assert len(result.detections) == 3

        # Check excavator detection
        excavator = result.detections[0]
        assert excavator.detection_type == DetectionType.CONSTRUCTION_EQUIPMENT
        assert excavator.label == "excavator"
        assert excavator.confidence == 0.85
        assert excavator.bbox is not None
        assert excavator.attributes.equipment_class == EquipmentClass.EXCAVATOR

        # Check person detection
        person = result.detections[1]
        assert person.detection_type == DetectionType.PERSON
        assert person.confidence == 0.92

        # Check hardhat detection
        hardhat = result.detections[2]
        assert hardhat.detection_type == DetectionType.HARDHAT
        assert hardhat.attributes.hardhat_color == HardhatColor.YELLOW

        # Check scene summary
        assert "excavator" in result.scene_summary.lower()

    def test_analyze_no_detections(
        self, sample_frame_meta: FrameMeta, tmp_path: Path
    ) -> None:
        """Test analyze when no objects are detected."""
        img_path = tmp_path / "empty.jpg"
        img_path.write_bytes(b"\xff\xd8\xff\xe0" + b"\x00" * 100)

        mock_model = MagicMock()
        mock_model.predict.return_value = []

        engine = YOLOWorldEngine()
        engine._model = mock_model
        engine._loaded = True

        result = engine.analyze(
            image_path=img_path,
            event=None,
            frame_meta=sample_frame_meta,
        )

        assert result.error is None
        assert len(result.detections) == 0
        assert "no objects" in result.scene_summary.lower()

    def test_analyze_missing_image(self, sample_frame_meta: FrameMeta) -> None:
        """Test analyze with non-existent image raises FileNotFoundError."""
        engine = YOLOWorldEngine()
        engine._model = MagicMock()
        engine._loaded = True

        with pytest.raises(FileNotFoundError):
            engine.analyze(
                image_path=Path("/nonexistent/image.jpg"),
                event=None,
                frame_meta=sample_frame_meta,
            )

    def test_unload(self) -> None:
        """Test unload clears model."""
        engine = YOLOWorldEngine()
        engine._model = MagicMock()
        engine._loaded = True

        engine.unload()
        assert not engine.is_loaded
        assert engine._model is None


class TestEngineRegistry:
    """Tests for YOLO-World engine registration."""

    def test_yolo_world_in_registry(self) -> None:
        """yolo_world is listed in engine registry."""
        from inf3_analytics.frame_analytics import list_engines

        engines = list_engines()
        assert "yolo_world" in engines

    def test_yolo_alias(self) -> None:
        """'yolo' alias resolves to YOLOWorldEngine."""
        from inf3_analytics.frame_analytics import get_engine

        engine_cls = get_engine("yolo")
        assert engine_cls.__name__ == "YOLOWorldEngine"

    def test_yolo_world_name(self) -> None:
        """'yolo_world' resolves to YOLOWorldEngine."""
        from inf3_analytics.frame_analytics import get_engine

        engine_cls = get_engine("yolo_world")
        assert engine_cls.__name__ == "YOLOWorldEngine"
