"""Base classes and protocols for transcription engines."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol, runtime_checkable

from inf3_analytics.types.transcript import Transcript


@dataclass
class TranscriptionConfig:
    """Configuration for transcription engines."""

    model_name: str = "base"
    language: str | None = None
    word_timestamps: bool = True
    beam_size: int = 5
    vad_filter: bool = True
    device: str = "auto"
    compute_type: str = "default"
    initial_prompt: str | None = None
    temperature: float | tuple[float, ...] = field(
        default_factory=lambda: (0.0, 0.2, 0.4, 0.6, 0.8, 1.0)
    )

    def __post_init__(self) -> None:
        """Validate configuration values."""
        valid_devices = {"auto", "cpu", "cuda"}
        if self.device not in valid_devices:
            raise ValueError(f"Invalid device: {self.device}. Must be one of {valid_devices}")

        valid_compute_types = {
            "default",
            "auto",
            "int8",
            "int8_float16",
            "int8_float32",
            "int8_bfloat16",
            "int16",
            "float16",
            "bfloat16",
            "float32",
        }
        if self.compute_type not in valid_compute_types:
            raise ValueError(
                f"Invalid compute_type: {self.compute_type}. "
                f"Must be one of {valid_compute_types}"
            )


@runtime_checkable
class TranscriptionEngine(Protocol):
    """Protocol for transcription engines."""

    def load(self) -> None:
        """Load the transcription model into memory."""
        ...

    def transcribe(self, audio_path: Path, source_video: Path | None = None) -> Transcript:
        """Transcribe audio file to text.

        Args:
            audio_path: Path to the audio file
            source_video: Optional path to the original video file

        Returns:
            Transcript with segments and metadata
        """
        ...

    def unload(self) -> None:
        """Unload the model from memory."""
        ...

    @property
    def is_loaded(self) -> bool:
        """Check if the model is currently loaded."""
        ...


class BaseTranscriptionEngine(ABC):
    """Abstract base class for transcription engines with context manager support."""

    def __init__(self, config: TranscriptionConfig | None = None) -> None:
        """Initialize the engine with configuration.

        Args:
            config: Transcription configuration (uses defaults if None)
        """
        self.config = config or TranscriptionConfig()
        self._loaded = False

    @abstractmethod
    def load(self) -> None:
        """Load the transcription model into memory."""
        pass

    @abstractmethod
    def transcribe(self, audio_path: Path, source_video: Path | None = None) -> Transcript:
        """Transcribe audio file to text.

        Args:
            audio_path: Path to the audio file
            source_video: Optional path to the original video file

        Returns:
            Transcript with segments and metadata
        """
        pass

    @abstractmethod
    def unload(self) -> None:
        """Unload the model from memory."""
        pass

    @property
    def is_loaded(self) -> bool:
        """Check if the model is currently loaded."""
        return self._loaded

    def __enter__(self) -> "BaseTranscriptionEngine":
        """Context manager entry - loads the model."""
        self.load()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: object,
    ) -> None:
        """Context manager exit - unloads the model."""
        self.unload()
