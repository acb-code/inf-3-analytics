"""Detection data types for frame analytics."""

from dataclasses import dataclass
from enum import Enum
from typing import Any


class DetectionType(Enum):
    """Categories of detections in infrastructure inspection frames."""

    STRUCTURAL_ANOMALY = "structural_anomaly"
    CORROSION = "corrosion"
    CRACK = "crack"
    SPALLING = "spalling"
    LEAK = "leak"
    OBSTRUCTION = "obstruction"
    SAFETY_RISK = "safety_risk"
    EQUIPMENT_ISSUE = "equipment_issue"
    VEGETATION = "vegetation"
    CONSTRUCTION_EQUIPMENT = "construction_equipment"
    VEHICLE = "vehicle"
    PERSON = "person"
    HARDHAT = "hardhat"
    OTHER = "other"


class Severity(Enum):
    """Severity classification for detections."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class EquipmentClass(Enum):
    """Construction equipment categories."""

    EXCAVATOR = "excavator"
    CRANE = "crane"
    DUMP_TRUCK = "dump_truck"
    CONCRETE_MIXER = "concrete_mixer"
    BULLDOZER = "bulldozer"
    LOADER = "loader"
    SCAFFOLDING = "scaffolding"
    OTHER = "other"


class HardhatColor(Enum):
    """Hardhat color categories for personnel identification."""

    WHITE = "white"
    YELLOW = "yellow"
    ORANGE = "orange"
    RED = "red"
    BLUE = "blue"
    GREEN = "green"
    OTHER = "other"


@dataclass(frozen=True, slots=True)
class BoundingBox:
    """Bounding box coordinates (normalized 0-1 or absolute pixels)."""

    x: float
    y: float
    w: float
    h: float

    def to_dict(self) -> dict[str, float]:
        """Convert to dictionary for serialization."""
        return {"x": self.x, "y": self.y, "w": self.w, "h": self.h}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "BoundingBox":
        """Create BoundingBox from dictionary."""
        return cls(
            x=float(data["x"]),
            y=float(data["y"]),
            w=float(data["w"]),
            h=float(data["h"]),
        )


@dataclass(frozen=True, slots=True)
class DetectionAttributes:
    """Additional attributes for a detection."""

    severity: Severity | None
    materials: tuple[str, ...] | None
    location_hint: str | None
    notes: str | None
    equipment_class: EquipmentClass | None = None
    hardhat_color: HardhatColor | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        d: dict[str, Any] = {
            "severity": self.severity.value if self.severity else None,
            "materials": list(self.materials) if self.materials else None,
            "location_hint": self.location_hint,
            "notes": self.notes,
        }
        if self.equipment_class is not None:
            d["equipment_class"] = self.equipment_class.value
        if self.hardhat_color is not None:
            d["hardhat_color"] = self.hardhat_color.value
        return d

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "DetectionAttributes":
        """Create DetectionAttributes from dictionary."""
        severity_data = data.get("severity")
        severity = Severity(severity_data) if severity_data else None

        materials_data = data.get("materials")
        materials = tuple(str(m) for m in materials_data) if materials_data else None

        eq_data = data.get("equipment_class")
        equipment_class = EquipmentClass(eq_data) if eq_data else None

        hc_data = data.get("hardhat_color")
        hardhat_color = HardhatColor(hc_data) if hc_data else None

        return cls(
            severity=severity,
            materials=materials,
            location_hint=data.get("location_hint"),
            notes=data.get("notes"),
            equipment_class=equipment_class,
            hardhat_color=hardhat_color,
        )


@dataclass(frozen=True, slots=True)
class Detection:
    """A single detection in a frame."""

    detection_type: DetectionType
    label: str
    confidence: float
    bbox: BoundingBox | None
    attributes: DetectionAttributes

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "type": self.detection_type.value,
            "label": self.label,
            "confidence": self.confidence,
            "bbox": self.bbox.to_dict() if self.bbox else None,
            "attributes": self.attributes.to_dict(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Detection":
        """Create Detection from dictionary."""
        bbox_data = data.get("bbox")
        bbox = BoundingBox.from_dict(bbox_data) if bbox_data else None

        attributes_data = data.get("attributes", {})
        if not isinstance(attributes_data, dict):
            attributes_data = {}

        return cls(
            detection_type=DetectionType(data["type"]),
            label=str(data["label"]),
            confidence=float(data["confidence"]),
            bbox=bbox,
            attributes=DetectionAttributes.from_dict(attributes_data),
        )


@dataclass(frozen=True, slots=True)
class QAPair:
    """A question-answer pair from VLM analysis."""

    question: str
    answer: str

    def to_dict(self) -> dict[str, str]:
        """Convert to dictionary for serialization."""
        return {"q": self.question, "a": self.answer}

    @classmethod
    def from_dict(cls, data: dict[str, str]) -> "QAPair":
        """Create QAPair from dictionary."""
        return cls(question=str(data["q"]), answer=str(data["a"]))


@dataclass(frozen=True, slots=True)
class EngineInfo:
    """Information about the analysis engine used."""

    name: str  # "vlm" or "baseline_quality"
    provider: str | None  # "openai", "gemini", or None for baseline
    model: str | None  # "gpt-5-mini", "gemini-3-flash-preview", etc.
    prompt_version: str | None  # e.g., "v1"
    version: str  # Engine version, e.g., "0.1.0"
    config: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "name": self.name,
            "provider": self.provider,
            "model": self.model,
            "prompt_version": self.prompt_version,
            "version": self.version,
            "config": self.config,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "EngineInfo":
        """Create EngineInfo from dictionary."""
        config_data = data.get("config", {})
        if not isinstance(config_data, dict):
            config_data = {}

        return cls(
            name=str(data["name"]),
            provider=data.get("provider"),
            model=data.get("model"),
            prompt_version=data.get("prompt_version"),
            version=str(data["version"]),
            config=config_data,
        )


@dataclass(frozen=True, slots=True)
class FrameMeta:
    """Metadata about a frame being analyzed."""

    frame_idx: int
    timestamp_s: float
    timestamp_ts: str
    image_path: str
    event_id: str
    event_title: str | None
    event_summary: str | None
    transcript_excerpt: str | None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "frame_idx": self.frame_idx,
            "timestamp_s": self.timestamp_s,
            "timestamp_ts": self.timestamp_ts,
            "image_path": self.image_path,
            "event_id": self.event_id,
            "event_title": self.event_title,
            "event_summary": self.event_summary,
            "transcript_excerpt": self.transcript_excerpt,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "FrameMeta":
        """Create FrameMeta from dictionary."""
        return cls(
            frame_idx=int(data["frame_idx"]),
            timestamp_s=float(data["timestamp_s"]),
            timestamp_ts=str(data["timestamp_ts"]),
            image_path=str(data["image_path"]),
            event_id=str(data["event_id"]),
            event_title=data.get("event_title"),
            event_summary=data.get("event_summary"),
            transcript_excerpt=data.get("transcript_excerpt"),
        )


@dataclass(frozen=True, slots=True)
class FrameAnalyticsResult:
    """Result of analyzing a single frame."""

    event_id: str
    frame_idx: int
    timestamp_s: float
    timestamp_ts: str
    image_path: str
    engine: EngineInfo
    detections: tuple[Detection, ...]
    scene_summary: str
    qa: tuple[QAPair, ...] | None
    raw_model_output: dict[str, Any] | None
    error: str | None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "event_id": self.event_id,
            "frame_idx": self.frame_idx,
            "timestamp_s": self.timestamp_s,
            "timestamp_ts": self.timestamp_ts,
            "image_path": self.image_path,
            "engine": self.engine.to_dict(),
            "detections": [d.to_dict() for d in self.detections],
            "scene_summary": self.scene_summary,
            "qa": [q.to_dict() for q in self.qa] if self.qa else None,
            "raw_model_output": self.raw_model_output,
            "error": self.error,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "FrameAnalyticsResult":
        """Create FrameAnalyticsResult from dictionary."""
        engine_data = data["engine"]
        if not isinstance(engine_data, dict):
            raise ValueError("engine must be a dict")

        detections_data = data.get("detections", [])
        if not isinstance(detections_data, list):
            detections_data = []

        qa_data = data.get("qa")
        qa = None
        if qa_data and isinstance(qa_data, list):
            qa = tuple(QAPair.from_dict(q) for q in qa_data)

        return cls(
            event_id=str(data["event_id"]),
            frame_idx=int(data["frame_idx"]),
            timestamp_s=float(data["timestamp_s"]),
            timestamp_ts=str(data["timestamp_ts"]),
            image_path=str(data["image_path"]),
            engine=EngineInfo.from_dict(engine_data),
            detections=tuple(Detection.from_dict(d) for d in detections_data),
            scene_summary=str(data.get("scene_summary", "")),
            qa=qa,
            raw_model_output=data.get("raw_model_output"),
            error=data.get("error"),
        )


@dataclass(frozen=True, slots=True)
class TimeRange:
    """Time range in seconds."""

    start_s: float
    end_s: float

    def to_dict(self) -> dict[str, float]:
        """Convert to dictionary for serialization."""
        return {"start_s": self.start_s, "end_s": self.end_s}

    @classmethod
    def from_dict(cls, data: dict[str, float]) -> "TimeRange":
        """Create TimeRange from dictionary."""
        return cls(start_s=float(data["start_s"]), end_s=float(data["end_s"]))


@dataclass(frozen=True, slots=True)
class RepresentativeFrame:
    """Reference to a representative frame."""

    frame_idx: int
    image_path: str
    timestamp_s: float

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "frame_idx": self.frame_idx,
            "image_path": self.image_path,
            "timestamp_s": self.timestamp_s,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "RepresentativeFrame":
        """Create RepresentativeFrame from dictionary."""
        return cls(
            frame_idx=int(data["frame_idx"]),
            image_path=str(data["image_path"]),
            timestamp_s=float(data["timestamp_s"]),
        )


@dataclass(frozen=True, slots=True)
class Finding:
    """A top finding from event analysis."""

    detection_type: DetectionType
    label: str
    max_confidence: float
    frame_count: int
    severity: Severity | None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "type": self.detection_type.value,
            "label": self.label,
            "max_confidence": self.max_confidence,
            "frame_count": self.frame_count,
            "severity": self.severity.value if self.severity else None,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Finding":
        """Create Finding from dictionary."""
        severity_data = data.get("severity")
        severity = Severity(severity_data) if severity_data else None

        return cls(
            detection_type=DetectionType(data["type"]),
            label=str(data["label"]),
            max_confidence=float(data["max_confidence"]),
            frame_count=int(data["frame_count"]),
            severity=severity,
        )


@dataclass(frozen=True, slots=True)
class AggregatedConfidence:
    """Aggregated confidence scores by detection type."""

    by_type: dict[str, float]  # DetectionType.value -> max confidence

    def to_dict(self) -> dict[str, dict[str, float]]:
        """Convert to dictionary for serialization."""
        return {"by_type": self.by_type}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AggregatedConfidence":
        """Create AggregatedConfidence from dictionary."""
        by_type_data = data.get("by_type", {})
        if not isinstance(by_type_data, dict):
            by_type_data = {}
        return cls(by_type={str(k): float(v) for k, v in by_type_data.items()})


@dataclass(frozen=True, slots=True)
class EventAnalyticsSummary:
    """Summary of analytics for an event."""

    event_id: str
    engine: EngineInfo
    frame_count: int
    analyzed_count: int
    failed_count: int
    time_range: TimeRange
    top_findings: tuple[Finding, ...]
    aggregated_confidence: AggregatedConfidence
    representative_frame: RepresentativeFrame | None
    created_at: str
    source_manifest: str

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "event_id": self.event_id,
            "engine": self.engine.to_dict(),
            "frame_count": self.frame_count,
            "analyzed_count": self.analyzed_count,
            "failed_count": self.failed_count,
            "time_range": self.time_range.to_dict(),
            "top_findings": [f.to_dict() for f in self.top_findings],
            "aggregated_confidence": self.aggregated_confidence.to_dict(),
            "representative_frame": (
                self.representative_frame.to_dict() if self.representative_frame else None
            ),
            "created_at": self.created_at,
            "source_manifest": self.source_manifest,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "EventAnalyticsSummary":
        """Create EventAnalyticsSummary from dictionary."""
        engine_data = data["engine"]
        if not isinstance(engine_data, dict):
            raise ValueError("engine must be a dict")

        time_range_data = data["time_range"]
        if not isinstance(time_range_data, dict):
            raise ValueError("time_range must be a dict")

        findings_data = data.get("top_findings", [])
        if not isinstance(findings_data, list):
            findings_data = []

        confidence_data = data.get("aggregated_confidence", {"by_type": {}})
        if not isinstance(confidence_data, dict):
            confidence_data = {"by_type": {}}

        rep_frame_data = data.get("representative_frame")
        rep_frame = None
        if rep_frame_data and isinstance(rep_frame_data, dict):
            rep_frame = RepresentativeFrame.from_dict(rep_frame_data)

        return cls(
            event_id=str(data["event_id"]),
            engine=EngineInfo.from_dict(engine_data),
            frame_count=int(data["frame_count"]),
            analyzed_count=int(data.get("analyzed_count", data["frame_count"])),
            failed_count=int(data.get("failed_count", 0)),
            time_range=TimeRange.from_dict(time_range_data),
            top_findings=tuple(Finding.from_dict(f) for f in findings_data),
            aggregated_confidence=AggregatedConfidence.from_dict(confidence_data),
            representative_frame=rep_frame,
            created_at=str(data["created_at"]),
            source_manifest=str(data["source_manifest"]),
        )


@dataclass(frozen=True, slots=True)
class AnalyticsManifest:
    """Manifest for frame analytics run."""

    run_id: str
    engine: EngineInfo
    source_event_frames_manifest: str
    events_file: str | None
    total_events: int
    total_frames: int
    analyzed_frames: int
    failed_frames: int
    created_at: str
    event_summaries: tuple[str, ...]  # Paths to event_summary.json files

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "run_id": self.run_id,
            "engine": self.engine.to_dict(),
            "source_event_frames_manifest": self.source_event_frames_manifest,
            "events_file": self.events_file,
            "total_events": self.total_events,
            "total_frames": self.total_frames,
            "analyzed_frames": self.analyzed_frames,
            "failed_frames": self.failed_frames,
            "created_at": self.created_at,
            "event_summaries": list(self.event_summaries),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AnalyticsManifest":
        """Create AnalyticsManifest from dictionary."""
        engine_data = data["engine"]
        if not isinstance(engine_data, dict):
            raise ValueError("engine must be a dict")

        summaries_data = data.get("event_summaries", [])
        if not isinstance(summaries_data, list):
            summaries_data = []

        return cls(
            run_id=str(data["run_id"]),
            engine=EngineInfo.from_dict(engine_data),
            source_event_frames_manifest=str(data["source_event_frames_manifest"]),
            events_file=data.get("events_file"),
            total_events=int(data["total_events"]),
            total_frames=int(data["total_frames"]),
            analyzed_frames=int(data["analyzed_frames"]),
            failed_frames=int(data["failed_frames"]),
            created_at=str(data["created_at"]),
            event_summaries=tuple(str(s) for s in summaries_data),
        )
