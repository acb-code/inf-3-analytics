"""Tests for prompt templates and schema validation."""

import json

import pytest

from inf3_analytics.frame_analytics.prompting import (
    DETECTION_TYPES_LIST,
    INSPECTION_QUESTIONS,
    PROMPT_VERSION,
    SEVERITY_LEVELS,
    build_analysis_prompt,
    build_repair_prompt,
    build_system_prompt,
    get_json_schema,
    get_openai_response_format,
)
from inf3_analytics.types.detection import DetectionType, FrameMeta, Severity
from inf3_analytics.types.event import (
    Event,
    EventMetadata,
    EventSeverity,
    EventType,
    TranscriptReference,
)


class TestPromptConstants:
    """Tests for prompt constants."""

    def test_detection_types_list(self) -> None:
        """Verify detection types list matches enum."""
        assert len(DETECTION_TYPES_LIST) == len(DetectionType)
        for dtype in DetectionType:
            assert dtype.value in DETECTION_TYPES_LIST

    def test_severity_levels(self) -> None:
        """Verify severity levels match enum."""
        assert len(SEVERITY_LEVELS) == len(Severity)
        for sev in Severity:
            assert sev.value in SEVERITY_LEVELS

    def test_prompt_version_format(self) -> None:
        """Verify prompt version is properly formatted."""
        assert PROMPT_VERSION.startswith("v")
        assert len(PROMPT_VERSION) >= 2

    def test_inspection_questions_not_empty(self) -> None:
        """Verify inspection questions are defined."""
        assert len(INSPECTION_QUESTIONS) >= 3
        for q in INSPECTION_QUESTIONS:
            assert q.endswith("?")


class TestSystemPrompt:
    """Tests for system prompt building."""

    def test_system_prompt_content(self) -> None:
        """Verify system prompt contains key instructions."""
        prompt = build_system_prompt()
        assert "infrastructure" in prompt.lower()
        assert "inspection" in prompt.lower()
        assert "JSON" in prompt
        assert "structural" in prompt.lower()

    def test_system_prompt_json_instruction(self) -> None:
        """Verify system prompt instructs JSON output."""
        prompt = build_system_prompt()
        assert "valid JSON" in prompt or "JSON" in prompt
        assert "markdown" in prompt.lower()


class TestAnalysisPrompt:
    """Tests for analysis prompt building."""

    @pytest.fixture
    def sample_frame_meta(self) -> FrameMeta:
        return FrameMeta(
            frame_idx=0,
            timestamp_s=10.5,
            timestamp_ts="00:00:10,500",
            image_path="frames/000.jpg",
            event_id="evt_001",
            event_title="Crack detected",
            event_summary="Visible crack in concrete",
            transcript_excerpt="I can see a crack here near the joint",
        )

    @pytest.fixture
    def sample_event(self) -> Event:
        return Event(
            event_id="evt_001",
            event_type=EventType.STRUCTURAL_ANOMALY,
            severity=EventSeverity.MEDIUM,
            confidence=0.8,
            start_s=10.0,
            end_s=20.0,
            start_ts="00:00:10,000",
            end_ts="00:00:20,000",
            title="Crack detected near joint",
            summary="Inspector observed a visible crack in the concrete near the expansion joint.",
            transcript_ref=TranscriptReference(
                segment_ids=(5, 6),
                excerpt="I can see a crack here near the joint",
                keywords=("crack", "joint", "concrete"),
            ),
            suggested_actions=("Schedule follow-up inspection",),
            metadata=EventMetadata(
                extractor_engine="openai",
                extractor_version="1.0.0",
                created_at="2024-01-15T10:00:00",
                source_transcript_path="transcript.json",
            ),
        )

    def test_prompt_with_frame_meta_only(self, sample_frame_meta: FrameMeta) -> None:
        """Test prompt building with only frame metadata."""
        prompt = build_analysis_prompt(sample_frame_meta, event=None)

        # Check timestamp is included
        assert "00:00:10,500" in prompt
        assert "10.500" in prompt or "10.5" in prompt

        # Check structure
        assert "detections" in prompt
        assert "scene_summary" in prompt
        assert "qa" in prompt

    def test_prompt_with_event_context(
        self, sample_frame_meta: FrameMeta, sample_event: Event
    ) -> None:
        """Test prompt building with event context."""
        prompt = build_analysis_prompt(sample_frame_meta, event=sample_event)

        # Check event context is included
        assert "structural_anomaly" in prompt
        assert "Crack detected" in prompt
        assert "expansion joint" in prompt or sample_event.summary[:20] in prompt

    def test_prompt_with_transcript_excerpt(self, sample_frame_meta: FrameMeta) -> None:
        """Test prompt includes transcript excerpt."""
        prompt = build_analysis_prompt(sample_frame_meta, event=None)
        assert "crack here near the joint" in prompt

    def test_prompt_includes_inspection_questions(self, sample_frame_meta: FrameMeta) -> None:
        """Test prompt includes inspection checklist."""
        prompt = build_analysis_prompt(sample_frame_meta, event=None)
        for q in INSPECTION_QUESTIONS[:3]:  # Check first 3 questions
            assert q in prompt

    def test_prompt_includes_output_schema(self, sample_frame_meta: FrameMeta) -> None:
        """Test prompt includes output schema structure."""
        prompt = build_analysis_prompt(sample_frame_meta, event=None)
        assert '"detections"' in prompt
        assert '"type"' in prompt
        assert '"confidence"' in prompt
        assert '"bbox"' in prompt


class TestRepairPrompt:
    """Tests for repair prompt building."""

    def test_repair_prompt_includes_error(self) -> None:
        """Test repair prompt includes error message."""
        original = '{"detections": [invalid json'
        error = "Expecting value at position 20"
        prompt = build_repair_prompt(original, error)

        assert error in prompt
        assert "fix" in prompt.lower() or "correct" in prompt.lower()

    def test_repair_prompt_includes_original(self) -> None:
        """Test repair prompt includes original response."""
        original = '{"incomplete": true'
        error = "Unexpected end of input"
        prompt = build_repair_prompt(original, error)

        assert "incomplete" in prompt

    def test_repair_prompt_truncates_long_response(self) -> None:
        """Test repair prompt truncates very long original responses."""
        original = "x" * 2000
        error = "Some error"
        prompt = build_repair_prompt(original, error)

        # Should be truncated
        assert len(prompt) < len(original) + 500


class TestJsonSchema:
    """Tests for JSON schema."""

    def test_schema_structure(self) -> None:
        """Test schema has correct structure."""
        schema = get_json_schema()

        assert schema["type"] == "object"
        assert "properties" in schema
        assert "required" in schema

        # Check required fields
        required = schema["required"]
        assert "detections" in required
        assert "scene_summary" in required
        assert "qa" in required

    def test_detections_schema(self) -> None:
        """Test detections array schema."""
        schema = get_json_schema()
        detections = schema["properties"]["detections"]

        assert detections["type"] == "array"
        item_schema = detections["items"]
        assert "type" in item_schema["properties"]
        assert "label" in item_schema["properties"]
        assert "confidence" in item_schema["properties"]

    def test_detection_type_enum(self) -> None:
        """Test detection type enum in schema."""
        schema = get_json_schema()
        type_schema = schema["properties"]["detections"]["items"]["properties"]["type"]

        assert type_schema["enum"] == DETECTION_TYPES_LIST


class TestOpenAIResponseFormat:
    """Tests for OpenAI response format."""

    def test_format_structure(self) -> None:
        """Test OpenAI format has correct structure."""
        fmt = get_openai_response_format()

        assert fmt["type"] == "json_schema"
        assert "json_schema" in fmt
        assert fmt["json_schema"]["name"] == "frame_analysis"
        assert fmt["json_schema"]["strict"] is True

    def test_schema_is_valid_json(self) -> None:
        """Test schema can be serialized to JSON."""
        fmt = get_openai_response_format()
        # Should not raise
        json_str = json.dumps(fmt)
        assert len(json_str) > 100

    def test_schema_has_required_fields(self) -> None:
        """Test schema includes all required fields."""
        fmt = get_openai_response_format()
        schema = fmt["json_schema"]["schema"]

        props = schema["properties"]
        assert "detections" in props
        assert "scene_summary" in props
        assert "qa" in props

    def test_detection_item_schema(self) -> None:
        """Test detection item has correct schema."""
        fmt = get_openai_response_format()
        detection_schema = fmt["json_schema"]["schema"]["properties"]["detections"]["items"]

        props = detection_schema["properties"]
        assert "type" in props
        assert "label" in props
        assert "confidence" in props
        assert "bbox" in props
        assert "attributes" in props

    def test_severity_enum_includes_null(self) -> None:
        """Test severity enum allows null value."""
        fmt = get_openai_response_format()
        attrs_schema = fmt["json_schema"]["schema"]["properties"]["detections"]["items"][
            "properties"
        ]["attributes"]
        severity_schema = attrs_schema["properties"]["severity"]

        # Should allow null
        assert "null" in str(severity_schema["type"]) or None in severity_schema.get("enum", [])
