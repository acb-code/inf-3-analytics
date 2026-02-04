"""Comment data types for event annotations."""

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class EventComment:
    """A user comment on an event."""

    comment_id: str
    event_id: str
    text: str
    created_at: str

    def to_dict(self) -> dict[str, str]:
        """Convert to dictionary for serialization."""
        return {
            "comment_id": self.comment_id,
            "event_id": self.event_id,
            "text": self.text,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "EventComment":
        """Create EventComment from dictionary."""
        return cls(
            comment_id=str(data["comment_id"]),
            event_id=str(data["event_id"]),
            text=str(data["text"]),
            created_at=str(data["created_at"]),
        )


@dataclass(frozen=True, slots=True)
class CommentStore:
    """Collection of comments for a run."""

    comments: tuple[EventComment, ...]

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "comments": [c.to_dict() for c in self.comments],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CommentStore":
        """Create CommentStore from dictionary."""
        comments_data = data.get("comments", [])
        if not isinstance(comments_data, list):
            raise ValueError("comments must be a list")
        return cls(
            comments=tuple(EventComment.from_dict(c) for c in comments_data),
        )
