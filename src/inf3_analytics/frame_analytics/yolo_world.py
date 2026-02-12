"""YOLO-World engine for construction site object detection."""

import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any

from inf3_analytics.frame_analytics.base import AnalyticsConfig, BaseFrameAnalyticsEngine
from inf3_analytics.types.detection import (
    BoundingBox,
    Detection,
    DetectionAttributes,
    DetectionType,
    EngineInfo,
    EquipmentClass,
    FrameAnalyticsResult,
    FrameMeta,
    HardhatColor,
)

if TYPE_CHECKING:
    from inf3_analytics.types.event import Event

LOGGER = logging.getLogger(__name__)

ENGINE_VERSION = "0.1.0"
DEFAULT_MODEL = "yolov8x-worldv2"

# Default text prompts for YOLO-World zero-shot detection
DEFAULT_CLASSES: tuple[str, ...] = (
    "excavator",
    "crane",
    "dump truck",
    "concrete mixer",
    "bulldozer",
    "loader",
    "scaffolding",
    "person",
    "white hardhat",
    "yellow hardhat",
    "orange hardhat",
    "red hardhat",
    "blue hardhat",
    "green hardhat",
)

# Map YOLO-World class labels to DetectionType + EquipmentClass/HardhatColor
_EQUIPMENT_LABELS: dict[str, EquipmentClass] = {
    "excavator": EquipmentClass.EXCAVATOR,
    "crane": EquipmentClass.CRANE,
    "dump truck": EquipmentClass.DUMP_TRUCK,
    "concrete mixer": EquipmentClass.CONCRETE_MIXER,
    "bulldozer": EquipmentClass.BULLDOZER,
    "loader": EquipmentClass.LOADER,
    "scaffolding": EquipmentClass.SCAFFOLDING,
}

_HARDHAT_LABELS: dict[str, HardhatColor] = {
    "white hardhat": HardhatColor.WHITE,
    "yellow hardhat": HardhatColor.YELLOW,
    "orange hardhat": HardhatColor.ORANGE,
    "red hardhat": HardhatColor.RED,
    "blue hardhat": HardhatColor.BLUE,
    "green hardhat": HardhatColor.GREEN,
}


def _classify_detection(label: str) -> tuple[DetectionType, DetectionAttributes]:
    """Map a YOLO-World class label to DetectionType and attributes.

    Args:
        label: Raw class label from YOLO-World

    Returns:
        Tuple of (DetectionType, DetectionAttributes)
    """
    label_lower = label.lower().strip()

    if label_lower in _EQUIPMENT_LABELS:
        return DetectionType.CONSTRUCTION_EQUIPMENT, DetectionAttributes(
            severity=None,
            materials=None,
            location_hint=None,
            notes=None,
            equipment_class=_EQUIPMENT_LABELS[label_lower],
        )

    if label_lower in _HARDHAT_LABELS:
        return DetectionType.HARDHAT, DetectionAttributes(
            severity=None,
            materials=None,
            location_hint=None,
            notes=None,
            hardhat_color=_HARDHAT_LABELS[label_lower],
        )

    if label_lower == "person":
        return DetectionType.PERSON, DetectionAttributes(
            severity=None, materials=None, location_hint=None, notes=None,
        )

    return DetectionType.OTHER, DetectionAttributes(
        severity=None, materials=None, location_hint=None, notes=label_lower,
    )


class YOLOWorldEngine(BaseFrameAnalyticsEngine):
    """Zero-shot object detection using YOLO-World.

    Uses ultralytics YOLO-World model for open-vocabulary detection
    of construction equipment, personnel, and hardhats. Runs locally
    on GPU (fast) or CPU (slower fallback).

    Install: uv sync --extra yolo
    """

    def __init__(
        self,
        config: AnalyticsConfig | None = None,
        classes: tuple[str, ...] | None = None,
        confidence_threshold: float = 0.15,
        device: str | None = None,
    ) -> None:
        """Initialize the YOLO-World engine.

        Args:
            config: Analytics configuration
            classes: Text prompts for detection classes (default: construction site)
            confidence_threshold: Minimum confidence to keep a detection
            device: Device to run on ("cuda", "cpu", or None for auto-detect)
        """
        super().__init__(config=config or AnalyticsConfig())
        self._classes = classes or DEFAULT_CLASSES
        self._confidence_threshold = confidence_threshold
        self._device = device
        self._model: Any = None
        self._model_name = (
            config.model_name if config and config.model_name else DEFAULT_MODEL
        )

    def load(self) -> None:
        """Load YOLO-World model.

        Raises:
            ImportError: If ultralytics is not installed
        """
        if self._loaded:
            return

        try:
            from ultralytics import YOLO
        except ImportError as e:
            raise ImportError(
                "ultralytics package is not installed. Install with: uv sync --extra yolo"
            ) from e

        self._model = YOLO(self._model_name)
        self._model.set_classes(list(self._classes))
        self._loaded = True
        LOGGER.info(
            "YOLO-World loaded: model=%s, classes=%d, device=%s",
            self._model_name,
            len(self._classes),
            self._device or "auto",
        )

    def unload(self) -> None:
        """Release model resources."""
        self._model = None
        self._loaded = False

    def get_engine_info(self) -> EngineInfo:
        """Get engine information for traceability."""
        return EngineInfo(
            name="yolo_world",
            provider=None,
            model=self._model_name,
            prompt_version=None,
            version=ENGINE_VERSION,
            config={
                **self.config.to_dict(),
                "classes": list(self._classes),
                "confidence_threshold": self._confidence_threshold,
                "device": self._device,
            },
        )

    def analyze(
        self,
        image_path: Path,
        *,
        event: "Event | None",  # noqa: ARG002
        frame_meta: FrameMeta,
        **kwargs: Any,  # noqa: ARG002
    ) -> FrameAnalyticsResult:
        """Detect objects in a single frame using YOLO-World.

        Args:
            image_path: Path to the image file
            event: Optional event context (unused for YOLO)
            frame_meta: Frame metadata
            **kwargs: Additional arguments (unused)

        Returns:
            FrameAnalyticsResult with detections and bounding boxes
        """
        if not self._loaded or self._model is None:
            raise RuntimeError("Engine not loaded. Call load() first or use context manager.")

        if not image_path.exists():
            raise FileNotFoundError(f"Image not found: {image_path}")

        engine_info = self.get_engine_info()

        try:
            # Run inference
            device = self._device or ""
            results = self._model.predict(
                source=str(image_path),
                conf=self._confidence_threshold,
                device=device,
                verbose=False,
            )

            if not results:
                return FrameAnalyticsResult(
                    event_id=frame_meta.event_id,
                    frame_idx=frame_meta.frame_idx,
                    timestamp_s=frame_meta.timestamp_s,
                    timestamp_ts=frame_meta.timestamp_ts,
                    image_path=frame_meta.image_path,
                    engine=engine_info,
                    detections=(),
                    scene_summary="No objects detected",
                    qa=None,
                    raw_model_output=None,
                    error=None,
                )

            result = results[0]
            boxes = result.boxes
            img_h, img_w = result.orig_shape

            detections: list[Detection] = []
            class_names = result.names or {}

            for i in range(len(boxes)):
                conf = float(boxes.conf[i])
                cls_id = int(boxes.cls[i])
                label = class_names.get(cls_id, f"class_{cls_id}")

                # Convert xyxy to normalized xywh
                x1, y1, x2, y2 = boxes.xyxy[i].tolist()
                bbox = BoundingBox(
                    x=x1 / img_w,
                    y=y1 / img_h,
                    w=(x2 - x1) / img_w,
                    h=(y2 - y1) / img_h,
                )

                det_type, attrs = _classify_detection(label)
                detections.append(Detection(
                    detection_type=det_type,
                    label=label,
                    confidence=conf,
                    bbox=bbox,
                    attributes=attrs,
                ))

            # Build scene summary
            type_counts: dict[str, int] = {}
            for d in detections:
                type_counts[d.label] = type_counts.get(d.label, 0) + 1
            summary_parts = [f"{count} {label}" for label, count in type_counts.items()]
            scene_summary = "Detected: " + ", ".join(summary_parts) if summary_parts else "No objects detected"

            return FrameAnalyticsResult(
                event_id=frame_meta.event_id,
                frame_idx=frame_meta.frame_idx,
                timestamp_s=frame_meta.timestamp_s,
                timestamp_ts=frame_meta.timestamp_ts,
                image_path=frame_meta.image_path,
                engine=engine_info,
                detections=tuple(detections),
                scene_summary=scene_summary,
                qa=None,
                raw_model_output=None,
                error=None,
            )

        except Exception as e:
            LOGGER.warning("YOLO-World inference failed: %s", e)
            return FrameAnalyticsResult(
                event_id=frame_meta.event_id,
                frame_idx=frame_meta.frame_idx,
                timestamp_s=frame_meta.timestamp_s,
                timestamp_ts=frame_meta.timestamp_ts,
                image_path=frame_meta.image_path,
                engine=engine_info,
                detections=(),
                scene_summary="",
                qa=None,
                raw_model_output=None,
                error=f"YOLO-World inference failed: {e}",
            )
