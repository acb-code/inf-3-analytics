"""Rule-based event extraction using keyword matching."""

import hashlib
import re
from dataclasses import dataclass
from datetime import datetime

from inf3_analytics.engines.event_extraction.base import (
    BaseEventExtractionEngine,
    EventExtractionConfig,
)
from inf3_analytics.types.event import (
    Event,
    EventMetadata,
    EventSeverity,
    EventType,
    TranscriptReference,
)
from inf3_analytics.types.transcript import Segment, Transcript
from inf3_analytics.utils.time import seconds_to_timestamp

# Version for deterministic tracking
ENGINE_VERSION = "1.0.0"

# Default keywords for each event type
DEFAULT_KEYWORDS: dict[EventType, list[str]] = {
    EventType.OBSERVATION: [
        "observed",
        "observation",
        "observe",
        "noted",
        "note",
    ],
    EventType.STRUCTURAL_ANOMALY: [
        "crack",
        "cracked",
        "cracking",
        "fracture",
        "corrosion",
        "corroded",
        "rust",
        "rusted",
        "rusting",
        "deformation",
        "deformed",
        "bent",
        "buckled",
        "damage",
        "damaged",
        "deterioration",
        "spalling",
        "scaling",
        "erosion",
    ],
    EventType.SAFETY_RISK: [
        "danger",
        "dangerous",
        "hazard",
        "hazardous",
        "warning",
        "caution",
        "risk",
        "unsafe",
        "concern",
        "concerning",
        "worried",
        "worry",
    ],
    EventType.MAINTENANCE_NOTE: [
        "repair",
        "replace",
        "fix",
        "maintenance",
        "service",
        "inspect",
        "inspection required",
        "needs attention",
        "should be",
        "recommend",
    ],
    EventType.MEASUREMENT: [
        "millimeter",
        "centimeter",
        "meter",
        "inch",
        "foot",
        "feet",
        "degrees",
        "percent",
        "thickness",
        "depth",
        "width",
        "length",
    ],
    EventType.LOCATION_REFERENCE: [
        "section",
        "area",
        "zone",
        "location",
        "position",
        "north",
        "south",
        "east",
        "west",
        "top",
        "bottom",
        "left",
        "right",
        "center",
        "span",
        "pier",
        "column",
        "beam",
        "joint",
    ],
    EventType.UNCERTAINTY: [
        "maybe",
        "possibly",
        "perhaps",
        "unclear",
        "not sure",
        "uncertain",
        "might be",
        "could be",
        "appears to",
        "seems like",
        "looks like",
    ],
}

# French keywords for each event type
DEFAULT_KEYWORDS_FR: dict[EventType, list[str]] = {
    EventType.OBSERVATION: [
        "observé",
        "observation",
        "observer",
        "noté",
        "noter",
        "constaté",
    ],
    EventType.STRUCTURAL_ANOMALY: [
        "fissure",
        "fissuré",
        "fissuration",
        "fracture",
        "corrosion",
        "corrodé",
        "rouille",
        "rouillé",
        "déformation",
        "déformé",
        "plié",
        "flambé",
        "dommage",
        "endommagé",
        "détérioration",
        "écaillage",
        "éclatement",
        "érosion",
    ],
    EventType.SAFETY_RISK: [
        "danger",
        "dangereux",
        "risque",
        "avertissement",
        "prudence",
        "précaution",
        "insécuritaire",
        "inquiétant",
        "préoccupant",
    ],
    EventType.MAINTENANCE_NOTE: [
        "réparation",
        "réparer",
        "remplacer",
        "entretien",
        "maintenance",
        "inspecter",
        "inspection requise",
        "nécessite attention",
        "recommander",
    ],
    EventType.MEASUREMENT: [
        "millimètre",
        "centimètre",
        "mètre",
        "pouce",
        "pied",
        "pieds",
        "degrés",
        "pourcent",
        "épaisseur",
        "profondeur",
        "largeur",
        "longueur",
    ],
    EventType.LOCATION_REFERENCE: [
        "section",
        "zone",
        "emplacement",
        "position",
        "nord",
        "sud",
        "est",
        "ouest",
        "haut",
        "bas",
        "gauche",
        "droite",
        "centre",
        "travée",
        "pilier",
        "colonne",
        "poutre",
        "joint",
    ],
    EventType.UNCERTAINTY: [
        "peut-être",
        "possiblement",
        "pas certain",
        "incertain",
        "pourrait être",
        "semble être",
        "on dirait",
    ],
}

DEFAULT_KEYWORDS_BY_LANG: dict[str, dict[EventType, list[str]]] = {
    "en": DEFAULT_KEYWORDS,
    "fr": DEFAULT_KEYWORDS_FR,
}

# High-signal keywords that boost confidence
HIGH_SIGNAL_KEYWORDS: set[str] = {
    "crack",
    "corrosion",
    "danger",
    "hazard",
    "damage",
    "unsafe",
    "fracture",
    "deterioration",
}

HIGH_SIGNAL_KEYWORDS_FR: set[str] = {
    "fissure",
    "corrosion",
    "danger",
    "risque",
    "dommage",
    "insécuritaire",
    "fracture",
    "détérioration",
}

HIGH_SIGNAL_KEYWORDS_BY_LANG: dict[str, set[str]] = {
    "en": HIGH_SIGNAL_KEYWORDS,
    "fr": HIGH_SIGNAL_KEYWORDS | HIGH_SIGNAL_KEYWORDS_FR,
}

# Keywords that suggest severity levels
SEVERITY_KEYWORDS: dict[EventSeverity, set[str]] = {
    EventSeverity.HIGH: {
        "severe",
        "critical",
        "major",
        "significant",
        "serious",
        "immediate",
        "urgent",
        "dangerous",
        "hazardous",
        "unsafe",
    },
    EventSeverity.MEDIUM: {
        "moderate",
        "noticeable",
        "visible",
        "apparent",
        "concerning",
    },
    EventSeverity.LOW: {
        "minor",
        "slight",
        "small",
        "minimal",
        "superficial",
    },
}

SEVERITY_KEYWORDS_FR: dict[EventSeverity, set[str]] = {
    EventSeverity.HIGH: {
        "sévère",
        "critique",
        "majeur",
        "important",
        "grave",
        "immédiat",
        "urgent",
        "dangereux",
        "risqué",
        "insécuritaire",
    },
    EventSeverity.MEDIUM: {
        "modéré",
        "notable",
        "visible",
        "apparent",
        "préoccupant",
    },
    EventSeverity.LOW: {
        "mineur",
        "léger",
        "petit",
        "minimal",
        "superficiel",
    },
}

SEVERITY_KEYWORDS_BY_LANG: dict[str, dict[EventSeverity, set[str]]] = {
    "en": SEVERITY_KEYWORDS,
    "fr": {
        sev: SEVERITY_KEYWORDS[sev] | SEVERITY_KEYWORDS_FR[sev]
        for sev in EventSeverity
    },
}

NEGATION_TERMS = ("no", "not", "without", "none", "never", "neither")
NEGATION_TERMS_FR = ("non", "pas", "sans", "aucun", "aucune", "jamais", "ni")
NEGATION_TERMS_BY_LANG: dict[str, tuple[str, ...]] = {
    "en": NEGATION_TERMS,
    "fr": NEGATION_TERMS + NEGATION_TERMS_FR,
}
MEASUREMENT_NUMBER_RE = re.compile(r"\b\d+(?:\.\d+)?\b")


def _keyword_pattern(keyword: str) -> re.Pattern[str]:
    parts = [re.escape(p) for p in keyword.split()]
    if len(parts) == 1:
        word = parts[0]
        # Add optional 's' suffix for singular keywords
        pattern = r"\b" + word + r"s?\b" if not keyword.endswith("s") else r"\b" + word + r"\b"
    else:
        pattern = r"\b" + r"\s+".join(parts) + r"\b"
    return re.compile(pattern)


@dataclass
class TriggerMatch:
    """A segment that matched keywords."""

    segment_id: int
    event_type: EventType
    keywords: tuple[str, ...]
    confidence: float


@dataclass
class SegmentWindow:
    """A window of segments around a trigger."""

    segments: tuple[Segment, ...]
    event_type: EventType
    keywords: tuple[str, ...]
    confidence: float


class RuleBasedEventEngine(BaseEventExtractionEngine):
    """Rule-based event extraction using keyword matching."""

    def __init__(self, config: EventExtractionConfig | None = None) -> None:
        """Initialize the rule-based engine.

        Args:
            config: Event extraction configuration (uses defaults if None)
        """
        super().__init__(config)
        self._keywords: dict[EventType, list[str]] = {}
        self._keyword_patterns: dict[EventType, list[tuple[str, re.Pattern[str]]]] = {}

    def load(self) -> None:
        """Load keyword configuration."""
        if self._loaded:
            return

        # Select keyword set based on language
        lang = self.config.language
        base_keywords = DEFAULT_KEYWORDS_BY_LANG.get(lang, DEFAULT_KEYWORDS)
        self._keywords = {k: list(v) for k, v in base_keywords.items()}

        # For French, also include English keywords for broader coverage
        if lang == "fr":
            for event_type, en_keywords in DEFAULT_KEYWORDS.items():
                self._keywords.setdefault(event_type, [])
                self._keywords[event_type].extend(en_keywords)

        self._keyword_patterns = {
            event_type: [(kw, _keyword_pattern(kw)) for kw in keywords]
            for event_type, keywords in self._keywords.items()
        }

        # TODO: Load custom keywords from file if config.keywords_file is set

        self._loaded = True

    def unload(self) -> None:
        """Release engine resources."""
        self._keywords = {}
        self._keyword_patterns = {}
        self._loaded = False

    def extract(self, transcript: Transcript) -> tuple[Event, ...]:
        """Extract events from transcript using keyword matching.

        Args:
            transcript: Transcript to analyze

        Returns:
            Tuple of extracted events
        """
        if not self._loaded:
            self.load()

        if not transcript.segments:
            return ()

        # Step 1: Find trigger segments
        triggers = self._find_triggers(transcript.segments)

        if not triggers:
            return ()

        # Step 2: Expand context windows
        windows = self._expand_windows(triggers, transcript.segments)

        # Step 3: Merge overlapping windows
        merged = self._merge_overlapping(windows)

        # Step 4: Generate events
        events = self._create_events(merged, transcript)

        # Filter by minimum confidence
        filtered = [e for e in events if e.confidence >= self.config.min_confidence]

        return tuple(filtered)

    def _find_triggers(self, segments: tuple[Segment, ...]) -> list[TriggerMatch]:
        """Find segments that match keywords.

        Args:
            segments: Tuple of transcript segments

        Returns:
            List of trigger matches
        """
        triggers: list[TriggerMatch] = []

        for seg in segments:
            text_lower = seg.text.lower()
            segment_matches: dict[EventType, list[str]] = {}

            for event_type, patterns in self._keyword_patterns.items():
                matched: list[str] = []
                for kw, pattern in patterns:
                    match = pattern.search(text_lower)
                    if match and not self._is_negated(text_lower, match.start(), match.end()):
                        matched.append(kw)

                if matched:
                    segment_matches[event_type] = matched

            for event_type, matched in segment_matches.items():
                # Skip measurements without actual numbers
                if event_type == EventType.MEASUREMENT and not MEASUREMENT_NUMBER_RE.search(text_lower):
                    continue

                # Skip location references (too noisy as standalone events)
                if event_type == EventType.LOCATION_REFERENCE:
                    continue

                confidence = self._calculate_confidence(matched, text_lower)

                triggers.append(
                    TriggerMatch(
                        segment_id=seg.id,
                        event_type=event_type,
                        keywords=tuple(matched),
                        confidence=confidence,
                    )
                )

        return triggers

    def _is_negated(self, text: str, start: int, end: int) -> bool:
        """Check if a keyword match is negated within a short window."""
        prefix = text[max(0, start - 80) : start]
        suffix = text[end : min(len(text), end + 80)]

        neg_terms = NEGATION_TERMS_BY_LANG.get(self.config.language, NEGATION_TERMS)

        negation_prefix = re.search(
            r"\b(" + "|".join(re.escape(t) for t in neg_terms) + r")\b(?:\W+\w+){0,3}\W*$",
            prefix,
        )
        if negation_prefix:
            return True

        negation_suffix = re.search(
            r"^\W*(?:\w+\W+){0,3}\b(" + "|".join(re.escape(t) for t in neg_terms) + r")\b",
            suffix,
        )
        return bool(negation_suffix)

    def _calculate_confidence(self, keywords: list[str], _text: str) -> float:
        """Calculate confidence based on keyword density and specificity.

        Args:
            keywords: List of matched keywords
            _text: The text that was searched (reserved for future use)

        Returns:
            Confidence score between 0.0 and 1.0
        """
        # Base confidence from keyword count
        base = min(0.3 + 0.15 * len(keywords), 0.8)

        # Boost for specific high-signal keywords
        high_signal = HIGH_SIGNAL_KEYWORDS_BY_LANG.get(self.config.language, HIGH_SIGNAL_KEYWORDS)
        if any(kw in high_signal for kw in keywords):
            base = min(base + 0.15, 0.95)

        return base

    def _expand_windows(
        self, triggers: list[TriggerMatch], segments: tuple[Segment, ...]
    ) -> list[SegmentWindow]:
        """Expand triggers to include context segments.

        Args:
            triggers: List of trigger matches
            segments: All segments in the transcript

        Returns:
            List of segment windows
        """
        windows: list[SegmentWindow] = []
        segment_by_id = {s.id: s for s in segments}
        all_ids = sorted(segment_by_id.keys())

        if not all_ids:
            return windows

        min_id = min(all_ids)
        max_id = max(all_ids)

        for trigger in triggers:
            # Get ±context_window segments
            start_id = max(min_id, trigger.segment_id - self.config.context_window)
            end_id = min(max_id, trigger.segment_id + self.config.context_window)

            window_segments = [
                segment_by_id[i]
                for i in range(start_id, end_id + 1)
                if i in segment_by_id
            ]

            if window_segments:
                windows.append(
                    SegmentWindow(
                        segments=tuple(window_segments),
                        event_type=trigger.event_type,
                        keywords=trigger.keywords,
                        confidence=trigger.confidence,
                    )
                )

        return windows

    def _merge_overlapping(self, windows: list[SegmentWindow]) -> list[SegmentWindow]:
        """Merge windows that overlap or are within merge_gap_s.

        Args:
            windows: List of segment windows

        Returns:
            Merged list of segment windows
        """
        if not windows:
            return []

        # Sort by start time
        sorted_windows = sorted(windows, key=lambda w: w.segments[0].start_s)

        merged: list[SegmentWindow] = []
        current = sorted_windows[0]

        for window in sorted_windows[1:]:
            # Check if same event type and overlapping/close
            same_type = window.event_type == current.event_type
            gap = window.segments[0].start_s - current.segments[-1].end_s
            within_gap = gap <= self.config.merge_gap_s
            keywords_overlap = self._keywords_overlap(window, current)

            if same_type and within_gap and (gap <= 0 or keywords_overlap):
                # Merge windows
                current = self._merge_two_windows(current, window)
            else:
                merged.append(current)
                current = window

        merged.append(current)
        return merged

    def _keywords_overlap(self, window1: SegmentWindow, window2: SegmentWindow) -> bool:
        return bool(set(window1.keywords) & set(window2.keywords))

    def _merge_two_windows(
        self, window1: SegmentWindow, window2: SegmentWindow
    ) -> SegmentWindow:
        """Merge two overlapping windows into one.

        Args:
            window1: First window
            window2: Second window

        Returns:
            Merged window
        """
        # Combine segments, removing duplicates by id
        seen_ids: set[int] = set()
        combined_segments: list[Segment] = []

        for seg in list(window1.segments) + list(window2.segments):
            if seg.id not in seen_ids:
                seen_ids.add(seg.id)
                combined_segments.append(seg)

        # Sort by start time
        combined_segments.sort(key=lambda s: s.start_s)

        # Combine keywords, removing duplicates
        all_keywords = set(window1.keywords) | set(window2.keywords)

        # Take max confidence
        confidence = max(window1.confidence, window2.confidence)

        return SegmentWindow(
            segments=tuple(combined_segments),
            event_type=window1.event_type,
            keywords=tuple(sorted(all_keywords)),
            confidence=confidence,
        )

    def _create_events(
        self, windows: list[SegmentWindow], transcript: Transcript
    ) -> list[Event]:
        """Create Event objects from segment windows.

        Args:
            windows: List of merged segment windows
            transcript: Source transcript for metadata

        Returns:
            List of Event objects
        """
        events: list[Event] = []
        now = datetime.now().isoformat()

        for window in windows:
            if not window.segments:
                continue

            # Calculate timing
            start_s = window.segments[0].start_s
            end_s = window.segments[-1].end_s

            # Get segment IDs
            segment_ids = tuple(s.id for s in window.segments)

            # Generate excerpt from segment texts
            excerpt = self._generate_excerpt(window.segments)

            # Determine severity from text
            full_text = " ".join(s.text for s in window.segments).lower()
            severity = self._determine_severity(full_text)

            # Generate title and summary
            title = self._generate_title(window.event_type, window.keywords)
            summary = self._generate_summary(window.event_type, excerpt, window.keywords)

            # Generate deterministic event ID
            event_id = self._generate_event_id(window.event_type, start_s, segment_ids)

            # Create transcript reference
            transcript_ref = TranscriptReference(
                segment_ids=segment_ids,
                excerpt=excerpt,
                keywords=window.keywords,
            )

            # Create metadata
            metadata = EventMetadata(
                extractor_engine="rules",
                extractor_version=ENGINE_VERSION,
                created_at=now,
                source_transcript_path=(
                    str(transcript.metadata.source_video)
                    if transcript.metadata.source_video
                    else None
                ),
            )

            # Create event
            event = Event(
                event_id=event_id,
                event_type=window.event_type,
                severity=severity,
                confidence=window.confidence,
                start_s=start_s,
                end_s=end_s,
                start_ts=seconds_to_timestamp(start_s),
                end_ts=seconds_to_timestamp(end_s),
                title=title,
                summary=summary,
                transcript_ref=transcript_ref,
                suggested_actions=self._suggest_actions(window.event_type, severity),
                metadata=metadata,
            )

            events.append(event)

        return events

    def _generate_event_id(
        self, event_type: EventType, start_s: float, segment_ids: tuple[int, ...]
    ) -> str:
        """Generate stable, deterministic event ID.

        Args:
            event_type: Type of the event
            start_s: Start time in seconds
            segment_ids: IDs of source segments

        Returns:
            Deterministic event ID string
        """
        content = f"{event_type.value}:{start_s:.3f}:{','.join(map(str, segment_ids))}"
        hash_suffix = hashlib.md5(content.encode()).hexdigest()[:8]
        return f"{event_type.value}_{int(start_s * 1000)}_{hash_suffix}"

    def _generate_excerpt(self, segments: tuple[Segment, ...], max_length: int = 200) -> str:
        """Generate a concise excerpt from segments.

        Args:
            segments: Segments to excerpt
            max_length: Maximum excerpt length

        Returns:
            Concise text excerpt
        """
        full_text = " ".join(s.text.strip() for s in segments)

        if len(full_text) <= max_length:
            return full_text

        # Truncate and add ellipsis
        return full_text[: max_length - 3].rsplit(" ", 1)[0] + "..."

    def _determine_severity(self, text: str) -> EventSeverity | None:
        """Determine event severity from text.

        Args:
            text: Lowercase text to analyze

        Returns:
            Severity level or None if undetermined
        """
        # Check for severity keywords in order of priority
        sev_keywords = SEVERITY_KEYWORDS_BY_LANG.get(self.config.language, SEVERITY_KEYWORDS)
        for severity in [EventSeverity.HIGH, EventSeverity.MEDIUM, EventSeverity.LOW]:
            if any(kw in text for kw in sev_keywords[severity]):
                return severity

        return None

    def _generate_title(self, event_type: EventType, keywords: tuple[str, ...]) -> str:
        """Generate a short title for the event.

        Args:
            event_type: Type of the event
            keywords: Keywords that triggered the event

        Returns:
            Short descriptive title
        """
        type_names_en = {
            EventType.OBSERVATION: "Observation",
            EventType.STRUCTURAL_ANOMALY: "Structural issue",
            EventType.MAINTENANCE_NOTE: "Maintenance note",
            EventType.SAFETY_RISK: "Safety concern",
            EventType.MEASUREMENT: "Measurement",
            EventType.LOCATION_REFERENCE: "Location reference",
            EventType.UNCERTAINTY: "Uncertainty noted",
            EventType.OTHER: "Note",
        }
        type_names_fr = {
            EventType.OBSERVATION: "Observation",
            EventType.STRUCTURAL_ANOMALY: "Anomalie structurelle",
            EventType.MAINTENANCE_NOTE: "Note de maintenance",
            EventType.SAFETY_RISK: "Risque de sécurité",
            EventType.MEASUREMENT: "Mesure",
            EventType.LOCATION_REFERENCE: "Référence de localisation",
            EventType.UNCERTAINTY: "Incertitude notée",
            EventType.OTHER: "Note",
        }

        is_fr = self.config.language == "fr"
        type_names = type_names_fr if is_fr else type_names_en
        base_title = type_names.get(event_type, "Note")

        # Add primary keyword if it provides specificity
        high_signal = HIGH_SIGNAL_KEYWORDS_BY_LANG.get(self.config.language, HIGH_SIGNAL_KEYWORDS)
        if keywords:
            primary_kw = keywords[0]
            if primary_kw in high_signal:
                suffix = "détecté(e)" if is_fr else "detected"
                return f"{primary_kw.capitalize()} {suffix}"

        return base_title

    def _generate_summary(
        self, event_type: EventType, excerpt: str, keywords: tuple[str, ...]
    ) -> str:
        """Generate a summary for the event.

        Args:
            event_type: Type of the event
            excerpt: Text excerpt
            keywords: Keywords that triggered the event

        Returns:
            1-3 sentence summary
        """
        keyword_str = ", ".join(keywords[:3])
        type_label = event_type.value.replace("_", " ")
        if self.config.language == "fr":
            return f"Mots-clés de type {type_label} détectés ({keyword_str}) : \"{excerpt}\""
        return f"Detected {type_label} keywords ({keyword_str}): \"{excerpt}\""

    def _suggest_actions(
        self, event_type: EventType, severity: EventSeverity | None
    ) -> tuple[str, ...] | None:
        """Suggest follow-up actions based on event type and severity.

        Args:
            event_type: Type of the event
            severity: Severity level

        Returns:
            Tuple of suggested actions or None
        """
        actions: list[str] = []
        is_fr = self.config.language == "fr"

        if event_type == EventType.STRUCTURAL_ANOMALY:
            actions.append("Planifier une inspection détaillée" if is_fr else "Schedule detailed inspection")
            if severity == EventSeverity.HIGH:
                actions.append("Prioriser pour évaluation immédiate" if is_fr else "Prioritize for immediate assessment")

        elif event_type == EventType.SAFETY_RISK:
            actions.append("Réviser les protocoles de sécurité" if is_fr else "Review safety protocols")
            if severity == EventSeverity.HIGH:
                actions.append("Considérer une remédiation immédiate" if is_fr else "Consider immediate remediation")

        elif event_type == EventType.MAINTENANCE_NOTE:
            actions.append("Ajouter au calendrier de maintenance" if is_fr else "Add to maintenance schedule")

        elif event_type == EventType.MEASUREMENT:
            actions.append("Vérifier la précision de la mesure" if is_fr else "Verify measurement accuracy")
            actions.append("Comparer avec les données de référence" if is_fr else "Compare with baseline data")

        elif event_type == EventType.UNCERTAINTY:
            actions.append("Planifier une inspection de suivi pour clarification" if is_fr else "Schedule follow-up inspection for clarification")

        return tuple(actions) if actions else None
