"""Frame analytics engines for infrastructure inspection."""

from inf3_analytics.frame_analytics.base import (
    AnalyticsConfig,
    BaseFrameAnalyticsEngine,
    FrameAnalyticsEngine,
)

# Lazy imports for optional engines
_openai_engine: type[BaseFrameAnalyticsEngine] | None = None
_gemini_engine: type[BaseFrameAnalyticsEngine] | None = None
_baseline_engine: type[BaseFrameAnalyticsEngine] | None = None


def _get_openai_engine() -> type[BaseFrameAnalyticsEngine]:
    """Lazily import OpenAI VLM engine."""
    global _openai_engine
    if _openai_engine is None:
        from inf3_analytics.frame_analytics.vlm_openai import OpenAIVLMEngine

        _openai_engine = OpenAIVLMEngine
    return _openai_engine


def _get_gemini_engine() -> type[BaseFrameAnalyticsEngine]:
    """Lazily import Gemini VLM engine."""
    global _gemini_engine
    if _gemini_engine is None:
        from inf3_analytics.frame_analytics.vlm_gemini import GeminiVLMEngine

        _gemini_engine = GeminiVLMEngine
    return _gemini_engine


def _get_baseline_engine() -> type[BaseFrameAnalyticsEngine]:
    """Lazily import baseline quality engine."""
    global _baseline_engine
    if _baseline_engine is None:
        from inf3_analytics.frame_analytics.baseline_quality import BaselineQualityEngine

        _baseline_engine = BaselineQualityEngine
    return _baseline_engine


_ENGINE_REGISTRY: dict[str, type[BaseFrameAnalyticsEngine] | str] = {
    "openai": "lazy:openai",
    "gemini": "lazy:gemini",
    "baseline_quality": "lazy:baseline",
    "baseline": "baseline_quality",  # Alias
}


def get_engine(name: str) -> type[BaseFrameAnalyticsEngine]:
    """Get a frame analytics engine class by name.

    Args:
        name: Engine name ("openai", "gemini", "baseline_quality")

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
            engine_type = entry[5:]
            if engine_type == "openai":
                return _get_openai_engine()
            elif engine_type == "gemini":
                return _get_gemini_engine()
            elif engine_type == "baseline":
                return _get_baseline_engine()
            else:
                raise ValueError(f"Unknown lazy engine: {engine_type}")
        else:
            return get_engine(entry)

    return entry


def list_engines() -> list[str]:
    """List available frame analytics engine names.

    Returns:
        List of registered engine names (excluding internal aliases)
    """
    return [k for k in _ENGINE_REGISTRY if k != "baseline"]


__all__ = [
    "AnalyticsConfig",
    "BaseFrameAnalyticsEngine",
    "FrameAnalyticsEngine",
    "get_engine",
    "list_engines",
]
