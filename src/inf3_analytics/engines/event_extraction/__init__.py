"""Event extraction engines for transcript analysis."""

from inf3_analytics.engines.event_extraction.base import (
    BaseEventExtractionEngine,
    EventExtractionConfig,
    EventExtractionEngine,
)
from inf3_analytics.engines.event_extraction.rules import RuleBasedEventEngine

# Lazy imports for optional cloud engines
_openai_engine: type[BaseEventExtractionEngine] | None = None
_gemini_engine: type[BaseEventExtractionEngine] | None = None


def _get_openai_engine() -> type[BaseEventExtractionEngine]:
    """Lazily import OpenAI event engine."""
    global _openai_engine
    if _openai_engine is None:
        from inf3_analytics.engines.event_extraction.llm import OpenAIEventEngine

        _openai_engine = OpenAIEventEngine
    return _openai_engine


def _get_gemini_engine() -> type[BaseEventExtractionEngine]:
    """Lazily import Gemini event engine."""
    global _gemini_engine
    if _gemini_engine is None:
        from inf3_analytics.engines.event_extraction.llm import GeminiEventEngine

        _gemini_engine = GeminiEventEngine
    return _gemini_engine


_ENGINE_REGISTRY: dict[str, type[BaseEventExtractionEngine] | str] = {
    "rules": RuleBasedEventEngine,
    "rule-based": "rules",  # Alias for user convenience
    "openai": "lazy:openai",  # Lazy-loaded
    "gemini": "lazy:gemini",  # Lazy-loaded
}


def get_engine(name: str) -> type[BaseEventExtractionEngine]:
    """Get an event extraction engine class by name.

    Args:
        name: Engine name (e.g., "rules", "openai", "gemini")
            "rule-based" is an alias for "rules"

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
            # Lazy load optional engines
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
    """List available event extraction engine names.

    Returns:
        List of registered engine names (excluding internal aliases)
    """
    # Return user-facing engine names, excluding aliases
    return [k for k in _ENGINE_REGISTRY if k != "rule-based"]


__all__ = [
    "BaseEventExtractionEngine",
    "EventExtractionConfig",
    "EventExtractionEngine",
    "RuleBasedEventEngine",
    "get_engine",
    "list_engines",
]
