"""Gemini VLM engine for frame analytics."""

import contextlib
import json
import logging
import os
import time
from pathlib import Path
from typing import TYPE_CHECKING, Any

from inf3_analytics.frame_analytics.base import AnalyticsConfig, BaseFrameAnalyticsEngine
from inf3_analytics.frame_analytics.prompting import (
    PROMPT_VERSION,
    build_analysis_prompt,
    build_repair_prompt,
    build_system_prompt,
)
from inf3_analytics.types.detection import (
    BoundingBox,
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
DEFAULT_MODEL = "gemini-3-flash-preview"


class CredentialsError(RuntimeError):
    """Raised when API credentials are missing or invalid."""

    pass


class APIError(RuntimeError):
    """Raised when API call fails."""

    pass


def _strip_code_fences(text: str) -> str:
    """Strip markdown code fences from response."""
    cleaned = text.strip()
    if cleaned.startswith("```json"):
        cleaned = cleaned[7:]
    elif cleaned.startswith("```"):
        cleaned = cleaned[3:]
    if cleaned.endswith("```"):
        cleaned = cleaned[:-3]
    return cleaned.strip()


def _parse_vlm_response(
    response_text: str,
    frame_meta: FrameMeta,
    engine_info: EngineInfo,
) -> FrameAnalyticsResult:
    """Parse VLM response into FrameAnalyticsResult.

    Args:
        response_text: Raw response text from VLM
        frame_meta: Frame metadata
        engine_info: Engine information

    Returns:
        FrameAnalyticsResult
    """
    cleaned = _strip_code_fences(response_text)

    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError as e:
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
            raw_model_output={"raw_text": response_text[:500]},
            error=f"JSON parse error: {e}",
        )

    # Parse detections
    detections: list[Detection] = []
    detections_data = data.get("detections", [])
    if isinstance(detections_data, list):
        for d in detections_data:
            try:
                # Parse detection type
                dtype_str = d.get("type", "other")
                try:
                    dtype = DetectionType(dtype_str)
                except ValueError:
                    dtype = DetectionType.OTHER

                # Parse bbox
                bbox = None
                bbox_data = d.get("bbox")
                if bbox_data and isinstance(bbox_data, dict):
                    with contextlib.suppress(KeyError, TypeError, ValueError):
                        bbox = BoundingBox(
                            x=float(bbox_data["x"]),
                            y=float(bbox_data["y"]),
                            w=float(bbox_data["w"]),
                            h=float(bbox_data["h"]),
                        )

                # Parse attributes
                attrs_data = d.get("attributes", {})
                if not isinstance(attrs_data, dict):
                    attrs_data = {}

                severity = None
                sev_str = attrs_data.get("severity")
                if sev_str:
                    with contextlib.suppress(ValueError):
                        severity = Severity(sev_str)

                materials_data = attrs_data.get("materials")
                materials = None
                if materials_data and isinstance(materials_data, list):
                    materials = tuple(str(m) for m in materials_data)

                attrs = DetectionAttributes(
                    severity=severity,
                    materials=materials,
                    location_hint=attrs_data.get("location_hint"),
                    notes=attrs_data.get("notes"),
                )

                # Parse confidence
                confidence = d.get("confidence", 0.5)
                if isinstance(confidence, (int, float)):
                    confidence = max(0.0, min(1.0, float(confidence)))
                else:
                    confidence = 0.5

                detection = Detection(
                    detection_type=dtype,
                    label=str(d.get("label", "")),
                    confidence=confidence,
                    bbox=bbox,
                    attributes=attrs,
                )
                detections.append(detection)
            except (KeyError, TypeError, ValueError) as e:
                LOGGER.warning("Skipping malformed detection: %s", e)
                continue

    # Parse QA pairs
    qa: list[QAPair] = []
    qa_data = data.get("qa", [])
    if isinstance(qa_data, list):
        for q in qa_data:
            if isinstance(q, dict) and "q" in q and "a" in q:
                qa.append(QAPair(question=str(q["q"]), answer=str(q["a"])))

    return FrameAnalyticsResult(
        event_id=frame_meta.event_id,
        frame_idx=frame_meta.frame_idx,
        timestamp_s=frame_meta.timestamp_s,
        timestamp_ts=frame_meta.timestamp_ts,
        image_path=frame_meta.image_path,
        engine=engine_info,
        detections=tuple(detections),
        scene_summary=str(data.get("scene_summary", "")),
        qa=tuple(qa) if qa else None,
        raw_model_output=None,
        error=None,
    )


class GeminiVLMEngine(BaseFrameAnalyticsEngine):
    """VLM-based frame analytics using Google Gemini API.

    Uses Gemini-3-Flash-Preview (or specified model) for vision analysis.
    Requires GEMINI_API_KEY or GOOGLE_API_KEY environment variable.
    """

    def __init__(self, config: AnalyticsConfig | None = None) -> None:
        """Initialize the Gemini VLM engine.

        Args:
            config: Analytics configuration
        """
        super().__init__(config=config or AnalyticsConfig())
        self._client: Any = None
        self._model_name = config.model_name if config and config.model_name else DEFAULT_MODEL

    def load(self) -> None:
        """Initialize the Gemini client.

        Raises:
            CredentialsError: If API key is not set
            ImportError: If google-genai package is not installed
        """
        if self._loaded:
            return

        api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
        if not api_key:
            raise CredentialsError(
                "GEMINI_API_KEY or GOOGLE_API_KEY environment variable is not set. "
                "Get your API key from https://aistudio.google.com/app/apikey"
            )

        try:
            from google import genai

            self._client = genai.Client(api_key=api_key)
            self._loaded = True
        except ImportError as e:
            raise ImportError(
                "google-genai package is not installed. Install with: uv sync --extra gemini"
            ) from e

    def unload(self) -> None:
        """Release Gemini client resources."""
        if self._client is not None:
            with contextlib.suppress(Exception):
                self._client.close()
        self._client = None
        self._loaded = False

    def get_engine_info(self) -> EngineInfo:
        """Get engine information for traceability."""
        return EngineInfo(
            name="vlm",
            provider="gemini",
            model=self._model_name,
            prompt_version=PROMPT_VERSION,
            version=ENGINE_VERSION,
            config=self.config.to_dict(),
        )

    def analyze(
        self,
        image_path: Path,
        *,
        event: "Event | None",
        frame_meta: FrameMeta,
        **kwargs: Any,  # noqa: ARG002
    ) -> FrameAnalyticsResult:
        """Analyze a single frame using Gemini Vision API.

        Args:
            image_path: Path to the image file
            event: Optional event context
            frame_meta: Frame metadata
            **kwargs: Additional engine-specific arguments (unused)

        Returns:
            FrameAnalyticsResult with detections and analysis
        """
        if not self._loaded or self._client is None:
            raise RuntimeError("Engine not loaded. Call load() first or use context manager.")

        if not image_path.exists():
            raise FileNotFoundError(f"Image not found: {image_path}")

        engine_info = self.get_engine_info()
        system_prompt = build_system_prompt(language=self.config.language)
        user_prompt = build_analysis_prompt(frame_meta, event, language=self.config.language)

        # Full prompt combining system and user prompts
        full_prompt = f"{system_prompt}\n\n{user_prompt}"

        # Read image bytes
        with open(image_path, "rb") as f:
            image_bytes = f.read()

        # Determine mime type
        suffix = image_path.suffix.lower()
        mime_types = {
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".png": "image/png",
            ".gif": "image/gif",
            ".webp": "image/webp",
        }
        mime_type = mime_types.get(suffix, "image/jpeg")

        # Make API call with retries
        last_error: Exception | None = None
        for attempt in range(self.config.max_retries + 1):
            try:
                from google.genai import types

                # Build content with image and text
                contents = [
                    types.Part.from_bytes(data=image_bytes, mime_type=mime_type),
                    types.Part.from_text(text=full_prompt),
                ]

                # Try with JSON response format first
                try:
                    response = self._client.models.generate_content(
                        model=self._model_name,
                        contents=contents,
                        config=types.GenerateContentConfig(
                            response_mime_type="application/json",
                            temperature=self.config.temperature,
                            max_output_tokens=self.config.max_tokens,
                        ),
                    )
                except Exception as e:
                    msg = str(e).lower()
                    if "response_mime_type" in msg or "config" in msg:
                        response = self._client.models.generate_content(
                            model=self._model_name,
                            contents=contents,
                        )
                    else:
                        raise

                response_text = response.text or ""
                result = _parse_vlm_response(response_text, frame_meta, engine_info)

                # If parsing failed, try repair
                if result.error and attempt < self.config.max_retries:
                    repair_prompt = build_repair_prompt(response_text, result.error)
                    repair_contents = [
                        types.Part.from_text(text=repair_prompt),
                    ]

                    try:
                        repair_response = self._client.models.generate_content(
                            model=self._model_name,
                            contents=repair_contents,
                            config=types.GenerateContentConfig(
                                response_mime_type="application/json",
                                temperature=0.1,
                            ),
                        )
                    except Exception:
                        repair_response = self._client.models.generate_content(
                            model=self._model_name,
                            contents=repair_contents,
                        )

                    repair_text = repair_response.text or ""
                    result = _parse_vlm_response(repair_text, frame_meta, engine_info)

                return result

            except Exception as e:
                last_error = e
                LOGGER.warning(
                    "Gemini API call failed (attempt %d/%d): %s",
                    attempt + 1,
                    self.config.max_retries + 1,
                    e,
                )
                if attempt < self.config.max_retries:
                    time.sleep(self.config.retry_delay_ms / 1000)

        # All retries failed
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
            error=f"API call failed after {self.config.max_retries + 1} attempts: {last_error}",
        )
