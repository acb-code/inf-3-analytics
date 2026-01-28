"""Aggregation logic for event-level analytics summaries."""

from collections import defaultdict
from datetime import datetime

from inf3_analytics.types.detection import (
    AggregatedConfidence,
    DetectionType,
    EngineInfo,
    EventAnalyticsSummary,
    Finding,
    FrameAnalyticsResult,
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
