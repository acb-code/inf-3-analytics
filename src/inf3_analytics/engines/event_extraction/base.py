"""Base classes and protocols for event extraction engines."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol, runtime_checkable

from inf3_analytics.types.event import Event
from inf3_analytics.types.transcript import Transcript


@dataclass
class EventExtractionConfig:
    """Configuration for event extraction engines."""

    # Window settings
    context_window: int = 1
    min_confidence: float = 0.3
    merge_gap_s: float = 5.0

    # Rule engine settings
    keywords_file: Path | None = None

    # LLM engine settings
    llm_engine: str | None = None
    llm_model: str = "gpt-5-mini"
    max_segments_per_batch: int = 20
    llm_batch_overlap: int = 1

    def __post_init__(self) -> None:
        """Validate configuration values."""
        if self.context_window < 0:
            raise ValueError(
                f"Invalid context_window: {self.context_window}. Must be >= 0"
            )
        if not 0.0 <= self.min_confidence <= 1.0:
            raise ValueError(
                f"Invalid min_confidence: {self.min_confidence}. Must be between 0.0 and 1.0"
            )
        if self.merge_gap_s < 0:
            raise ValueError(
                f"Invalid merge_gap_s: {self.merge_gap_s}. Must be >= 0"
            )
        if self.llm_batch_overlap < 0:
            raise ValueError(
                f"Invalid llm_batch_overlap: {self.llm_batch_overlap}. Must be >= 0"
            )


@runtime_checkable
class EventExtractionEngine(Protocol):
    """Protocol for event extraction engines."""

    def load(self) -> None:
        """Initialize engine resources."""
        ...

    def extract(self, transcript: Transcript) -> tuple[Event, ...]:
        """Extract events from transcript.

        Args:
            transcript: Transcript to analyze

        Returns:
            Tuple of extracted events
        """
        ...

    def unload(self) -> None:
        """Release engine resources."""
        ...

    @property
    def is_loaded(self) -> bool:
        """Check if engine is ready."""
        ...


class BaseEventExtractionEngine(ABC):
    """Abstract base class for event extraction engines with context manager support."""

    def __init__(self, config: EventExtractionConfig | None = None) -> None:
        """Initialize the engine with configuration.

        Args:
            config: Event extraction configuration (uses defaults if None)
        """
        self.config = config or EventExtractionConfig()
        self._loaded = False

    @abstractmethod
    def load(self) -> None:
        """Initialize engine resources."""
        pass

    @abstractmethod
    def extract(self, transcript: Transcript) -> tuple[Event, ...]:
        """Extract events from transcript.

        Args:
            transcript: Transcript to analyze

        Returns:
            Tuple of extracted events
        """
        pass

    @abstractmethod
    def unload(self) -> None:
        """Release engine resources."""
        pass

    @property
    def is_loaded(self) -> bool:
        """Check if engine is ready."""
        return self._loaded

    def __enter__(self) -> "BaseEventExtractionEngine":
        """Context manager entry - initializes engine."""
        self.load()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: object,
    ) -> None:
        """Context manager exit - releases engine resources."""
        self.unload()
