"""Pydantic request/response models for the API."""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class RunStatus(str, Enum):
    """Status of a pipeline run."""

    CREATED = "created"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


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
