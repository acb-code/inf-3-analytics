"""Tests for SiteVLMEngine (mock-based, no API keys required)."""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from inf3_analytics.frame_analytics.vlm_site import SiteVLMEngine
from inf3_analytics.types.detection import (
    DetectionType,
    EngineInfo,
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


class TestSiteVLMEngineLifecycle:
    """Tests for SiteVLMEngine lifecycle and configuration."""

    def test_default_provider_is_gemini(self) -> None:
        engine = SiteVLMEngine()
        info = engine.get_engine_info()
        assert info.provider == "gemini"

    def test_openai_provider(self) -> None:
        engine = SiteVLMEngine(provider="openai")
        info = engine.get_engine_info()
        assert info.provider == "openai"

    def test_invalid_provider_raises(self) -> None:
        with pytest.raises(ValueError, match="Unsupported provider"):
            SiteVLMEngine(provider="invalid")

    def test_engine_not_loaded_raises(self) -> None:
        engine = SiteVLMEngine()
        assert not engine.is_loaded

        with pytest.raises(RuntimeError, match="not loaded"):
            engine.analyze(
                image_path=Path("/fake/path.jpg"),
                event=None,
                frame_meta=MagicMock(),
            )

    def test_missing_gemini_api_key_raises(self) -> None:
        from inf3_analytics.frame_analytics.vlm_site import CredentialsError

        engine = SiteVLMEngine(provider="gemini")
        with patch.dict("os.environ", {}, clear=True):
            with pytest.raises(CredentialsError):
                engine.load()

    def test_missing_openai_api_key_raises(self) -> None:
        from inf3_analytics.frame_analytics.vlm_site import CredentialsError

        engine = SiteVLMEngine(provider="openai")
        with patch.dict("os.environ", {}, clear=True):
            with pytest.raises(CredentialsError):
                engine.load()

    def test_unload(self) -> None:
        engine = SiteVLMEngine()
        engine._client = MagicMock()
        engine._loaded = True

        engine.unload()
        assert not engine.is_loaded
        assert engine._client is None


class TestSiteVLMEngineInfo:
    """Tests for get_engine_info() metadata."""

    def test_gemini_engine_info(self) -> None:
        engine = SiteVLMEngine(provider="gemini")
        info = engine.get_engine_info()

        assert info.name == "vlm_site"
        assert info.provider == "gemini"
        assert info.model == "gemini-3-flash-preview"
        assert info.prompt_version is not None
        assert info.prompt_version == "v1"

    def test_openai_engine_info(self) -> None:
        engine = SiteVLMEngine(provider="openai")
        info = engine.get_engine_info()

        assert info.name == "vlm_site"
        assert info.provider == "openai"
        assert info.model == "gpt-5-mini"
        assert info.prompt_version == "v1"

    def test_custom_model_in_engine_info(self) -> None:
        from inf3_analytics.frame_analytics import AnalyticsConfig

        config = AnalyticsConfig(model_name="gemini-2.5-flash")
        engine = SiteVLMEngine(config=config, provider="gemini")
        info = engine.get_engine_info()

        assert info.model == "gemini-2.5-flash"


class TestSiteVLMEngineRegistry:
    """Tests for engine registry integration."""

    def test_vlm_site_in_registry(self) -> None:
        from inf3_analytics.frame_analytics import list_engines

        engines = list_engines()
        assert "vlm_site" in engines

    def test_vlm_site_resolves(self) -> None:
        from inf3_analytics.frame_analytics import get_engine

        engine_cls = get_engine("vlm_site")
        assert engine_cls.__name__ == "SiteVLMEngine"

    def test_site_vlm_alias(self) -> None:
        from inf3_analytics.frame_analytics import get_engine

        engine_cls = get_engine("site_vlm")
        assert engine_cls.__name__ == "SiteVLMEngine"


class TestSiteVLMPromptUsage:
    """Tests that construction site prompts are used (not infrastructure prompts)."""

    def test_gemini_uses_construction_prompt(
        self, sample_frame_meta: FrameMeta, tmp_path: Path
    ) -> None:
        """Verify Gemini provider sends construction site prompt."""
        img_path = tmp_path / "test.jpg"
        img_path.write_bytes(b"\xff\xd8\xff\xe0" + b"\x00" * 100)

        # Mock the Gemini client and capture the prompt
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.text = json.dumps({
            "detections": [
                {
                    "type": "construction_equipment",
                    "label": "excavator",
                    "confidence": 0.9,
                    "bbox": None,
                    "attributes": {"equipment_class": "excavator", "notes": None},
                }
            ],
            "scene_summary": "Construction site with excavator",
        })
        mock_client.models.generate_content.return_value = mock_response

        engine = SiteVLMEngine(provider="gemini")
        engine._client = mock_client
        engine._loaded = True

        result = engine.analyze(
            image_path=img_path,
            event=None,
            frame_meta=sample_frame_meta,
        )

        # Verify the prompt content includes construction site terminology
        call_args = mock_client.models.generate_content.call_args
        contents = call_args.kwargs.get("contents") or call_args[1].get("contents")
        # The second part is the text prompt
        prompt_text = contents[1].text if hasattr(contents[1], "text") else str(contents[1])
        assert "construction" in prompt_text.lower() or "equipment" in prompt_text.lower()

        # Verify result parsed correctly
        assert result.error is None
        assert len(result.detections) == 1
        assert result.detections[0].detection_type == DetectionType.CONSTRUCTION_EQUIPMENT
        assert result.detections[0].attributes.equipment_class == EquipmentClass.EXCAVATOR

    def test_openai_uses_construction_prompt(
        self, sample_frame_meta: FrameMeta, tmp_path: Path
    ) -> None:
        """Verify OpenAI provider sends construction site prompt."""
        img_path = tmp_path / "test.jpg"
        img_path.write_bytes(b"\xff\xd8\xff\xe0" + b"\x00" * 100)

        # Mock the OpenAI client
        mock_client = MagicMock()
        mock_message = MagicMock()
        mock_message.content = json.dumps({
            "detections": [
                {
                    "type": "hardhat",
                    "label": "yellow hardhat",
                    "confidence": 0.85,
                    "bbox": {"x": 0.1, "y": 0.2, "w": 0.05, "h": 0.05},
                    "attributes": {"hardhat_color": "yellow", "notes": None},
                }
            ],
            "scene_summary": "Worker wearing yellow hardhat",
        })
        mock_choice = MagicMock()
        mock_choice.message = mock_message
        mock_response = MagicMock()
        mock_response.choices = [mock_choice]
        mock_client.chat.completions.create.return_value = mock_response

        engine = SiteVLMEngine(provider="openai")
        engine._client = mock_client
        engine._loaded = True

        result = engine.analyze(
            image_path=img_path,
            event=None,
            frame_meta=sample_frame_meta,
        )

        # Verify the system prompt includes construction site terminology
        call_args = mock_client.chat.completions.create.call_args
        messages = call_args.kwargs.get("messages") or call_args[1].get("messages")
        system_msg = messages[0]["content"]
        assert "construction" in system_msg.lower()

        # Verify result parsed correctly
        assert result.error is None
        assert len(result.detections) == 1
        assert result.detections[0].detection_type == DetectionType.HARDHAT
        assert result.detections[0].attributes.hardhat_color == HardhatColor.YELLOW


class TestVLMResponseParsingWithConstructionAttrs:
    """Tests that VLM parsers correctly extract construction site attributes."""

    def test_gemini_parser_extracts_equipment_class(self) -> None:
        from inf3_analytics.frame_analytics.vlm_gemini import _parse_vlm_response

        frame_meta = FrameMeta(
            frame_idx=0, timestamp_s=0.0, timestamp_ts="00:00:00,000",
            image_path="test.jpg", event_id="test", event_title=None,
            event_summary=None, transcript_excerpt=None,
        )
        engine_info = EngineInfo(
            name="vlm_site", provider="gemini", model="test",
            prompt_version="v1", version="0.1.0", config={},
        )

        response = json.dumps({
            "detections": [{
                "type": "construction_equipment",
                "label": "crane",
                "confidence": 0.88,
                "bbox": None,
                "attributes": {"equipment_class": "crane", "notes": "tower crane"},
            }],
            "scene_summary": "Crane on site",
            "qa": [],
        })

        result = _parse_vlm_response(response, frame_meta, engine_info)
        assert result.error is None
        assert result.detections[0].attributes.equipment_class == EquipmentClass.CRANE

    def test_openai_parser_extracts_hardhat_color(self) -> None:
        from inf3_analytics.frame_analytics.vlm_openai import _parse_vlm_response

        frame_meta = FrameMeta(
            frame_idx=0, timestamp_s=0.0, timestamp_ts="00:00:00,000",
            image_path="test.jpg", event_id="test", event_title=None,
            event_summary=None, transcript_excerpt=None,
        )
        engine_info = EngineInfo(
            name="vlm_site", provider="openai", model="test",
            prompt_version="v1", version="0.1.0", config={},
        )

        response = json.dumps({
            "detections": [{
                "type": "hardhat",
                "label": "orange hardhat",
                "confidence": 0.92,
                "bbox": None,
                "attributes": {"hardhat_color": "orange", "notes": None},
            }],
            "scene_summary": "Worker with orange hardhat",
            "qa": [],
        })

        result = _parse_vlm_response(response, frame_meta, engine_info)
        assert result.error is None
        assert result.detections[0].attributes.hardhat_color == HardhatColor.ORANGE

    def test_invalid_equipment_class_ignored(self) -> None:
        from inf3_analytics.frame_analytics.vlm_gemini import _parse_vlm_response

        frame_meta = FrameMeta(
            frame_idx=0, timestamp_s=0.0, timestamp_ts="00:00:00,000",
            image_path="test.jpg", event_id="test", event_title=None,
            event_summary=None, transcript_excerpt=None,
        )
        engine_info = EngineInfo(
            name="vlm_site", provider="gemini", model="test",
            prompt_version="v1", version="0.1.0", config={},
        )

        response = json.dumps({
            "detections": [{
                "type": "construction_equipment",
                "label": "forklift",
                "confidence": 0.7,
                "bbox": None,
                "attributes": {"equipment_class": "forklift_invalid", "notes": None},
            }],
            "scene_summary": "Forklift on site",
            "qa": [],
        })

        result = _parse_vlm_response(response, frame_meta, engine_info)
        assert result.error is None
        # Invalid enum value should be suppressed, leaving None
        assert result.detections[0].attributes.equipment_class is None

    def test_backward_compatible_no_construction_attrs(self) -> None:
        """Old infrastructure responses without construction attrs still parse fine."""
        from inf3_analytics.frame_analytics.vlm_openai import _parse_vlm_response

        frame_meta = FrameMeta(
            frame_idx=0, timestamp_s=0.0, timestamp_ts="00:00:00,000",
            image_path="test.jpg", event_id="test", event_title=None,
            event_summary=None, transcript_excerpt=None,
        )
        engine_info = EngineInfo(
            name="vlm", provider="openai", model="gpt-5-mini",
            prompt_version="v2", version="0.1.0", config={},
        )

        response = json.dumps({
            "detections": [{
                "type": "crack",
                "label": "Hairline crack",
                "confidence": 0.85,
                "bbox": None,
                "attributes": {
                    "severity": "medium",
                    "materials": ["concrete"],
                    "location_hint": "upper wall",
                    "notes": None,
                },
            }],
            "scene_summary": "Cracked wall",
            "qa": [{"q": "Is there cracking?", "a": "Yes"}],
        })

        result = _parse_vlm_response(response, frame_meta, engine_info)
        assert result.error is None
        assert result.detections[0].attributes.equipment_class is None
        assert result.detections[0].attributes.hardhat_color is None
        assert result.detections[0].attributes.severity is not None
