"""Pydantic request/response models for the API."""

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class RunStatus(str, Enum):
    """Status of a pipeline run."""

    CREATED = "created"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class PipelineStep(str, Enum):
    """Steps in the analytics pipeline."""

    TRANSCRIBE = "transcribe"
    EXTRACT_EVENTS = "extract_events"
    EXTRACT_FRAMES = "extract_frames"
    FRAME_ANALYTICS = "frame_analytics"


class StepStatus(str, Enum):
    """Status of a pipeline step."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class ArtifactType(str, Enum):
    """Types of artifacts produced by the pipeline."""

    TRANSCRIPT = "transcript"
    EVENTS = "events"
    EVENT_FRAMES_MANIFEST = "event_frames_manifest"
    FRAME_ANALYTICS_MANIFEST = "frame_analytics_manifest"


# Request models


class CreateRunRequest(BaseModel):
    """Request to create a new run."""

    video_path: str = Field(..., description="Path to the video file")
    run_root: str = Field(..., description="Directory for pipeline outputs")
    run_id: str | None = Field(None, description="Optional custom run ID")


# Response models


class RunMetadata(BaseModel):
    """Metadata for a pipeline run."""

    run_id: str
    video_path: str
    run_root: str
    video_basename: str
    status: RunStatus
    created_at: datetime
    language: str = "en"


class ArtifactInfo(BaseModel):
    """Information about an artifact."""

    type: ArtifactType
    available: bool
    url: str | None = None


class RunDetailResponse(BaseModel):
    """Detailed response for a single run."""

    run: RunMetadata
    artifacts: list[ArtifactInfo]


class RunListResponse(BaseModel):
    """Response containing list of runs."""

    runs: list[RunMetadata]


class TranscriptResponse(BaseModel):
    """Transcript artifact response."""

    full_text: str
    segments: list[dict[str, Any]]
    metadata: dict[str, Any]


class EventsResponse(BaseModel):
    """Events artifact response."""

    events: list[dict[str, Any]]
    source_transcript_path: str | None = None
    extraction_engine: str
    extraction_timestamp: str


class EventFramesManifestResponse(BaseModel):
    """Event frames manifest response."""

    event_frame_sets: list[dict[str, Any]]
    metadata: dict[str, Any]
    total_frames: int
    total_events: int
    successful_events: int
    skipped_events: int
    failed_events: int


class FrameAnalyticsManifestResponse(BaseModel):
    """Frame analytics manifest response."""

    run_id: str
    engine: dict[str, Any]
    source_event_frames_manifest: str
    events_file: str | None
    total_events: int
    total_frames: int
    analyzed_frames: int
    failed_frames: int
    created_at: str
    event_summaries: list[str]


class FrameAnalyticsEventResponse(BaseModel):
    """Frame analytics response for a single event."""

    event_id: str
    frame_analyses: list[dict[str, Any]]
    event_summary: dict[str, Any] | None


# Pipeline models


class PipelineStepInfo(BaseModel):
    """Information about a pipeline step."""

    step: PipelineStep
    status: StepStatus
    started_at: datetime | None = None
    completed_at: datetime | None = None
    error_message: str | None = None
    output: str | None = None
    progress_current: int | None = None
    progress_total: int | None = None
    progress_unit: str | None = None
    progress_message: str | None = None
    pid: int | None = None


class PipelineStatusResponse(BaseModel):
    """Response for pipeline status."""

    run_id: str
    run_status: RunStatus
    steps: list[PipelineStepInfo]
    progress_percent: int = Field(..., ge=0, le=100)


class UploadResponse(BaseModel):
    """Response after successful video upload."""

    run_id: str
    video_path: str
    run_root: str
    message: str
    language: str = "en"


class TriggerPipelineRequest(BaseModel):
    """Request to trigger pipeline execution."""

    steps: list[PipelineStep] | None = Field(
        default=None, description="Steps to run (default: all steps)"
    )
    transcription_engine: str = Field(
        default="openai", description="Transcription engine: openai, gemini, faster-whisper"
    )
    event_engine: str = Field(
        default="openai", description="Event extraction engine: openai, gemini, rules"
    )
    frame_analytics_engine: str = Field(
        default="gemini", description="Frame analytics engine: gemini, openai, baseline_quality"
    )
    language: str = Field(
        default="en", description="Language code: en (English), fr (French)"
    )


# Decomposition models


class SplitPointResponse(BaseModel):
    """A suggested split point."""

    timestamp_s: float
    timestamp_ts: str
    type: str  # "silence", "scene", "interval", "user"
    keyframe_s: float
    confidence: float


class SegmentPreview(BaseModel):
    """Preview of a segment before decomposition."""

    index: int
    start_s: float
    end_s: float
    duration_s: float
    start_ts: str
    end_ts: str
    estimated_size_mb: float


class DecompositionPlanResponse(BaseModel):
    """Response from analyzing a video for decomposition."""

    video_path: str
    duration_s: float
    duration_ts: str
    file_size_mb: float
    suggested_splits: list[SplitPointResponse]
    estimated_segments: list[SegmentPreview]


class AnalyzeDecompositionRequest(BaseModel):
    """Request to analyze a video for decomposition."""

    video_path: str = Field(..., description="Path to the video file")
    target_segment_duration_s: float = Field(
        default=300, description="Target segment duration in seconds (default 5 min)"
    )
    silence_threshold_db: float = Field(
        default=-35, description="Silence detection threshold in dB"
    )


class ExecuteDecompositionRequest(BaseModel):
    """Request to execute video decomposition."""

    video_path: str = Field(..., description="Path to the video file")
    split_timestamps: list[float] = Field(
        ..., description="Timestamps where to split the video"
    )
    create_child_runs: bool = Field(
        default=True, description="Create separate runs for each segment"
    )
    parent_run_id: str | None = Field(
        default=None, description="Parent run ID (optional)"
    )


class SegmentResultResponse(BaseModel):
    """Result of creating a single segment."""

    index: int
    path: str
    start_s: float
    end_s: float
    duration_s: float
    file_size_mb: float
    child_run_id: str | None


class DecompositionJobStatus(str, Enum):
    """Status of a decomposition job."""

    ANALYZING = "analyzing"
    SPLITTING = "splitting"
    CREATING_RUNS = "creating_runs"
    COMPLETED = "completed"
    FAILED = "failed"


class DecompositionStatusResponse(BaseModel):
    """Status of a decomposition job."""

    job_id: str
    status: DecompositionJobStatus
    progress_current: int
    progress_total: int
    progress_message: str | None = None
    segments_created: list[SegmentResultResponse] = []
    child_run_ids: list[str] = []
    error_message: str | None = None


class DecompositionJobResponse(BaseModel):
    """Response when starting a decomposition job."""

    job_id: str
    message: str
    status_url: str


# Event management models


class CreateEventRequest(BaseModel):
    """Request to create a manual event."""

    start_s: float = Field(..., description="Start time in seconds")
    end_s: float = Field(..., description="End time in seconds")
    event_type: str = Field(..., description="Event type (e.g., observation, structural_anomaly)")
    severity: str | None = Field(None, description="Severity level (low, medium, high)")
    title: str = Field(..., description="Event title")
    summary: str = Field(..., description="Event summary/description")


class CreateCommentRequest(BaseModel):
    """Request to create a comment on an event."""

    text: str = Field(..., description="Comment text")


class EventCommentResponse(BaseModel):
    """Response for a single comment."""

    comment_id: str
    event_id: str
    text: str
    created_at: str
