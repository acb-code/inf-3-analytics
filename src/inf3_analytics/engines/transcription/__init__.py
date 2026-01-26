"""Transcription engines for audio-to-text conversion."""

from inf3_analytics.engines.transcription.base import (
    BaseTranscriptionEngine,
    TranscriptionConfig,
    TranscriptionEngine,
)
from inf3_analytics.engines.transcription.faster_whisper_engine import FasterWhisperEngine

_ENGINE_REGISTRY: dict[str, type[BaseTranscriptionEngine]] = {
    "faster-whisper": FasterWhisperEngine,
}


def get_engine(name: str) -> type[BaseTranscriptionEngine]:
    """Get a transcription engine class by name.

    Args:
        name: Engine name (e.g., "faster-whisper")

    Returns:
        The engine class

    Raises:
        ValueError: If engine name is not recognized
    """
    if name not in _ENGINE_REGISTRY:
        available = ", ".join(_ENGINE_REGISTRY.keys())
        raise ValueError(f"Unknown engine '{name}'. Available engines: {available}")
    return _ENGINE_REGISTRY[name]


def list_engines() -> list[str]:
    """List available transcription engine names.

    Returns:
        List of registered engine names
    """
    return list(_ENGINE_REGISTRY.keys())


__all__ = [
    "BaseTranscriptionEngine",
    "FasterWhisperEngine",
    "TranscriptionConfig",
    "TranscriptionEngine",
    "get_engine",
    "list_engines",
]
