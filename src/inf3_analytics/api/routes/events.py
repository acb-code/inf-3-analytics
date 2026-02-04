"""Event management endpoints."""

import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, status

from inf3_analytics.api.config import Settings, get_settings
from inf3_analytics.api.dependencies import get_run_or_404, validate_path_security
from inf3_analytics.api.models import (
    CreateCommentRequest,
    CreateEventRequest,
    EventCommentResponse,
    RunMetadata,
)
from inf3_analytics.io.comment_writer import (
    add_comment,
    delete_comment,
    get_comments_for_event,
)
from inf3_analytics.io.event_writer import read_json as read_events_json
from inf3_analytics.io.event_writer import write_json as write_events_json
from inf3_analytics.types.event import (
    Event,
    EventList,
    EventMetadata,
    EventSeverity,
    EventType,
    TranscriptReference,
)

router = APIRouter(prefix="/runs/{run_id}/events", tags=["events"])


def _get_events_path(run: RunMetadata) -> Path:
    """Get the path to the events file for a run."""
    run_root = Path(run.run_root)
    return run_root / "events" / f"{run.video_basename}_events.json"


def _format_timestamp(seconds: float) -> str:
    """Format seconds as HH:MM:SS.mmm timestamp."""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = seconds % 60
    return f"{hours:02d}:{minutes:02d}:{secs:06.3f}"


@router.post("", status_code=status.HTTP_201_CREATED)
def create_event(
    request: CreateEventRequest,
    run: Annotated[RunMetadata, Depends(get_run_or_404)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> dict[str, Any]:
    """Create a manual event."""
    run_root = Path(run.run_root)
    validate_path_security(run_root, settings)

    events_path = _get_events_path(run)

    # Read existing events or create new list
    if events_path.exists():
        event_list = read_events_json(events_path)
        existing_events = list(event_list.events)
    else:
        existing_events = []

    # Create new event
    event_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()

    new_event = Event(
        event_id=event_id,
        event_type=EventType(request.event_type),
        severity=EventSeverity(request.severity) if request.severity else None,
        confidence=1.0,  # Manual events have full confidence
        start_s=request.start_s,
        end_s=request.end_s,
        start_ts=_format_timestamp(request.start_s),
        end_ts=_format_timestamp(request.end_s),
        title=request.title,
        summary=request.summary,
        transcript_ref=TranscriptReference(
            segment_ids=(),
            excerpt="",
            keywords=None,
        ),
        suggested_actions=None,
        metadata=EventMetadata(
            extractor_engine="manual",
            extractor_version="1.0.0",
            created_at=now,
            source_transcript_path=None,
            source="manual",
        ),
        related_rule_events=None,
    )

    # Add and save
    existing_events.append(new_event)
    existing_events.sort(key=lambda e: e.start_s)

    new_event_list = EventList(
        events=tuple(existing_events),
        source_transcript_path=event_list.source_transcript_path if events_path.exists() else None,
        extraction_engine="mixed" if events_path.exists() else "manual",
        extraction_timestamp=now,
    )
    write_events_json(new_event_list, events_path)

    return new_event.to_dict()


@router.delete("/{event_id}", status_code=status.HTTP_200_OK)
def delete_event(
    event_id: str,
    run: Annotated[RunMetadata, Depends(get_run_or_404)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> dict[str, str]:
    """Delete an event."""
    run_root = Path(run.run_root)
    validate_path_security(run_root, settings)

    events_path = _get_events_path(run)

    if not events_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No events file found",
        )

    event_list = read_events_json(events_path)
    remaining_events = [e for e in event_list.events if e.event_id != event_id]

    if len(remaining_events) == len(event_list.events):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Event {event_id} not found",
        )

    new_event_list = EventList(
        events=tuple(remaining_events),
        source_transcript_path=event_list.source_transcript_path,
        extraction_engine=event_list.extraction_engine,
        extraction_timestamp=datetime.now(timezone.utc).isoformat(),
    )
    write_events_json(new_event_list, events_path)

    return {"message": "Event deleted", "event_id": event_id}


@router.get("/{event_id}/comments", response_model=list[EventCommentResponse])
def get_event_comments(
    event_id: str,
    run: Annotated[RunMetadata, Depends(get_run_or_404)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> list[EventCommentResponse]:
    """Get all comments for an event."""
    run_root = Path(run.run_root)
    validate_path_security(run_root, settings)

    comments = get_comments_for_event(run_root, event_id)
    return [
        EventCommentResponse(
            comment_id=c.comment_id,
            event_id=c.event_id,
            text=c.text,
            created_at=c.created_at,
        )
        for c in comments
    ]


@router.post("/{event_id}/comments", status_code=status.HTTP_201_CREATED)
def create_comment(
    event_id: str,
    request: CreateCommentRequest,
    run: Annotated[RunMetadata, Depends(get_run_or_404)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> EventCommentResponse:
    """Add a comment to an event."""
    run_root = Path(run.run_root)
    validate_path_security(run_root, settings)

    comment = add_comment(run_root, event_id, request.text)
    return EventCommentResponse(
        comment_id=comment.comment_id,
        event_id=comment.event_id,
        text=comment.text,
        created_at=comment.created_at,
    )


@router.delete("/{event_id}/comments/{comment_id}", status_code=status.HTTP_200_OK)
def remove_comment(
    event_id: str,
    comment_id: str,
    run: Annotated[RunMetadata, Depends(get_run_or_404)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> dict[str, str]:
    """Delete a comment."""
    run_root = Path(run.run_root)
    validate_path_security(run_root, settings)

    deleted = delete_comment(run_root, comment_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Comment {comment_id} not found",
        )

    return {"message": "Comment deleted", "comment_id": comment_id}
