"""Aggregation logic for event-level analytics summaries."""

from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from inf3_analytics.types.detection import (
    AggregatedConfidence,
    DetectionType,
    EngineInfo,
    EquipmentClass,
    EventAnalyticsSummary,
    Finding,
    FrameAnalyticsResult,
    HardhatColor,
    RepresentativeFrame,
    Severity,
    TimeRange,
)


def aggregate_event_results(
    results: list[FrameAnalyticsResult],
    event_id: str,
    engine_info: EngineInfo,
    source_manifest: str,
) -> EventAnalyticsSummary:
    """Aggregate frame-level results into an event summary.

    Args:
        results: List of frame analysis results for this event
        event_id: Event identifier
        engine_info: Engine information for traceability
        source_manifest: Path to source manifest file

    Returns:
        EventAnalyticsSummary with aggregated findings
    """
    if not results:
        return EventAnalyticsSummary(
            event_id=event_id,
            engine=engine_info,
            frame_count=0,
            analyzed_count=0,
            failed_count=0,
            time_range=TimeRange(start_s=0.0, end_s=0.0),
            top_findings=(),
            aggregated_confidence=AggregatedConfidence(by_type={}),
            representative_frame=None,
            created_at=datetime.now().isoformat(),
            source_manifest=source_manifest,
        )

    # Count successful vs failed
    successful = [r for r in results if r.error is None]
    failed = [r for r in results if r.error is not None]

    # Time range
    timestamps = [r.timestamp_s for r in results]
    time_range = TimeRange(start_s=min(timestamps), end_s=max(timestamps))

    # Aggregate detections by type
    type_detections: dict[DetectionType, list[tuple[float, str, Severity | None]]] = defaultdict(
        list
    )

    for result in successful:
        for detection in result.detections:
            type_detections[detection.detection_type].append(
                (
                    detection.confidence,
                    detection.label,
                    detection.attributes.severity,
                )
            )

    # Build findings (top detections by type)
    findings: list[Finding] = []
    confidence_by_type: dict[str, float] = {}

    for dtype, detects in type_detections.items():
        if not detects:
            continue

        # Get max confidence and most severe
        max_conf = max(d[0] for d in detects)
        frame_count = len(detects)

        # Get most common label
        label_counts: dict[str, int] = defaultdict(int)
        for _, label, _ in detects:
            label_counts[label] += 1
        top_label = max(label_counts.items(), key=lambda x: x[1])[0]

        # Get highest severity
        severities = [d[2] for d in detects if d[2] is not None]
        severity_order = {Severity.HIGH: 3, Severity.MEDIUM: 2, Severity.LOW: 1}
        max_severity = None
        if severities:
            max_severity = max(severities, key=lambda s: severity_order.get(s, 0))

        findings.append(
            Finding(
                detection_type=dtype,
                label=top_label,
                max_confidence=max_conf,
                frame_count=frame_count,
                severity=max_severity,
            )
        )

        confidence_by_type[dtype.value] = max_conf

    # Sort findings by confidence descending
    findings.sort(key=lambda f: f.max_confidence, reverse=True)

    # Select representative frame (highest total detection confidence)
    representative: RepresentativeFrame | None = None
    if successful:
        best_result = max(
            successful,
            key=lambda r: sum(d.confidence for d in r.detections) if r.detections else 0,
        )
        representative = RepresentativeFrame(
            frame_idx=best_result.frame_idx,
            image_path=best_result.image_path,
            timestamp_s=best_result.timestamp_s,
        )

    return EventAnalyticsSummary(
        event_id=event_id,
        engine=engine_info,
        frame_count=len(results),
        analyzed_count=len(successful),
        failed_count=len(failed),
        time_range=time_range,
        top_findings=tuple(findings[:10]),  # Top 10 findings
        aggregated_confidence=AggregatedConfidence(by_type=confidence_by_type),
        representative_frame=representative,
        created_at=datetime.now().isoformat(),
        source_manifest=source_manifest,
    )


def select_representative_frame(results: list[FrameAnalyticsResult]) -> RepresentativeFrame | None:
    """Select the most representative frame from results.

    Selection criteria:
    1. Frames with detections are preferred
    2. Higher total confidence is preferred
    3. Frames without errors are required

    Args:
        results: List of frame analysis results

    Returns:
        RepresentativeFrame or None if no valid frames
    """
    valid = [r for r in results if r.error is None]
    if not valid:
        return None

    # Prefer frames with detections
    with_detections = [r for r in valid if r.detections]
    candidates = with_detections if with_detections else valid

    # Select by highest total confidence
    best = max(
        candidates,
        key=lambda r: sum(d.confidence for d in r.detections) if r.detections else 0,
    )

    return RepresentativeFrame(
        frame_idx=best.frame_idx,
        image_path=best.image_path,
        timestamp_s=best.timestamp_s,
    )


# ---------------------------------------------------------------------------
# Construction site counting aggregation
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class FrameCount:
    """Per-frame counts of equipment and personnel.

    Attributes:
        frame_idx: Frame index in the sequence
        timestamp_s: Timestamp in seconds
        timestamp_ts: Formatted timestamp string
        equipment_counts: Counts by EquipmentClass
        person_count: Total people detected
        hardhat_counts: Counts by HardhatColor
    """

    frame_idx: int
    timestamp_s: float
    timestamp_ts: str
    equipment_counts: dict[str, int]  # EquipmentClass.value -> count
    person_count: int
    hardhat_counts: dict[str, int]  # HardhatColor.value -> count

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "frame_idx": self.frame_idx,
            "timestamp_s": self.timestamp_s,
            "timestamp_ts": self.timestamp_ts,
            "equipment_counts": self.equipment_counts,
            "person_count": self.person_count,
            "hardhat_counts": self.hardhat_counts,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "FrameCount":
        """Create FrameCount from dictionary."""
        return cls(
            frame_idx=int(data["frame_idx"]),
            timestamp_s=float(data["timestamp_s"]),
            timestamp_ts=str(data["timestamp_ts"]),
            equipment_counts=dict(data.get("equipment_counts", {})),
            person_count=int(data.get("person_count", 0)),
            hardhat_counts=dict(data.get("hardhat_counts", {})),
        )


@dataclass(frozen=True, slots=True)
class SiteCountSummary:
    """Summary statistics across all frames.

    Attributes:
        peak_equipment: Peak count per equipment type across all frames
        peak_persons: Peak person count in any single frame
        peak_hardhats: Peak count per hardhat color across all frames
        avg_persons: Average person count across frames
        total_frames: Number of frames analyzed
    """

    peak_equipment: dict[str, int]
    peak_persons: int
    peak_hardhats: dict[str, int]
    avg_persons: float
    total_frames: int

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "peak_equipment": self.peak_equipment,
            "peak_persons": self.peak_persons,
            "peak_hardhats": self.peak_hardhats,
            "avg_persons": round(self.avg_persons, 2),
            "total_frames": self.total_frames,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SiteCountSummary":
        """Create SiteCountSummary from dictionary."""
        return cls(
            peak_equipment=dict(data.get("peak_equipment", {})),
            peak_persons=int(data.get("peak_persons", 0)),
            peak_hardhats=dict(data.get("peak_hardhats", {})),
            avg_persons=float(data.get("avg_persons", 0.0)),
            total_frames=int(data.get("total_frames", 0)),
        )


@dataclass(frozen=True, slots=True)
class SiteCountTimeSeries:
    """Time series of per-frame counts with summary statistics.

    Attributes:
        engine: Engine info for traceability
        frames: Per-frame counts ordered by timestamp
        summary: Aggregate statistics
    """

    engine: EngineInfo
    frames: tuple[FrameCount, ...]
    summary: SiteCountSummary

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "engine": self.engine.to_dict(),
            "frames": [f.to_dict() for f in self.frames],
            "summary": self.summary.to_dict(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SiteCountTimeSeries":
        """Create SiteCountTimeSeries from dictionary."""
        return cls(
            engine=EngineInfo.from_dict(data["engine"]),
            frames=tuple(FrameCount.from_dict(f) for f in data.get("frames", [])),
            summary=SiteCountSummary.from_dict(data.get("summary", {})),
        )


def _count_frame(result: FrameAnalyticsResult) -> FrameCount:
    """Extract counts from a single frame's detections.

    Args:
        result: Frame analytics result with detections

    Returns:
        FrameCount for this frame
    """
    equipment_counts: dict[str, int] = defaultdict(int)
    person_count = 0
    hardhat_counts: dict[str, int] = defaultdict(int)

    for det in result.detections:
        if det.detection_type == DetectionType.CONSTRUCTION_EQUIPMENT:
            eq_class = (
                det.attributes.equipment_class.value
                if det.attributes.equipment_class
                else EquipmentClass.OTHER.value
            )
            equipment_counts[eq_class] += 1

        elif det.detection_type == DetectionType.PERSON:
            person_count += 1

        elif det.detection_type == DetectionType.HARDHAT:
            hc = (
                det.attributes.hardhat_color.value
                if det.attributes.hardhat_color
                else HardhatColor.OTHER.value
            )
            hardhat_counts[hc] += 1

    return FrameCount(
        frame_idx=result.frame_idx,
        timestamp_s=result.timestamp_s,
        timestamp_ts=result.timestamp_ts,
        equipment_counts=dict(equipment_counts),
        person_count=person_count,
        hardhat_counts=dict(hardhat_counts),
    )


def aggregate_site_counts(
    results: list[FrameAnalyticsResult],
    engine_info: EngineInfo,
) -> SiteCountTimeSeries:
    """Aggregate per-frame detections into a site count time series.

    Args:
        results: List of frame analytics results (should be sorted by timestamp)
        engine_info: Engine information for traceability

    Returns:
        SiteCountTimeSeries with per-frame counts and summary
    """
    valid = [r for r in results if r.error is None]
    frame_counts = [_count_frame(r) for r in valid]

    # Sort by timestamp
    frame_counts.sort(key=lambda fc: fc.timestamp_s)

    if not frame_counts:
        return SiteCountTimeSeries(
            engine=engine_info,
            frames=(),
            summary=SiteCountSummary(
                peak_equipment={},
                peak_persons=0,
                peak_hardhats={},
                avg_persons=0.0,
                total_frames=0,
            ),
        )

    # Compute peaks
    peak_equipment: dict[str, int] = defaultdict(int)
    peak_hardhats: dict[str, int] = defaultdict(int)
    peak_persons = 0
    total_persons = 0

    for fc in frame_counts:
        for eq, count in fc.equipment_counts.items():
            peak_equipment[eq] = max(peak_equipment[eq], count)
        for hc, count in fc.hardhat_counts.items():
            peak_hardhats[hc] = max(peak_hardhats[hc], count)
        peak_persons = max(peak_persons, fc.person_count)
        total_persons += fc.person_count

    avg_persons = total_persons / len(frame_counts) if frame_counts else 0.0

    return SiteCountTimeSeries(
        engine=engine_info,
        frames=tuple(frame_counts),
        summary=SiteCountSummary(
            peak_equipment=dict(peak_equipment),
            peak_persons=peak_persons,
            peak_hardhats=dict(peak_hardhats),
            avg_persons=avg_persons,
            total_frames=len(frame_counts),
        ),
    )
