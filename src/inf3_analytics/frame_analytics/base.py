"""Base classes and protocols for frame analytics engines."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

if TYPE_CHECKING:
    from inf3_analytics.types.detection import FrameAnalyticsResult, FrameMeta
    from inf3_analytics.types.event import Event


@dataclass
class AnalyticsConfig:
    """Configuration for frame analytics engines."""

    # Rate limiting
    max_frames_per_event: int = 10
    sleep_ms_between_requests: int = 200
    max_total_frames: int = 100

    # Retry settings
    max_retries: int = 2
    retry_delay_ms: int = 1000

    # VLM specific
    temperature: float = 0.2
    max_tokens: int = 2048

    # Fallback
    fallback_to_baseline: bool = False

    # Model override
    model_name: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert config to dictionary for traceability."""
        return {
            "max_frames_per_event": self.max_frames_per_event,
            "sleep_ms_between_requests": self.sleep_ms_between_requests,
            "max_total_frames": self.max_total_frames,
            "max_retries": self.max_retries,
            "retry_delay_ms": self.retry_delay_ms,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "fallback_to_baseline": self.fallback_to_baseline,
            "model_name": self.model_name,
        }


@runtime_checkable
class FrameAnalyticsEngine(Protocol):
    """Protocol for frame analytics engines."""

    @property
    def is_loaded(self) -> bool:
        """Return True if the engine is loaded and ready."""
        ...

    def load(self) -> None:
        """Load engine resources (model, API client, etc.)."""
        ...

    def unload(self) -> None:
        """Release engine resources."""
        ...

    def analyze(
        self,
        image_path: Path,
        *,
        event: "Event | None",
        frame_meta: "FrameMeta",
        **kwargs: Any,
    ) -> "FrameAnalyticsResult":
        """Analyze a single frame.

        Args:
            image_path: Path to the image file
            event: Optional event context for the frame
            frame_meta: Metadata about the frame
            **kwargs: Additional engine-specific arguments

        Returns:
            FrameAnalyticsResult with detections and analysis
        """
        ...


@dataclass
class BaseFrameAnalyticsEngine(ABC):
    """Base class for frame analytics engines.

    Provides common functionality and lifecycle management.
    Subclasses must implement load(), unload(), and analyze().
    """

    config: AnalyticsConfig = field(default_factory=AnalyticsConfig)
    _loaded: bool = field(default=False, init=False, repr=False)

    @property
    def is_loaded(self) -> bool:
        """Return True if the engine is loaded."""
        return self._loaded

    def __enter__(self) -> "BaseFrameAnalyticsEngine":
        """Context manager entry - loads the engine."""
        self.load()
        return self

    def __exit__(self, *args: Any) -> None:
        """Context manager exit - unloads the engine."""
        self.unload()

    @abstractmethod
    def load(self) -> None:
        """Load engine resources.

        Must set self._loaded = True on success.
        """
        ...

    @abstractmethod
    def unload(self) -> None:
        """Release engine resources.

        Must set self._loaded = False.
        """
        ...

    @abstractmethod
    def analyze(
        self,
        image_path: Path,
        *,
        event: "Event | None",
        frame_meta: "FrameMeta",
        **kwargs: Any,
    ) -> "FrameAnalyticsResult":
        """Analyze a single frame.

        Args:
            image_path: Path to the image file
            event: Optional event context for the frame
            frame_meta: Metadata about the frame
            **kwargs: Additional engine-specific arguments

        Returns:
            FrameAnalyticsResult with detections and analysis
        """
        ...

    @abstractmethod
    def get_engine_info(self) -> "EngineInfo":
        """Get engine information for traceability.

        Returns:
            EngineInfo with engine details
        """
        ...


# Import here to avoid circular import
from inf3_analytics.types.detection import EngineInfo  # noqa: E402
