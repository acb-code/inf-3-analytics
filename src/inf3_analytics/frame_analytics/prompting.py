"""Prompt templates and builders for VLM frame analysis.

This module contains versioned prompts for infrastructure inspection
frame analysis. Prompts are designed to extract structured JSON output
from vision-language models.
"""

from typing import Any

from inf3_analytics.types.detection import DetectionType, FrameMeta, Severity
from inf3_analytics.types.event import Event

# Current prompt version - increment when changing prompt content
PROMPT_VERSION = "v2"

# Detection types as string values for prompt
DETECTION_TYPES_LIST = [d.value for d in DetectionType]
SEVERITY_LEVELS = [s.value for s in Severity]

# Standard inspection questions
INSPECTION_QUESTIONS = [
    "Is there evidence of cracking?",
    "Is corrosion or rust visible?",
    "Are there signs of water damage or leaks?",
    "Is there any spalling or material deterioration?",
    "Are there any safety hazards visible?",
    "Is the structural element in good condition?",
]

INSPECTION_QUESTIONS_FR = [
    "Y a-t-il des signes de fissuration ?",
    "La corrosion ou la rouille est-elle visible ?",
    "Y a-t-il des signes de dommages causés par l'eau ou de fuites ?",
    "Y a-t-il de l'écaillage ou de la détérioration du matériau ?",
    "Y a-t-il des risques pour la sécurité visibles ?",
    "L'élément structurel est-il en bon état ?",
]

INSPECTION_QUESTIONS_BY_LANG: dict[str, list[str]] = {
    "en": INSPECTION_QUESTIONS,
    "fr": INSPECTION_QUESTIONS_FR,
}


def build_system_prompt(language: str = "en") -> str:
    """Build the system prompt for VLM analysis.

    Args:
        language: Language code for output

    Returns:
        System prompt string
    """
    prompt = """You are an expert infrastructure inspection analyst with extensive experience in identifying structural anomalies, defects, and safety issues in infrastructure images.

Your task is to analyze inspection images and identify:
- Structural issues (cracks, deformation, damage)
- Material degradation (corrosion, rust, spalling, erosion)
- Water-related issues (leaks, staining, moisture)
- Safety hazards
- Equipment or mechanical issues
- Obstructions or blockages

Be precise and objective. Report what you observe without speculation.
Always output STRICTLY valid JSON matching the provided schema.
Do NOT include markdown formatting, code fences, or explanatory text."""

    if language == "fr":
        prompt += "\n\nIMPORTANT: All text output must be in French (scene summaries, QA answers, detection labels, notes)."

    return prompt


def build_analysis_prompt(
    frame_meta: FrameMeta,
    event: Event | None = None,
    language: str = "en",
) -> str:
    """Build the user prompt for frame analysis.

    Args:
        frame_meta: Metadata about the frame being analyzed
        event: Optional event context from transcript
        language: Language code for output

    Returns:
        Formatted prompt string
    """
    context_lines = [
        f"Frame timestamp: {frame_meta.timestamp_ts} ({frame_meta.timestamp_s:.3f}s)",
    ]

    if event:
        context_lines.append(f"Event type: {event.event_type.value}")
        context_lines.append(f"Event title: {event.title}")
        if event.summary:
            context_lines.append(f"Event context: {event.summary}")

    if frame_meta.transcript_excerpt:
        excerpt = frame_meta.transcript_excerpt
        if len(excerpt) > 300:
            excerpt = excerpt[:297] + "..."
        context_lines.append(f"Inspector audio (transcript): \"{excerpt}\"")

    context_block = "\n".join(context_lines)

    questions = INSPECTION_QUESTIONS_BY_LANG.get(language, INSPECTION_QUESTIONS)
    questions_block = "\n".join(f"- {q}" for q in questions)

    language_instruction = ""
    if language == "fr":
        language_instruction = "\n- All text output (scene_summary, qa answers, detection labels, notes) must be in French"

    return f"""Analyze this infrastructure inspection image.

CONTEXT:
{context_block}

INSPECTION CHECKLIST (answer these):
{questions_block}

OUTPUT REQUIREMENTS:
Return a JSON object with this exact structure:
{{
  "detections": [
    {{
      "type": "one of: {DETECTION_TYPES_LIST}",
      "label": "brief description of the issue",
      "confidence": 0.0 to 1.0,
      "bbox": {{"x": normalized_x, "y": normalized_y, "w": normalized_width, "h": normalized_height}} or null,
      "attributes": {{
        "severity": "low|medium|high" or null,
        "materials": ["list", "of", "materials"] or null,
        "location_hint": "where in the frame" or null,
        "notes": "additional observations" or null
      }}
    }}
  ],
  "scene_summary": "1-2 sentences describing what is visible in the image",
  "qa": [
    {{"q": "question from checklist", "a": "your answer"}}
  ]
}}

IMPORTANT:
- Output ONLY valid JSON, no markdown or extra text
- Include empty detections array [] if no issues found
- Bounding box coordinates should be normalized (0-1) if provided, or null if uncertain
- Be conservative with confidence scores
- Answer all checklist questions in the qa array{language_instruction}"""


def get_json_schema() -> dict[str, Any]:
    """Get the JSON schema for VLM response validation.

    Returns:
        JSON Schema dict for response validation
    """
    return {
        "type": "object",
        "properties": {
            "detections": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "type": {"type": "string", "enum": DETECTION_TYPES_LIST},
                        "label": {"type": "string"},
                        "confidence": {"type": "number", "minimum": 0, "maximum": 1},
                        "bbox": {
                            "oneOf": [
                                {
                                    "type": "object",
                                    "properties": {
                                        "x": {"type": "number"},
                                        "y": {"type": "number"},
                                        "w": {"type": "number"},
                                        "h": {"type": "number"},
                                    },
                                    "required": ["x", "y", "w", "h"],
                                },
                                {"type": "null"},
                            ]
                        },
                        "attributes": {
                            "type": "object",
                            "properties": {
                                "severity": {
                                    "oneOf": [
                                        {"type": "string", "enum": SEVERITY_LEVELS},
                                        {"type": "null"},
                                    ]
                                },
                                "materials": {
                                    "oneOf": [
                                        {"type": "array", "items": {"type": "string"}},
                                        {"type": "null"},
                                    ]
                                },
                                "location_hint": {
                                    "oneOf": [{"type": "string"}, {"type": "null"}]
                                },
                                "notes": {"oneOf": [{"type": "string"}, {"type": "null"}]},
                            },
                        },
                    },
                    "required": ["type", "label", "confidence"],
                },
            },
            "scene_summary": {"type": "string"},
            "qa": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "q": {"type": "string"},
                        "a": {"type": "string"},
                    },
                    "required": ["q", "a"],
                },
            },
        },
        "required": ["detections", "scene_summary", "qa"],
    }


def get_openai_response_format() -> dict[str, Any]:
    """Get OpenAI-compatible response format for structured output.

    Returns:
        Response format dict for OpenAI API
    """
    return {
        "type": "json_schema",
        "json_schema": {
            "name": "frame_analysis",
            "strict": True,
            "schema": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "detections": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "additionalProperties": False,
                            "properties": {
                                "type": {"type": "string", "enum": DETECTION_TYPES_LIST},
                                "label": {"type": "string"},
                                "confidence": {"type": "number"},
                                "bbox": {
                                    "type": ["object", "null"],
                                    "additionalProperties": False,
                                    "properties": {
                                        "x": {"type": "number"},
                                        "y": {"type": "number"},
                                        "w": {"type": "number"},
                                        "h": {"type": "number"},
                                    },
                                    "required": ["x", "y", "w", "h"],
                                },
                                "attributes": {
                                    "type": "object",
                                    "additionalProperties": False,
                                    "properties": {
                                        "severity": {
                                            "type": ["string", "null"],
                                            "enum": [*SEVERITY_LEVELS, None],
                                        },
                                        "materials": {
                                            "type": ["array", "null"],
                                            "items": {"type": "string"},
                                        },
                                        "location_hint": {"type": ["string", "null"]},
                                        "notes": {"type": ["string", "null"]},
                                    },
                                    "required": [
                                        "severity",
                                        "materials",
                                        "location_hint",
                                        "notes",
                                    ],
                                },
                            },
                            "required": ["type", "label", "confidence", "bbox", "attributes"],
                        },
                    },
                    "scene_summary": {"type": "string"},
                    "qa": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "additionalProperties": False,
                            "properties": {
                                "q": {"type": "string"},
                                "a": {"type": "string"},
                            },
                            "required": ["q", "a"],
                        },
                    },
                },
                "required": ["detections", "scene_summary", "qa"],
            },
        },
    }


CONSTRUCTION_SITE_PROMPT_VERSION = "v1"

# Equipment types for construction site prompts
EQUIPMENT_TYPES_LIST = [
    "excavator", "crane", "dump_truck", "concrete_mixer",
    "bulldozer", "loader", "scaffolding", "other",
]
HARDHAT_COLORS_LIST = ["white", "yellow", "orange", "red", "blue", "green", "other"]


def build_construction_site_prompt(
    frame_meta: FrameMeta,
    language: str = "en",
) -> str:
    """Build a VLM prompt for construction site verification.

    Used when VLM verification is requested to classify uncertain detections
    from YOLO-World (e.g., equipment type or hardhat color).

    Args:
        frame_meta: Metadata about the frame being analyzed
        language: Language code for output

    Returns:
        Formatted prompt string
    """
    language_instruction = ""
    if language == "fr":
        language_instruction = "\n- All text output must be in French"

    return f"""Analyze this construction site image taken at {frame_meta.timestamp_ts}.

Count and classify all visible items:

1. EQUIPMENT: For each piece of construction equipment, identify its type from: {EQUIPMENT_TYPES_LIST}
2. PEOPLE: Count all visible people
3. HARDHATS: For each visible hardhat, identify its color from: {HARDHAT_COLORS_LIST}

OUTPUT REQUIREMENTS:
Return a JSON object with this exact structure:
{{
  "detections": [
    {{
      "type": "construction_equipment|person|hardhat",
      "label": "brief description",
      "confidence": 0.0 to 1.0,
      "bbox": {{"x": normalized_x, "y": normalized_y, "w": normalized_width, "h": normalized_height}} or null,
      "attributes": {{
        "equipment_class": "one of {EQUIPMENT_TYPES_LIST}" or null,
        "hardhat_color": "one of {HARDHAT_COLORS_LIST}" or null,
        "notes": "additional observations" or null
      }}
    }}
  ],
  "scene_summary": "1-2 sentences describing the construction site activity"
}}

IMPORTANT:
- Output ONLY valid JSON, no markdown or extra text
- Include empty detections array [] if nothing found
- Bounding box coordinates should be normalized (0-1) if provided
- Be conservative with confidence scores{language_instruction}"""


def build_construction_site_system_prompt(language: str = "en") -> str:
    """Build the system prompt for construction site VLM analysis.

    Args:
        language: Language code for output

    Returns:
        System prompt string
    """
    prompt = """You are an expert construction site analyst specializing in personnel counting, equipment identification, and safety compliance monitoring.

Your task is to analyze construction site images and identify:
- Construction equipment (excavators, cranes, dump trucks, concrete mixers, bulldozers, loaders, scaffolding)
- Personnel (people visible on site)
- Hardhats and their colors (for safety compliance tracking)

Be precise and objective. Report what you observe without speculation.
Always output STRICTLY valid JSON matching the provided schema.
Do NOT include markdown formatting, code fences, or explanatory text."""

    if language == "fr":
        prompt += "\n\nIMPORTANT: All text output must be in French (scene summaries, detection labels, notes)."

    return prompt


def build_repair_prompt(original_response: str, error_message: str) -> str:
    """Build a prompt to repair malformed JSON output.

    Args:
        original_response: The original malformed response
        error_message: The error message from validation

    Returns:
        Repair prompt string
    """
    return f"""The previous response was not valid JSON. Please fix it.

ERROR: {error_message}

ORIGINAL RESPONSE:
{original_response[:1000]}

Please output ONLY the corrected JSON object with this structure:
{{
  "detections": [...],
  "scene_summary": "...",
  "qa": [...]
}}

Output ONLY valid JSON, nothing else."""
