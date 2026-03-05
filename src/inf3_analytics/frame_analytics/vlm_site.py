"""VLM-only engine for construction site analytics.

Uses Gemini or OpenAI vision-language models with construction site
prompts for equipment, personnel, and hardhat detection.
"""

import contextlib
import logging
import os
import time
from pathlib import Path
from typing import TYPE_CHECKING, Any

from inf3_analytics.frame_analytics.base import AnalyticsConfig, BaseFrameAnalyticsEngine
from inf3_analytics.frame_analytics.prompting import (
    CONSTRUCTION_SITE_PROMPT_VERSION,
    build_construction_site_prompt,
    build_construction_site_system_prompt,
    build_repair_prompt,
)
from inf3_analytics.types.detection import (
    EngineInfo,
    FrameAnalyticsResult,
    FrameMeta,
)

if TYPE_CHECKING:
    from inf3_analytics.types.event import Event

LOGGER = logging.getLogger(__name__)

ENGINE_VERSION = "0.1.0"

DEFAULT_GEMINI_MODEL = "gemini-3-flash-preview"
DEFAULT_OPENAI_MODEL = "gpt-5-mini"


class CredentialsError(RuntimeError):
    """Raised when API credentials are missing or invalid."""

    pass


class SiteVLMEngine(BaseFrameAnalyticsEngine):
    """VLM-based construction site analytics engine.

    Sends each frame to a vision-language model with construction site
    prompts for equipment, personnel, and hardhat detection. Supports
    Gemini (default) or OpenAI as the provider.

    This is an alternative to the YOLO-World engine for users without
    a GPU, or who want higher semantic accuracy.
    """

    def __init__(
        self,
        config: AnalyticsConfig | None = None,
        provider: str = "gemini",
    ) -> None:
        """Initialize the site VLM engine.

        Args:
            config: Analytics configuration
            provider: API provider ("gemini" or "openai")
        """
        super().__init__(config=config or AnalyticsConfig())
        if provider not in ("gemini", "openai"):
            raise ValueError(f"Unsupported provider: {provider}. Use 'gemini' or 'openai'.")
        self._provider = provider
        self._client: Any = None

        default_model = DEFAULT_GEMINI_MODEL if provider == "gemini" else DEFAULT_OPENAI_MODEL
        self._model_name = (
            config.model_name if config and config.model_name else default_model
        )

    def load(self) -> None:
        """Initialize the API client.

        Raises:
            CredentialsError: If API key is not set
            ImportError: If required package is not installed
        """
        if self._loaded:
            return

        if self._provider == "gemini":
            api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
            if not api_key:
                raise CredentialsError(
                    "GEMINI_API_KEY or GOOGLE_API_KEY environment variable is not set. "
                    "Get your API key from https://aistudio.google.com/app/apikey"
                )
            try:
                from google import genai

                self._client = genai.Client(api_key=api_key)
            except ImportError as e:
                raise ImportError(
                    "google-genai package is not installed. Install with: uv sync --extra gemini"
                ) from e
        else:
            api_key = os.environ.get("OPENAI_API_KEY")
            if not api_key:
                raise CredentialsError(
                    "OPENAI_API_KEY environment variable is not set. "
                    "Get your API key from https://platform.openai.com/api-keys"
                )
            try:
                from openai import OpenAI

                self._client = OpenAI(api_key=api_key)
            except ImportError as e:
                raise ImportError(
                    "openai package is not installed. Install with: uv sync --extra openai"
                ) from e

        self._loaded = True

    def unload(self) -> None:
        """Release API client resources."""
        if self._provider == "gemini" and self._client is not None:
            with contextlib.suppress(Exception):
                self._client.close()
        self._client = None
        self._loaded = False

    def get_engine_info(self) -> EngineInfo:
        """Get engine information for traceability."""
        return EngineInfo(
            name="vlm_site",
            provider=self._provider,
            model=self._model_name,
            prompt_version=CONSTRUCTION_SITE_PROMPT_VERSION,
            version=ENGINE_VERSION,
            config=self.config.to_dict(),
        )

    def analyze(
        self,
        image_path: Path,
        *,
        event: "Event | None",  # noqa: ARG002
        frame_meta: FrameMeta,
        **kwargs: Any,  # noqa: ARG002
    ) -> FrameAnalyticsResult:
        """Analyze a single frame using VLM with construction site prompts.

        Args:
            image_path: Path to the image file
            event: Optional event context (unused)
            frame_meta: Frame metadata
            **kwargs: Additional arguments (unused)

        Returns:
            FrameAnalyticsResult with detections and analysis
        """
        if not self._loaded or self._client is None:
            raise RuntimeError("Engine not loaded. Call load() first or use context manager.")

        if not image_path.exists():
            raise FileNotFoundError(f"Image not found: {image_path}")

        engine_info = self.get_engine_info()
        system_prompt = build_construction_site_system_prompt(language=self.config.language)
        user_prompt = build_construction_site_prompt(frame_meta, language=self.config.language)

        if self._provider == "gemini":
            return self._analyze_gemini(
                image_path, system_prompt, user_prompt, frame_meta, engine_info
            )
        else:
            return self._analyze_openai(
                image_path, system_prompt, user_prompt, frame_meta, engine_info
            )

    def _analyze_gemini(
        self,
        image_path: Path,
        system_prompt: str,
        user_prompt: str,
        frame_meta: FrameMeta,
        engine_info: EngineInfo,
    ) -> FrameAnalyticsResult:
        """Run analysis via Gemini API."""
        from inf3_analytics.frame_analytics.vlm_gemini import _parse_vlm_response

        full_prompt = f"{system_prompt}\n\n{user_prompt}"

        with open(image_path, "rb") as f:
            image_bytes = f.read()

        suffix = image_path.suffix.lower()
        mime_types = {
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".png": "image/png",
            ".gif": "image/gif",
            ".webp": "image/webp",
        }
        mime_type = mime_types.get(suffix, "image/jpeg")

        last_error: Exception | None = None
        for attempt in range(self.config.max_retries + 1):
            try:
                from google.genai import types

                contents = [
                    types.Part.from_bytes(data=image_bytes, mime_type=mime_type),
                    types.Part.from_text(text=full_prompt),
                ]

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

                if result.error and attempt < self.config.max_retries:
                    repair_prompt = build_repair_prompt(response_text, result.error)
                    repair_contents = [types.Part.from_text(text=repair_prompt)]
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
                    attempt + 1, self.config.max_retries + 1, e,
                )
                if attempt < self.config.max_retries:
                    time.sleep(self.config.retry_delay_ms / 1000)

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

    def _analyze_openai(
        self,
        image_path: Path,
        system_prompt: str,
        user_prompt: str,
        frame_meta: FrameMeta,
        engine_info: EngineInfo,
    ) -> FrameAnalyticsResult:
        """Run analysis via OpenAI API."""
        from inf3_analytics.frame_analytics.vlm_openai import (
            _encode_image_base64,
            _get_image_media_type,
            _parse_vlm_response,
        )

        image_b64 = _encode_image_base64(image_path)
        media_type = _get_image_media_type(image_path)

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

                if not self._model_name.startswith("gpt-5"):
                    request_args["temperature"] = self.config.temperature

                response = self._client.chat.completions.create(**request_args)
                response_text = response.choices[0].message.content or ""
                result = _parse_vlm_response(response_text, frame_meta, engine_info)

                if result.error and attempt < self.config.max_retries:
                    repair_prompt = build_repair_prompt(response_text, result.error)
                    messages.append({"role": "assistant", "content": response_text})
                    messages.append({"role": "user", "content": repair_prompt})
                    request_args["messages"] = messages
                    repair_response = self._client.chat.completions.create(**request_args)
                    repair_text = repair_response.choices[0].message.content or ""
                    result = _parse_vlm_response(repair_text, frame_meta, engine_info)

                return result

            except Exception as e:
                last_error = e
                LOGGER.warning(
                    "OpenAI API call failed (attempt %d/%d): %s",
                    attempt + 1, self.config.max_retries + 1, e,
                )
                if attempt < self.config.max_retries:
                    time.sleep(self.config.retry_delay_ms / 1000)

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
