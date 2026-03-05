"""OpenAI VLM engine for frame analytics."""

import base64
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
    get_openai_response_format,
)
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
    QAPair,
    Severity,
)

if TYPE_CHECKING:
    from openai import OpenAI

    from inf3_analytics.types.event import Event

LOGGER = logging.getLogger(__name__)

ENGINE_VERSION = "0.1.0"
DEFAULT_MODEL = "gpt-5-mini"


class CredentialsError(RuntimeError):
    """Raised when API credentials are missing or invalid."""

    pass


class APIError(RuntimeError):
    """Raised when API call fails."""

    pass


def _encode_image_base64(image_path: Path) -> str:
    """Encode image to base64 for API submission."""
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def _get_image_media_type(image_path: Path) -> str:
    """Get media type for image based on extension."""
    suffix = image_path.suffix.lower()
    media_types = {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".gif": "image/gif",
        ".webp": "image/webp",
    }
    return media_types.get(suffix, "image/jpeg")


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

                equipment_class = None
                ec_str = attrs_data.get("equipment_class")
                if ec_str:
                    with contextlib.suppress(ValueError):
                        equipment_class = EquipmentClass(ec_str)

                hardhat_color = None
                hc_str = attrs_data.get("hardhat_color")
                if hc_str:
                    with contextlib.suppress(ValueError):
                        hardhat_color = HardhatColor(hc_str)

                attrs = DetectionAttributes(
                    severity=severity,
                    materials=materials,
                    location_hint=attrs_data.get("location_hint"),
                    notes=attrs_data.get("notes"),
                    equipment_class=equipment_class,
                    hardhat_color=hardhat_color,
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


class OpenAIVLMEngine(BaseFrameAnalyticsEngine):
    """VLM-based frame analytics using OpenAI API.

    Uses GPT-5-mini (or specified model) for vision analysis.
    Requires OPENAI_API_KEY environment variable.
    """

    def __init__(self, config: AnalyticsConfig | None = None) -> None:
        """Initialize the OpenAI VLM engine.

        Args:
            config: Analytics configuration
        """
        super().__init__(config=config or AnalyticsConfig())
        self._client: OpenAI | None = None
        self._model_name = config.model_name if config and config.model_name else DEFAULT_MODEL

    def load(self) -> None:
        """Initialize the OpenAI client.

        Raises:
            CredentialsError: If OPENAI_API_KEY is not set
            ImportError: If openai package is not installed
        """
        if self._loaded:
            return

        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise CredentialsError(
                "OPENAI_API_KEY environment variable is not set. "
                "Get your API key from https://platform.openai.com/api-keys"
            )

        try:
            from openai import OpenAI

            self._client = OpenAI(api_key=api_key)
            self._loaded = True
        except ImportError as e:
            raise ImportError(
                "openai package is not installed. Install with: uv sync --extra openai"
            ) from e

    def unload(self) -> None:
        """Release OpenAI client resources."""
        self._client = None
        self._loaded = False

    def get_engine_info(self) -> EngineInfo:
        """Get engine information for traceability."""
        return EngineInfo(
            name="vlm",
            provider="openai",
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
        """Analyze a single frame using OpenAI Vision API.

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

        # Encode image
        image_b64 = _encode_image_base64(image_path)
        media_type = _get_image_media_type(image_path)

        # Build messages
        messages: list[dict[str, Any]] = [
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:{media_type};base64,{image_b64}",
                            "detail": "high",
                        },
                    },
                    {"type": "text", "text": user_prompt},
                ],
            },
        ]

        # Make API call with retries
        last_error: Exception | None = None
        for attempt in range(self.config.max_retries + 1):
            try:
                # gpt-5* models use max_completion_tokens; older models use max_tokens
                tokens_key = "max_completion_tokens" if self._model_name.startswith("gpt-5") else "max_tokens"
                request_args: dict[str, Any] = {
                    "model": self._model_name,
                    "messages": messages,
                    tokens_key: self.config.max_tokens,
                }

                # gpt-5* models only accept default temperature
                if not self._model_name.startswith("gpt-5"):
                    request_args["temperature"] = self.config.temperature

                # Try with structured output first
                try:
                    request_args["response_format"] = get_openai_response_format()
                    response = self._client.chat.completions.create(**request_args)
                except Exception as e:
                    msg = str(e).lower()
                    if "response_format" in msg or "json_schema" in msg:
                        request_args.pop("response_format", None)
                        response = self._client.chat.completions.create(**request_args)
                    else:
                        raise

                response_text = response.choices[0].message.content or ""
                result = _parse_vlm_response(response_text, frame_meta, engine_info)

                # If parsing failed, try repair
                if result.error and attempt < self.config.max_retries:
                    repair_prompt = build_repair_prompt(response_text, result.error)
                    messages.append({"role": "assistant", "content": response_text})
                    messages.append({"role": "user", "content": repair_prompt})

                    request_args["messages"] = messages
                    request_args.pop("response_format", None)
                    repair_response = self._client.chat.completions.create(**request_args)
                    repair_text = repair_response.choices[0].message.content or ""
                    result = _parse_vlm_response(repair_text, frame_meta, engine_info)

                return result

            except Exception as e:
                last_error = e
                LOGGER.warning(
                    "OpenAI API call failed (attempt %d/%d): %s",
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
