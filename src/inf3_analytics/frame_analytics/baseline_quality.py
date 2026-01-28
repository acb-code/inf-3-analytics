"""Baseline quality metrics engine for frame analytics.

This engine provides deterministic, local image quality metrics
without requiring network access or API calls. It serves as:
- A fallback when VLM engines fail
- A secondary engine for cheap quality checks
- A baseline for testing
"""

import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any

from inf3_analytics.frame_analytics.base import AnalyticsConfig, BaseFrameAnalyticsEngine
from inf3_analytics.types.detection import (
    Detection,
    DetectionAttributes,
    DetectionType,
    EngineInfo,
    FrameAnalyticsResult,
    FrameMeta,
    QAPair,
    Severity,
)

if TYPE_CHECKING:
    from inf3_analytics.types.event import Event

LOGGER = logging.getLogger(__name__)

ENGINE_VERSION = "0.1.0"


class BaselineQualityEngine(BaseFrameAnalyticsEngine):
    """Baseline quality metrics engine using OpenCV/numpy.

    Provides deterministic image quality metrics:
    - Blur detection (Laplacian variance)
    - Brightness analysis
    - Contrast measurement
    - Edge density

    Does not detect infrastructure issues - only image quality.
    Use as fallback or secondary engine.
    """

    def __init__(self, config: AnalyticsConfig | None = None) -> None:
        """Initialize the baseline quality engine.

        Args:
            config: Analytics configuration (most settings unused)
        """
        super().__init__(config=config or AnalyticsConfig())
        self._cv2: Any = None
        self._np: Any = None

    def load(self) -> None:
        """Load OpenCV and numpy.

        Raises:
            ImportError: If opencv-python or numpy is not installed
        """
        if self._loaded:
            return

        try:
            import cv2
            import numpy as np

            self._cv2 = cv2
            self._np = np
            self._loaded = True
        except ImportError as e:
            raise ImportError(
                "opencv-python and numpy are required for baseline quality engine. "
                "Install with: pip install opencv-python numpy"
            ) from e

    def unload(self) -> None:
        """Release resources."""
        self._cv2 = None
        self._np = None
        self._loaded = False

    def get_engine_info(self) -> EngineInfo:
        """Get engine information for traceability."""
        return EngineInfo(
            name="baseline_quality",
            provider=None,
            model=None,
            prompt_version=None,
            version=ENGINE_VERSION,
            config={
                "blur_threshold": 100.0,
                "brightness_low": 40,
                "brightness_high": 220,
                "contrast_low": 30,
            },
        )

    def _compute_blur_score(self, gray: Any) -> float:
        """Compute blur score using Laplacian variance.

        Higher values = sharper image.
        """
        laplacian = self._cv2.Laplacian(gray, self._cv2.CV_64F)
        return float(laplacian.var())

    def _compute_brightness(self, gray: Any) -> float:
        """Compute average brightness (0-255)."""
        return float(self._np.mean(gray))

    def _compute_contrast(self, gray: Any) -> float:
        """Compute contrast as standard deviation of pixel values."""
        return float(self._np.std(gray))

    def _compute_edge_density(self, gray: Any) -> float:
        """Compute edge density using Canny edge detection."""
        edges = self._cv2.Canny(gray, 50, 150)
        total_pixels = edges.shape[0] * edges.shape[1]
        edge_pixels = self._np.count_nonzero(edges)
        return float(edge_pixels / total_pixels)

    def analyze(
        self,
        image_path: Path,
        *,
        event: "Event | None",  # noqa: ARG002
        frame_meta: FrameMeta,
        **kwargs: Any,  # noqa: ARG002
    ) -> FrameAnalyticsResult:
        """Analyze image quality metrics.

        Args:
            image_path: Path to the image file
            event: Optional event context (unused by this engine)
            frame_meta: Frame metadata
            **kwargs: Additional arguments (unused)

        Returns:
            FrameAnalyticsResult with quality-based detections
        """
        if not self._loaded:
            raise RuntimeError("Engine not loaded. Call load() first or use context manager.")

        if not image_path.exists():
            raise FileNotFoundError(f"Image not found: {image_path}")

        engine_info = self.get_engine_info()

        try:
            # Load image
            img = self._cv2.imread(str(image_path))
            if img is None:
                return FrameAnalyticsResult(
                    event_id=frame_meta.event_id,
                    frame_idx=frame_meta.frame_idx,
                    timestamp_s=frame_meta.timestamp_s,
                    timestamp_ts=frame_meta.timestamp_ts,
                    image_path=frame_meta.image_path,
                    engine=engine_info,
                    detections=(),
                    scene_summary="Failed to load image",
                    qa=None,
                    raw_model_output=None,
                    error="Failed to load image with OpenCV",
                )

            # Convert to grayscale
            gray = self._cv2.cvtColor(img, self._cv2.COLOR_BGR2GRAY)

            # Compute metrics
            blur_score = self._compute_blur_score(gray)
            brightness = self._compute_brightness(gray)
            contrast = self._compute_contrast(gray)
            edge_density = self._compute_edge_density(gray)

            # Generate detections based on quality issues
            detections: list[Detection] = []

            # Blur detection
            blur_threshold = 100.0
            if blur_score < blur_threshold:
                severity = Severity.HIGH if blur_score < 50 else Severity.MEDIUM
                detections.append(
                    Detection(
                        detection_type=DetectionType.EQUIPMENT_ISSUE,
                        label="Image blur detected",
                        confidence=min(1.0, (blur_threshold - blur_score) / blur_threshold),
                        bbox=None,
                        attributes=DetectionAttributes(
                            severity=severity,
                            materials=None,
                            location_hint="entire frame",
                            notes=f"Blur score: {blur_score:.1f} (threshold: {blur_threshold})",
                        ),
                    )
                )

            # Brightness issues
            if brightness < 40:
                detections.append(
                    Detection(
                        detection_type=DetectionType.EQUIPMENT_ISSUE,
                        label="Image underexposed (too dark)",
                        confidence=min(1.0, (40 - brightness) / 40),
                        bbox=None,
                        attributes=DetectionAttributes(
                            severity=Severity.MEDIUM,
                            materials=None,
                            location_hint="entire frame",
                            notes=f"Brightness: {brightness:.1f}/255",
                        ),
                    )
                )
            elif brightness > 220:
                detections.append(
                    Detection(
                        detection_type=DetectionType.EQUIPMENT_ISSUE,
                        label="Image overexposed (too bright)",
                        confidence=min(1.0, (brightness - 220) / 35),
                        bbox=None,
                        attributes=DetectionAttributes(
                            severity=Severity.MEDIUM,
                            materials=None,
                            location_hint="entire frame",
                            notes=f"Brightness: {brightness:.1f}/255",
                        ),
                    )
                )

            # Low contrast
            if contrast < 30:
                detections.append(
                    Detection(
                        detection_type=DetectionType.EQUIPMENT_ISSUE,
                        label="Low image contrast",
                        confidence=min(1.0, (30 - contrast) / 30),
                        bbox=None,
                        attributes=DetectionAttributes(
                            severity=Severity.LOW,
                            materials=None,
                            location_hint="entire frame",
                            notes=f"Contrast: {contrast:.1f}",
                        ),
                    )
                )

            # Build scene summary
            quality_issues = []
            if blur_score < blur_threshold:
                quality_issues.append("blurry")
            if brightness < 40:
                quality_issues.append("dark")
            elif brightness > 220:
                quality_issues.append("overexposed")
            if contrast < 30:
                quality_issues.append("low contrast")

            if quality_issues:
                scene_summary = f"Image quality issues detected: {', '.join(quality_issues)}."
            else:
                scene_summary = "Image quality is acceptable for analysis."

            # Build QA pairs
            qa = [
                QAPair(
                    question="Is the image sharp enough for inspection?",
                    answer="No, image is blurry" if blur_score < blur_threshold else "Yes",
                ),
                QAPair(
                    question="Is the lighting adequate?",
                    answer=(
                        "No, too dark"
                        if brightness < 40
                        else "No, too bright" if brightness > 220 else "Yes"
                    ),
                ),
                QAPair(
                    question="Is there sufficient contrast?",
                    answer="No, low contrast" if contrast < 30 else "Yes",
                ),
            ]

            return FrameAnalyticsResult(
                event_id=frame_meta.event_id,
                frame_idx=frame_meta.frame_idx,
                timestamp_s=frame_meta.timestamp_s,
                timestamp_ts=frame_meta.timestamp_ts,
                image_path=frame_meta.image_path,
                engine=engine_info,
                detections=tuple(detections),
                scene_summary=scene_summary,
                qa=tuple(qa),
                raw_model_output={
                    "metrics": {
                        "blur_score": blur_score,
                        "brightness": brightness,
                        "contrast": contrast,
                        "edge_density": edge_density,
                    }
                },
                error=None,
            )

        except Exception as e:
            LOGGER.exception("Error analyzing image: %s", e)
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
                error=f"Analysis failed: {e}",
            )
