"""LLM-based event extraction using cloud APIs."""

import hashlib
import json
import os
from datetime import datetime
from typing import TYPE_CHECKING, Any

from inf3_analytics.engines.event_extraction.base import (
    BaseEventExtractionEngine,
    EventExtractionConfig,
)
from inf3_analytics.types.event import (
    Event,
    EventMetadata,
    EventSeverity,
    EventType,
    RuleEventCorrelation,
    TranscriptReference,
)
from inf3_analytics.types.transcript import Segment, Transcript
from inf3_analytics.utils.time import seconds_to_timestamp

if TYPE_CHECKING:
    from openai import OpenAI

# Engine version for metadata
ENGINE_VERSION = "1.0.0"

# Event types as string values for LLM prompt
EVENT_TYPES_LIST = [e.value for e in EventType]


class CredentialsError(RuntimeError):
    """Raised when API credentials are missing or invalid."""

    pass


class APIError(RuntimeError):
    """Raised when API call fails."""

    pass


def _build_extraction_prompt(
    segments: list[Segment],
    rule_events: tuple[Event, ...] | None = None,
) -> str:
    """Build prompt for event extraction.

    Args:
        segments: Segments to analyze
        rule_events: Optional rule-based events for correlation

    Returns:
        Formatted prompt string
    """
    segment_text = "\n".join(
        f"[Segment {seg.id}] ({seg.start_ts} - {seg.end_ts}): {seg.text}"
        for seg in segments
    )

    rule_events_text = ""
    if rule_events:
        rule_events_text = "\n\nRULE-BASED EVENTS ALREADY DETECTED:\n"
        rule_events_text += "\n".join(
            f"- [{e.event_id}] {e.event_type.value}: \"{e.title}\" "
            f"({e.start_ts}-{e.end_ts}, confidence: {e.confidence:.0%})"
            for e in rule_events
        )
        rule_events_text += "\n\nFor each event you extract, identify which rule-based events (if any) describe the same finding."

    return f"""You are an infrastructure inspection analyst. Analyze this transcript and extract significant events.

TRANSCRIPT:
{segment_text}
{rule_events_text}

Extract events matching these types: {EVENT_TYPES_LIST}

For each event found, return a JSON object with:
- "event_type": one of {EVENT_TYPES_LIST}
- "severity": "low", "medium", or "high" (or null if unclear)
- "confidence": number 0.0-1.0 based on how certain you are
- "segment_ids": array of segment IDs this event spans
- "title": short descriptive title (5-10 words)
- "summary": 1-3 sentence description of the finding
- "keywords": array of relevant keywords from the text
- "suggested_actions": array of recommended follow-up actions (or null)
- "related_rule_event_ids": array of rule event IDs that describe the same finding (empty if none)
- "correlation_reason": why these rule events are related (or null if none)

Return ONLY a valid JSON array of event objects. No markdown, no explanation.
Focus on significant findings: structural issues, safety concerns, maintenance needs, and measurements.
Avoid extracting trivial location references or routine observations unless they're significant."""


def _parse_llm_response(
    response_text: str,
    segments: list[Segment],
    engine_name: str,
    model_name: str,
    source_path: str | None,
    rule_events: tuple[Event, ...] | None = None,
) -> list[Event]:
    """Parse LLM response into Event objects.

    Args:
        response_text: Raw LLM response text
        segments: Source segments for reference
        engine_name: Name of the LLM engine
        model_name: Model name used
        source_path: Source transcript path
        rule_events: Rule-based events for correlation lookup

    Returns:
        List of Event objects
    """
    # Clean response text - remove markdown code blocks if present
    text = response_text.strip()
    if text.startswith("```json"):
        text = text[7:]
    if text.startswith("```"):
        text = text[3:]
    if text.endswith("```"):
        text = text[:-3]
    text = text.strip()

    try:
        events_data = json.loads(text)
    except json.JSONDecodeError as e:
        raise APIError(f"Failed to parse LLM response as JSON: {e}\nResponse: {text[:500]}")

    if not isinstance(events_data, list):
        raise APIError(f"Expected JSON array, got: {type(events_data)}")

    segment_by_id = {s.id: s for s in segments}
    rule_events_by_id = {e.event_id: e for e in rule_events} if rule_events else {}
    now = datetime.now().isoformat()

    events: list[Event] = []
    for idx, data in enumerate(events_data):
        try:
            # Parse event type
            event_type_str = data.get("event_type", "other")
            try:
                event_type = EventType(event_type_str)
            except ValueError:
                event_type = EventType.OTHER

            # Parse severity
            severity_str = data.get("severity")
            severity = None
            if severity_str:
                try:
                    severity = EventSeverity(severity_str)
                except ValueError:
                    pass

            # Parse segment IDs and get timing
            segment_ids = data.get("segment_ids", [])
            if not segment_ids:
                continue  # Skip events without segments

            # Ensure segment IDs are valid
            valid_segment_ids = [sid for sid in segment_ids if sid in segment_by_id]
            if not valid_segment_ids:
                continue

            ref_segments = [segment_by_id[sid] for sid in valid_segment_ids]
            start_s = min(s.start_s for s in ref_segments)
            end_s = max(s.end_s for s in ref_segments)

            # Generate excerpt from referenced segments
            excerpt = " ".join(s.text for s in ref_segments)
            if len(excerpt) > 200:
                excerpt = excerpt[:197] + "..."

            # Parse keywords
            keywords_data = data.get("keywords", [])
            keywords = tuple(str(k) for k in keywords_data) if keywords_data else None

            # Parse suggested actions
            actions_data = data.get("suggested_actions")
            suggested_actions = None
            if actions_data and isinstance(actions_data, list):
                suggested_actions = tuple(str(a) for a in actions_data)

            # Parse correlation with rule events
            related_rule_events = None
            related_ids = data.get("related_rule_event_ids", [])
            correlation_reason = data.get("correlation_reason")
            if related_ids:
                # Validate that referenced rule events exist
                valid_related_ids = [rid for rid in related_ids if rid in rule_events_by_id]
                if valid_related_ids:
                    # Calculate overlap score based on temporal overlap
                    overlap_score = 0.0
                    for rid in valid_related_ids:
                        rule_event = rule_events_by_id[rid]
                        # Check temporal overlap
                        overlap_start = max(start_s, rule_event.start_s)
                        overlap_end = min(end_s, rule_event.end_s)
                        if overlap_end > overlap_start:
                            overlap_duration = overlap_end - overlap_start
                            event_duration = end_s - start_s
                            if event_duration > 0:
                                overlap_score = max(
                                    overlap_score,
                                    overlap_duration / event_duration
                                )

                    related_rule_events = RuleEventCorrelation(
                        rule_event_ids=tuple(valid_related_ids),
                        correlation_reason=correlation_reason or "Temporal and semantic overlap",
                        overlap_score=min(overlap_score, 1.0),
                    )

            # Generate deterministic event ID
            content = f"{event_type.value}:{start_s:.3f}:{','.join(map(str, valid_segment_ids))}"
            hash_suffix = hashlib.md5(content.encode()).hexdigest()[:8]
            event_id = f"llm_{event_type.value}_{int(start_s * 1000)}_{hash_suffix}"

            # Create event
            event = Event(
                event_id=event_id,
                event_type=event_type,
                severity=severity,
                confidence=float(data.get("confidence", 0.7)),
                start_s=start_s,
                end_s=end_s,
                start_ts=seconds_to_timestamp(start_s),
                end_ts=seconds_to_timestamp(end_s),
                title=str(data.get("title", f"{event_type.value.replace('_', ' ').title()}")),
                summary=str(data.get("summary", excerpt)),
                transcript_ref=TranscriptReference(
                    segment_ids=tuple(valid_segment_ids),
                    excerpt=excerpt,
                    keywords=keywords,
                ),
                suggested_actions=suggested_actions,
                metadata=EventMetadata(
                    extractor_engine=engine_name,
                    extractor_version=ENGINE_VERSION,
                    created_at=now,
                    source_transcript_path=source_path,
                ),
                related_rule_events=related_rule_events,
            )
            events.append(event)

        except (KeyError, TypeError, ValueError) as e:
            # Skip malformed events
            continue

    return events


class OpenAIEventEngine(BaseEventExtractionEngine):
    """LLM-based event extraction using OpenAI API.

    Requires OPENAI_API_KEY environment variable to be set.
    Default model: gpt-5-mini
    """

    def __init__(self, config: EventExtractionConfig | None = None) -> None:
        """Initialize the OpenAI event engine.

        Args:
            config: Event extraction configuration
        """
        super().__init__(config)
        self._client: OpenAI | None = None
        self._model_name = config.llm_model if config else "gpt-5-mini"

    def load(self) -> None:
        """Initialize the OpenAI client.

        Raises:
            CredentialsError: If OPENAI_API_KEY is not set
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
                "openai package is not installed. "
                "Install with: uv sync --extra openai"
            ) from e

    def unload(self) -> None:
        """Release OpenAI client resources."""
        self._client = None
        self._loaded = False

    def extract(
        self,
        transcript: Transcript,
        rule_events: tuple[Event, ...] | None = None,
    ) -> tuple[Event, ...]:
        """Extract events from transcript using OpenAI.

        Args:
            transcript: Transcript to analyze
            rule_events: Optional rule-based events for correlation

        Returns:
            Tuple of extracted events
        """
        if not self._loaded or self._client is None:
            raise RuntimeError("Client not loaded. Call load() first or use context manager.")

        if not transcript.segments:
            return ()

        # Process in batches
        all_events: list[Event] = []
        segments_list = list(transcript.segments)
        batch_size = self.config.max_segments_per_batch

        for i in range(0, len(segments_list), batch_size):
            batch = segments_list[i : i + batch_size]

            # Build prompt with rule events for correlation
            prompt = _build_extraction_prompt(batch, rule_events)

            try:
                request_args = {
                    "model": self._model_name,
                    "messages": [
                        {
                            "role": "system",
                            "content": "You are an expert infrastructure inspection analyst. "
                            "Extract significant events from transcripts and return valid JSON.",
                        },
                        {"role": "user", "content": prompt},
                    ],
                }
                # gpt-5* models currently only accept the default temperature (1).
                if not self._model_name.startswith("gpt-5"):
                    request_args["temperature"] = 0.2  # Lower temperature for consistency

                response = self._client.chat.completions.create(**request_args)

                response_text = response.choices[0].message.content or ""

                events = _parse_llm_response(
                    response_text,
                    batch,
                    f"openai/{self._model_name}",
                    self._model_name,
                    str(transcript.metadata.source_video)
                    if transcript.metadata.source_video
                    else None,
                    rule_events,
                )
                all_events.extend(events)

            except Exception as e:
                raise APIError(f"OpenAI API call failed: {e}") from e

        # Filter by minimum confidence
        filtered = [e for e in all_events if e.confidence >= self.config.min_confidence]

        return tuple(filtered)


class GeminiEventEngine(BaseEventExtractionEngine):
    """LLM-based event extraction using Google Gemini API.

    Requires GEMINI_API_KEY or GOOGLE_API_KEY environment variable.
    Default model: gemini-3-flash-preview
    """

    def __init__(self, config: EventExtractionConfig | None = None) -> None:
        """Initialize the Gemini event engine.

        Args:
            config: Event extraction configuration
        """
        super().__init__(config)
        self._client: Any = None
        self._model_name = config.llm_model if config else "gemini-3-flash-preview"

    def load(self) -> None:
        """Initialize the Gemini client.

        Raises:
            CredentialsError: If API key is not set
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
                "google-genai package is not installed. "
                "Install with: uv sync --extra gemini"
            ) from e

    def unload(self) -> None:
        """Release Gemini client resources."""
        import contextlib

        if self._client is not None:
            with contextlib.suppress(Exception):
                self._client.close()
        self._client = None
        self._loaded = False

    def extract(
        self,
        transcript: Transcript,
        rule_events: tuple[Event, ...] | None = None,
    ) -> tuple[Event, ...]:
        """Extract events from transcript using Gemini.

        Args:
            transcript: Transcript to analyze
            rule_events: Optional rule-based events for correlation

        Returns:
            Tuple of extracted events
        """
        if not self._loaded or self._client is None:
            raise RuntimeError("Client not loaded. Call load() first or use context manager.")

        if not transcript.segments:
            return ()

        # Process in batches
        all_events: list[Event] = []
        segments_list = list(transcript.segments)
        batch_size = self.config.max_segments_per_batch

        for i in range(0, len(segments_list), batch_size):
            batch = segments_list[i : i + batch_size]

            # Build prompt with rule events for correlation
            prompt = _build_extraction_prompt(batch, rule_events)

            try:
                response = self._client.models.generate_content(
                    model=self._model_name,
                    contents=prompt,
                )

                response_text = response.text or ""

                events = _parse_llm_response(
                    response_text,
                    batch,
                    f"gemini/{self._model_name}",
                    self._model_name,
                    str(transcript.metadata.source_video)
                    if transcript.metadata.source_video
                    else None,
                    rule_events,
                )
                all_events.extend(events)

            except Exception as e:
                raise APIError(f"Gemini API call failed: {e}") from e

        # Filter by minimum confidence
        filtered = [e for e in all_events if e.confidence >= self.config.min_confidence]

        return tuple(filtered)
