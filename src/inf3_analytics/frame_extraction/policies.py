"""Frame sampling policies for event-based extraction."""

from typing import Protocol


class FrameSamplingPolicy(Protocol):
    """Protocol for frame sampling strategies."""

    @property
    def name(self) -> str:
        """Name of the policy."""
        ...

    @property
    def params(self) -> dict[str, int | float]:
        """Policy parameters for serialization."""
        ...

    def compute_timestamps(
        self, start_s: float, end_s: float, video_duration_s: float
    ) -> tuple[float, ...]:
        """Compute timestamps to extract within the event window.

        Args:
            start_s: Event start time in seconds
            end_s: Event end time in seconds
            video_duration_s: Total video duration for clamping

        Returns:
            Tuple of timestamps to extract
        """
        ...


class NFramesPerEventPolicy:
    """Extract N evenly-spaced frames within each event window.

    - N=1: Returns the midpoint
    - N=2: Returns start and end
    - N>2: Returns evenly spaced frames including endpoints
    """

    def __init__(self, n: int = 5) -> None:
        """Initialize policy.

        Args:
            n: Number of frames to extract per event (default: 5)
        """
        if n < 1:
            raise ValueError("n must be at least 1")
        self._n = n

    @property
    def name(self) -> str:
        """Name of the policy."""
        return "nframes"

    @property
    def params(self) -> dict[str, int | float]:
        """Policy parameters for serialization."""
        return {"n": self._n}

    def compute_timestamps(
        self, start_s: float, end_s: float, video_duration_s: float
    ) -> tuple[float, ...]:
        """Compute N evenly-spaced timestamps within the event window.

        Args:
            start_s: Event start time in seconds
            end_s: Event end time in seconds
            video_duration_s: Total video duration for clamping

        Returns:
            Tuple of timestamps to extract
        """
        # Clamp to video bounds
        start_s = max(0.0, min(start_s, video_duration_s))
        end_s = max(0.0, min(end_s, video_duration_s))

        # Handle invalid range
        if start_s >= end_s:
            return ()

        duration = end_s - start_s

        # Short events: return single midpoint
        if duration < 0.2:
            midpoint = (start_s + end_s) / 2
            return (midpoint,)

        # N=1: midpoint
        if self._n == 1:
            return ((start_s + end_s) / 2,)

        # N=2: start and end
        if self._n == 2:
            return (start_s, end_s)

        # N>2: evenly spaced including endpoints
        step = duration / (self._n - 1)
        timestamps = [start_s + i * step for i in range(self._n)]
        return tuple(timestamps)


class FixedFPSWithinEventPolicy:
    """Extract frames at a fixed FPS rate within each event window.

    Samples frames at the specified FPS, capped at max_frames.
    """

    def __init__(self, fps: float = 1.0, max_frames: int = 30) -> None:
        """Initialize policy.

        Args:
            fps: Frames per second to extract (default: 1.0)
            max_frames: Maximum frames per event (default: 30)
        """
        if fps <= 0:
            raise ValueError("fps must be positive")
        if max_frames < 1:
            raise ValueError("max_frames must be at least 1")
        self._fps = fps
        self._max_frames = max_frames

    @property
    def name(self) -> str:
        """Name of the policy."""
        return "fps"

    @property
    def params(self) -> dict[str, int | float]:
        """Policy parameters for serialization."""
        return {"fps": self._fps, "max_frames": self._max_frames}

    def compute_timestamps(
        self, start_s: float, end_s: float, video_duration_s: float
    ) -> tuple[float, ...]:
        """Compute timestamps at fixed FPS within the event window.

        Args:
            start_s: Event start time in seconds
            end_s: Event end time in seconds
            video_duration_s: Total video duration for clamping

        Returns:
            Tuple of timestamps to extract
        """
        # Clamp to video bounds
        start_s = max(0.0, min(start_s, video_duration_s))
        end_s = max(0.0, min(end_s, video_duration_s))

        # Handle invalid range
        if start_s >= end_s:
            return ()

        duration = end_s - start_s

        # Short events: return single midpoint
        if duration < 0.2:
            midpoint = (start_s + end_s) / 2
            return (midpoint,)

        # Calculate interval between frames
        interval = 1.0 / self._fps

        # Generate timestamps
        timestamps: list[float] = []
        t = start_s
        while t <= end_s and len(timestamps) < self._max_frames:
            timestamps.append(t)
            t += interval

        return tuple(timestamps)
