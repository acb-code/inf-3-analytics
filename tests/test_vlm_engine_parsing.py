"""Tests for VLM engine response parsing.

These tests validate parsing and normalization of VLM outputs
without making actual API calls.
"""

import json
from unittest.mock import MagicMock, patch

import pytest

from inf3_analytics.frame_analytics.vlm_openai import _parse_vlm_response, _strip_code_fences
from inf3_analytics.types.detection import (
    DetectionType,
    EngineInfo,
    FrameMeta,
    Severity,
)


@pytest.fixture
def sample_frame_meta() -> FrameMeta:
    """Create sample frame metadata for tests."""
    return FrameMeta(
        frame_idx=0,
        timestamp_s=10.5,
        timestamp_ts="00:00:10,500",
        image_path="frames/000.jpg",
        event_id="evt_001",
        event_title="Test event",
        event_summary=None,
        transcript_excerpt=None,
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


class TestStripCodeFences:
    """Tests for code fence stripping."""

    def test_strip_json_fence(self) -> None:
        text = '```json\n{"key": "value"}\n```'
        result = _strip_code_fences(text)
        assert result == '{"key": "value"}'

    def test_strip_plain_fence(self) -> None:
        text = '```\n{"key": "value"}\n```'
        result = _strip_code_fences(text)
        assert result == '{"key": "value"}'

    def test_no_fence(self) -> None:
        text = '{"key": "value"}'
        result = _strip_code_fences(text)
        assert result == '{"key": "value"}'

    def test_whitespace_handling(self) -> None:
        text = '  ```json\n{"key": "value"}\n```  '
        result = _strip_code_fences(text)
        assert result == '{"key": "value"}'


class TestParseVLMResponse:
    """Tests for VLM response parsing."""

    def test_parse_valid_response(
        self, sample_frame_meta: FrameMeta, sample_engine_info: EngineInfo
    ) -> None:
        """Test parsing a valid VLM response."""
        response = json.dumps({
            "detections": [
                {
                    "type": "crack",
                    "label": "Hairline crack in concrete",
                    "confidence": 0.85,
                    "bbox": {"x": 0.2, "y": 0.3, "w": 0.1, "h": 0.05},
                    "attributes": {
                        "severity": "medium",
                        "materials": ["concrete"],
                        "location_hint": "upper left",
                        "notes": "Near expansion joint",
                    },
                }
            ],
            "scene_summary": "Concrete surface with visible crack near joint",
            "qa": [
                {"q": "Is there cracking?", "a": "Yes, hairline crack visible"},
                {"q": "Is corrosion present?", "a": "No"},
            ],
        })

        result = _parse_vlm_response(response, sample_frame_meta, sample_engine_info)

        assert result.error is None
        assert len(result.detections) == 1
        assert result.detections[0].detection_type == DetectionType.CRACK
        assert result.detections[0].confidence == 0.85
        assert result.detections[0].bbox is not None
        assert result.detections[0].attributes.severity == Severity.MEDIUM
        assert result.scene_summary == "Concrete surface with visible crack near joint"
        assert result.qa is not None
        assert len(result.qa) == 2

    def test_parse_empty_detections(
        self, sample_frame_meta: FrameMeta, sample_engine_info: EngineInfo
    ) -> None:
        """Test parsing response with no detections."""
        response = json.dumps({
            "detections": [],
            "scene_summary": "Clean concrete surface, no issues visible",
            "qa": [{"q": "Is there cracking?", "a": "No"}],
        })

        result = _parse_vlm_response(response, sample_frame_meta, sample_engine_info)

        assert result.error is None
        assert len(result.detections) == 0
        assert "no issues" in result.scene_summary.lower()

    def test_parse_multiple_detections(
        self, sample_frame_meta: FrameMeta, sample_engine_info: EngineInfo
    ) -> None:
        """Test parsing multiple detections."""
        response = json.dumps({
            "detections": [
                {
                    "type": "crack",
                    "label": "Crack 1",
                    "confidence": 0.9,
                    "bbox": None,
                    "attributes": {"severity": "high", "materials": None, "location_hint": None, "notes": None},
                },
                {
                    "type": "corrosion",
                    "label": "Surface rust",
                    "confidence": 0.7,
                    "bbox": None,
                    "attributes": {"severity": "low", "materials": ["steel"], "location_hint": None, "notes": None},
                },
            ],
            "scene_summary": "Multiple issues found",
            "qa": [],
        })

        result = _parse_vlm_response(response, sample_frame_meta, sample_engine_info)

        assert result.error is None
        assert len(result.detections) == 2
        assert result.detections[0].detection_type == DetectionType.CRACK
        assert result.detections[1].detection_type == DetectionType.CORROSION

    def test_parse_with_code_fences(
        self, sample_frame_meta: FrameMeta, sample_engine_info: EngineInfo
    ) -> None:
        """Test parsing response wrapped in code fences."""
        response = '```json\n{"detections": [], "scene_summary": "Test", "qa": []}\n```'

        result = _parse_vlm_response(response, sample_frame_meta, sample_engine_info)

        assert result.error is None
        assert result.scene_summary == "Test"

    def test_parse_invalid_json(
        self, sample_frame_meta: FrameMeta, sample_engine_info: EngineInfo
    ) -> None:
        """Test parsing invalid JSON returns error result."""
        response = '{"detections": [invalid json'

        result = _parse_vlm_response(response, sample_frame_meta, sample_engine_info)

        assert result.error is not None
        assert "JSON" in result.error or "parse" in result.error.lower()
        assert len(result.detections) == 0

    def test_parse_unknown_detection_type(
        self, sample_frame_meta: FrameMeta, sample_engine_info: EngineInfo
    ) -> None:
        """Test unknown detection type defaults to OTHER."""
        response = json.dumps({
            "detections": [
                {
                    "type": "unknown_type",
                    "label": "Something",
                    "confidence": 0.5,
                    "bbox": None,
                    "attributes": {},
                }
            ],
            "scene_summary": "Test",
            "qa": [],
        })

        result = _parse_vlm_response(response, sample_frame_meta, sample_engine_info)

        assert result.error is None
        assert len(result.detections) == 1
        assert result.detections[0].detection_type == DetectionType.OTHER

    def test_parse_confidence_clamping(
        self, sample_frame_meta: FrameMeta, sample_engine_info: EngineInfo
    ) -> None:
        """Test confidence values are clamped to 0-1 range."""
        response = json.dumps({
            "detections": [
                {
                    "type": "crack",
                    "label": "High confidence",
                    "confidence": 1.5,  # Should be clamped to 1.0
                    "bbox": None,
                    "attributes": {},
                },
                {
                    "type": "crack",
                    "label": "Low confidence",
                    "confidence": -0.5,  # Should be clamped to 0.0
                    "bbox": None,
                    "attributes": {},
                },
            ],
            "scene_summary": "Test",
            "qa": [],
        })

        result = _parse_vlm_response(response, sample_frame_meta, sample_engine_info)

        assert result.detections[0].confidence == 1.0
        assert result.detections[1].confidence == 0.0

    def test_parse_null_bbox(
        self, sample_frame_meta: FrameMeta, sample_engine_info: EngineInfo
    ) -> None:
        """Test null bounding box is handled correctly."""
        response = json.dumps({
            "detections": [
                {
                    "type": "leak",
                    "label": "Water stain",
                    "confidence": 0.6,
                    "bbox": None,
                    "attributes": {},
                }
            ],
            "scene_summary": "Test",
            "qa": [],
        })

        result = _parse_vlm_response(response, sample_frame_meta, sample_engine_info)

        assert result.detections[0].bbox is None

    def test_parse_invalid_bbox_ignored(
        self, sample_frame_meta: FrameMeta, sample_engine_info: EngineInfo
    ) -> None:
        """Test invalid bounding box is ignored (set to None)."""
        response = json.dumps({
            "detections": [
                {
                    "type": "crack",
                    "label": "Crack",
                    "confidence": 0.8,
                    "bbox": {"x": "invalid", "y": 0.1},  # Invalid
                    "attributes": {},
                }
            ],
            "scene_summary": "Test",
            "qa": [],
        })

        result = _parse_vlm_response(response, sample_frame_meta, sample_engine_info)

        # Should still parse, bbox should be None due to error
        assert len(result.detections) == 1
        assert result.detections[0].bbox is None

    def test_parse_materials_list(
        self, sample_frame_meta: FrameMeta, sample_engine_info: EngineInfo
    ) -> None:
        """Test materials list is parsed correctly."""
        response = json.dumps({
            "detections": [
                {
                    "type": "corrosion",
                    "label": "Rust",
                    "confidence": 0.75,
                    "bbox": None,
                    "attributes": {
                        "severity": None,
                        "materials": ["steel", "iron"],
                        "location_hint": None,
                        "notes": None,
                    },
                }
            ],
            "scene_summary": "Test",
            "qa": [],
        })

        result = _parse_vlm_response(response, sample_frame_meta, sample_engine_info)

        assert result.detections[0].attributes.materials == ("steel", "iron")

    def test_parse_empty_qa(
        self, sample_frame_meta: FrameMeta, sample_engine_info: EngineInfo
    ) -> None:
        """Test empty QA array results in empty tuple."""
        response = json.dumps({
            "detections": [],
            "scene_summary": "Test",
            "qa": [],
        })

        result = _parse_vlm_response(response, sample_frame_meta, sample_engine_info)

        # Empty QA should be None or empty tuple
        assert result.qa is None or len(result.qa) == 0

    def test_parse_malformed_detection_handled(
        self, sample_frame_meta: FrameMeta, sample_engine_info: EngineInfo
    ) -> None:
        """Test malformed detection is handled gracefully with defaults."""
        response = json.dumps({
            "detections": [
                {"type": "crack", "label": "Valid", "confidence": 0.8, "bbox": None, "attributes": {}},
                {"missing_required_fields": True},  # Malformed - will use defaults
                {"type": "leak", "label": "Also valid", "confidence": 0.6, "bbox": None, "attributes": {}},
            ],
            "scene_summary": "Test",
            "qa": [],
        })

        result = _parse_vlm_response(response, sample_frame_meta, sample_engine_info)

        # Parser is lenient - malformed detection uses defaults (type=other)
        assert len(result.detections) == 3
        assert result.detections[0].detection_type == DetectionType.CRACK
        assert result.detections[1].detection_type == DetectionType.OTHER  # Default
        assert result.detections[2].detection_type == DetectionType.LEAK

    def test_frame_meta_preserved(
        self, sample_frame_meta: FrameMeta, sample_engine_info: EngineInfo
    ) -> None:
        """Test frame metadata is preserved in result."""
        response = json.dumps({
            "detections": [],
            "scene_summary": "Test",
            "qa": [],
        })

        result = _parse_vlm_response(response, sample_frame_meta, sample_engine_info)

        assert result.event_id == sample_frame_meta.event_id
        assert result.frame_idx == sample_frame_meta.frame_idx
        assert result.timestamp_s == sample_frame_meta.timestamp_s
        assert result.timestamp_ts == sample_frame_meta.timestamp_ts
        assert result.image_path == sample_frame_meta.image_path


class TestOpenAIVLMEngineIntegration:
    """Integration tests for OpenAI VLM engine (mocked)."""

    def test_engine_not_loaded_raises(self) -> None:
        """Test analyze raises if engine not loaded."""
        from inf3_analytics.frame_analytics.vlm_openai import OpenAIVLMEngine

        engine = OpenAIVLMEngine()
        # Don't call load()

        with pytest.raises(RuntimeError, match="not loaded"):
            engine.analyze(
                image_path=MagicMock(),
                event=None,
                frame_meta=MagicMock(),
            )

    def test_missing_api_key_raises(self) -> None:
        """Test load raises without API key."""
        from inf3_analytics.frame_analytics.vlm_openai import CredentialsError, OpenAIVLMEngine

        engine = OpenAIVLMEngine()

        with patch.dict("os.environ", {}, clear=True):
            with pytest.raises(CredentialsError):
                engine.load()

    def test_get_engine_info(self) -> None:
        """Test engine info is correct."""
        from inf3_analytics.frame_analytics import AnalyticsConfig
        from inf3_analytics.frame_analytics.vlm_openai import OpenAIVLMEngine

        config = AnalyticsConfig(model_name="gpt-5-mini")
        engine = OpenAIVLMEngine(config=config)

        info = engine.get_engine_info()

        assert info.name == "vlm"
        assert info.provider == "openai"
        assert info.model == "gpt-5-mini"
        assert info.prompt_version is not None


class TestGeminiVLMEngineIntegration:
    """Integration tests for Gemini VLM engine (mocked)."""

    def test_engine_not_loaded_raises(self) -> None:
        """Test analyze raises if engine not loaded."""
        from inf3_analytics.frame_analytics.vlm_gemini import GeminiVLMEngine

        engine = GeminiVLMEngine()

        with pytest.raises(RuntimeError, match="not loaded"):
            engine.analyze(
                image_path=MagicMock(),
                event=None,
                frame_meta=MagicMock(),
            )

    def test_missing_api_key_raises(self) -> None:
        """Test load raises without API key."""
        from inf3_analytics.frame_analytics.vlm_gemini import CredentialsError, GeminiVLMEngine

        engine = GeminiVLMEngine()

        with patch.dict("os.environ", {}, clear=True):
            with pytest.raises(CredentialsError):
                engine.load()

    def test_get_engine_info(self) -> None:
        """Test engine info is correct."""
        from inf3_analytics.frame_analytics import AnalyticsConfig
        from inf3_analytics.frame_analytics.vlm_gemini import GeminiVLMEngine

        config = AnalyticsConfig(model_name="gemini-3-flash-preview")
        engine = GeminiVLMEngine(config=config)

        info = engine.get_engine_info()

        assert info.name == "vlm"
        assert info.provider == "gemini"
        assert info.model == "gemini-3-flash-preview"
