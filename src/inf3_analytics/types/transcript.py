"""Transcript data types for video transcription."""

from dataclasses import dataclass
from enum import Enum
from pathlib import Path


class TranscriptionEngineType(Enum):
    """Supported transcription engine types."""

    FASTER_WHISPER = "faster-whisper"
    OPENAI = "openai"
    GEMINI = "gemini"


@dataclass(frozen=True, slots=True)
class Word:
    """A single transcribed word with timing and confidence."""

    word: str
    start_s: float
    end_s: float
    probability: float

    def to_dict(self) -> dict[str, str | float]:
        """Convert to dictionary for serialization."""
        return {
            "word": self.word,
            "start_s": self.start_s,
            "end_s": self.end_s,
            "probability": self.probability,
        }

    @classmethod
    def from_dict(cls, data: dict[str, str | float]) -> "Word":
        """Create Word from dictionary."""
        return cls(
            word=str(data["word"]),
            start_s=float(data["start_s"]),
            end_s=float(data["end_s"]),
            probability=float(data["probability"]),
        )


@dataclass(frozen=True, slots=True)
class Segment:
    """A transcript segment with timing and metadata."""

    id: int
    start_s: float
    end_s: float
    start_ts: str
    end_ts: str
    text: str
    words: tuple[Word, ...] | None
    avg_logprob: float
    no_speech_prob: float

    def to_dict(self) -> dict[str, int | float | str | list[dict[str, str | float]] | None]:
        """Convert to dictionary for serialization."""
        return {
            "id": self.id,
            "start_s": self.start_s,
            "end_s": self.end_s,
            "start_ts": self.start_ts,
            "end_ts": self.end_ts,
            "text": self.text,
            "words": [w.to_dict() for w in self.words] if self.words else None,
            "avg_logprob": self.avg_logprob,
            "no_speech_prob": self.no_speech_prob,
        }

    @classmethod
    def from_dict(
        cls, data: dict[str, int | float | str | list[dict[str, str | float]] | None]
    ) -> "Segment":
        """Create Segment from dictionary."""
        words_data = data.get("words")
        words = None
        if words_data is not None and isinstance(words_data, list):
            words = tuple(Word.from_dict(w) for w in words_data)

        return cls(
            id=int(data["id"]),  # type: ignore[arg-type]
            start_s=float(data["start_s"]),  # type: ignore[arg-type]
            end_s=float(data["end_s"]),  # type: ignore[arg-type]
            start_ts=str(data["start_ts"]),
            end_ts=str(data["end_ts"]),
            text=str(data["text"]),
            words=words,
            avg_logprob=float(data["avg_logprob"]),  # type: ignore[arg-type]
            no_speech_prob=float(data["no_speech_prob"]),  # type: ignore[arg-type]
        )


@dataclass(frozen=True, slots=True)
class TranscriptMetadata:
    """Metadata about the transcription process."""

    engine: TranscriptionEngineType
    model_name: str
    language: str | None
    detected_language: str | None
    language_probability: float | None
    duration_s: float
    source_video: Path | None
    source_audio: Path | None

    def to_dict(self) -> dict[str, str | float | None]:
        """Convert to dictionary for serialization."""
        return {
            "engine": self.engine.value,
            "model_name": self.model_name,
            "language": self.language,
            "detected_language": self.detected_language,
            "language_probability": self.language_probability,
            "duration_s": self.duration_s,
            "source_video": str(self.source_video) if self.source_video else None,
            "source_audio": str(self.source_audio) if self.source_audio else None,
        }

    @classmethod
    def from_dict(cls, data: dict[str, str | float | None]) -> "TranscriptMetadata":
        """Create TranscriptMetadata from dictionary."""
        engine_value = data["engine"]
        engine = TranscriptionEngineType(engine_value)

        source_video = data.get("source_video")
        source_audio = data.get("source_audio")

        return cls(
            engine=engine,
            model_name=str(data["model_name"]),
            language=str(data["language"]) if data.get("language") else None,
            detected_language=(
                str(data["detected_language"]) if data.get("detected_language") else None
            ),
            language_probability=(
                float(data["language_probability"])  # type: ignore[arg-type]
                if data.get("language_probability") is not None
                else None
            ),
            duration_s=float(data["duration_s"]),  # type: ignore[arg-type]
            source_video=Path(str(source_video)) if source_video else None,
            source_audio=Path(str(source_audio)) if source_audio else None,
        )


@dataclass(frozen=True, slots=True)
class Transcript:
    """Complete transcript with segments and metadata."""

    full_text: str
    segments: tuple[Segment, ...]
    metadata: TranscriptMetadata

    def to_dict(
        self,
    ) -> dict[
        str,
        str
        | list[dict[str, int | float | str | list[dict[str, str | float]] | None]]
        | dict[str, str | float | None],
    ]:
        """Convert to dictionary for serialization."""
        return {
            "full_text": self.full_text,
            "segments": [s.to_dict() for s in self.segments],
            "metadata": self.metadata.to_dict(),
        }

    @classmethod
    def from_dict(
        cls,
        data: dict[
            str,
            str
            | list[dict[str, int | float | str | list[dict[str, str | float]] | None]]
            | dict[str, str | float | None],
        ],
    ) -> "Transcript":
        """Create Transcript from dictionary."""
        segments_data = data["segments"]
        if not isinstance(segments_data, list):
            raise ValueError("segments must be a list")

        metadata_data = data["metadata"]
        if not isinstance(metadata_data, dict):
            raise ValueError("metadata must be a dict")

        return cls(
            full_text=str(data["full_text"]),
            segments=tuple(Segment.from_dict(s) for s in segments_data),
            metadata=TranscriptMetadata.from_dict(metadata_data),
        )
