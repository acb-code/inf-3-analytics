"""Transcription engines for audio-to-text conversion."""

from inf3_analytics.engines.transcription.base import (
    BaseTranscriptionEngine,
    TranscriptionConfig,
    TranscriptionEngine,
)
from inf3_analytics.engines.transcription.faster_whisper_engine import FasterWhisperEngine

# Lazy imports for optional cloud engines
_openai_engine: type[BaseTranscriptionEngine] | None = None
_gemini_engine: type[BaseTranscriptionEngine] | None = None


def _get_openai_engine() -> type[BaseTranscriptionEngine]:
    """Lazily import OpenAI engine."""
    global _openai_engine
    if _openai_engine is None:
        from inf3_analytics.engines.transcription.openai_engine import OpenAITranscriptionEngine

        _openai_engine = OpenAITranscriptionEngine
    return _openai_engine


def _get_gemini_engine() -> type[BaseTranscriptionEngine]:
    """Lazily import Gemini engine."""
    global _gemini_engine
    if _gemini_engine is None:
        from inf3_analytics.engines.transcription.gemini_engine import GeminiTranscriptionEngine

        _gemini_engine = GeminiTranscriptionEngine
    return _gemini_engine


_ENGINE_REGISTRY: dict[str, type[BaseTranscriptionEngine] | str] = {
    "faster-whisper": FasterWhisperEngine,
    "local": "faster-whisper",  # Alias for user convenience
    "openai": "lazy:openai",  # Lazy-loaded
    "gemini": "lazy:gemini",  # Lazy-loaded
}


def get_engine(name: str) -> type[BaseTranscriptionEngine]:
    """Get a transcription engine class by name.

    Args:
        name: Engine name (e.g., "faster-whisper", "openai", "gemini")
            "local" is an alias for "faster-whisper"

    Returns:
        The engine class

    Raises:
        ValueError: If engine name is not recognized
    """
    if name not in _ENGINE_REGISTRY:
        available = ", ".join(k for k in _ENGINE_REGISTRY if not k.startswith("lazy:"))
        raise ValueError(f"Unknown engine '{name}'. Available engines: {available}")

    entry = _ENGINE_REGISTRY[name]

    # Handle aliases
    if isinstance(entry, str):
        if entry.startswith("lazy:"):
            # Lazy load cloud engines
            engine_type = entry[5:]  # Remove "lazy:" prefix
            if engine_type == "openai":
                return _get_openai_engine()
            elif engine_type == "gemini":
                return _get_gemini_engine()
            else:
                raise ValueError(f"Unknown lazy engine: {engine_type}")
        else:
            # Regular alias - recurse
            return get_engine(entry)

    return entry


def list_engines() -> list[str]:
    """List available transcription engine names.

    Returns:
        List of registered engine names (excluding internal aliases)
    """
    # Return user-facing engine names, excluding the "local" alias to avoid confusion
    return [k for k in _ENGINE_REGISTRY if k != "local"]


__all__ = [
    "BaseTranscriptionEngine",
    "FasterWhisperEngine",
    "TranscriptionConfig",
    "TranscriptionEngine",
    "get_engine",
    "list_engines",
]
