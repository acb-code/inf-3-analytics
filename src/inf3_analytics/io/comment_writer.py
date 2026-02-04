"""Comment read/write utilities."""

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from inf3_analytics.types.comment import CommentStore, EventComment


def get_comments_path(run_root: Path) -> Path:
    """Get the path to the comments file for a run."""
    return run_root / "events" / "comments.json"


def read_comments(run_root: Path) -> CommentStore:
    """Read comments from the comments file.

    Args:
        run_root: Root directory of the run

    Returns:
        CommentStore with all comments, or empty store if file doesn't exist
    """
    path = get_comments_path(run_root)
    if not path.exists():
        return CommentStore(comments=())

    with open(path, encoding="utf-8") as f:
        data: dict[str, Any] = json.load(f)
    return CommentStore.from_dict(data)


def write_comments(run_root: Path, store: CommentStore) -> None:
    """Write comments to the comments file.

    Args:
        run_root: Root directory of the run
        store: CommentStore to serialize
    """
    path = get_comments_path(run_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(store.to_dict(), f, indent=2, ensure_ascii=False)


def add_comment(run_root: Path, event_id: str, text: str) -> EventComment:
    """Add a new comment to an event.

    Args:
        run_root: Root directory of the run
        event_id: ID of the event to comment on
        text: Comment text

    Returns:
        The created EventComment
    """
    store = read_comments(run_root)
    comment = EventComment(
        comment_id=str(uuid.uuid4()),
        event_id=event_id,
        text=text,
        created_at=datetime.now(timezone.utc).isoformat(),
    )
    new_store = CommentStore(comments=store.comments + (comment,))
    write_comments(run_root, new_store)
    return comment


def delete_comment(run_root: Path, comment_id: str) -> bool:
    """Delete a comment by ID.

    Args:
        run_root: Root directory of the run
        comment_id: ID of the comment to delete

    Returns:
        True if comment was found and deleted, False otherwise
    """
    store = read_comments(run_root)
    new_comments = tuple(c for c in store.comments if c.comment_id != comment_id)
    if len(new_comments) == len(store.comments):
        return False
    write_comments(run_root, CommentStore(comments=new_comments))
    return True


def get_comments_for_event(run_root: Path, event_id: str) -> list[EventComment]:
    """Get all comments for a specific event.

    Args:
        run_root: Root directory of the run
        event_id: ID of the event

    Returns:
        List of comments for the event, sorted by creation time
    """
    store = read_comments(run_root)
    return sorted(
        [c for c in store.comments if c.event_id == event_id],
        key=lambda c: c.created_at,
    )
