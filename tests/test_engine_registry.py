"""Tests for engine registry functionality."""

import pytest

from inf3_analytics.engines.transcription import (
    BaseTranscriptionEngine,
    FasterWhisperEngine,
    get_engine,
    list_engines,
)


class TestListEngines:
    """Tests for list_engines function."""

    def test_returns_list(self) -> None:
        """list_engines returns a list."""
        engines = list_engines()
        assert isinstance(engines, list)

    def test_includes_faster_whisper(self) -> None:
        """list_engines includes faster-whisper."""
        engines = list_engines()
        assert "faster-whisper" in engines

    def test_includes_cloud_engines(self) -> None:
        """list_engines includes cloud engines."""
        engines = list_engines()
        assert "openai" in engines
        assert "gemini" in engines

    def test_excludes_local_alias(self) -> None:
        """list_engines excludes 'local' alias for cleaner output."""
        engines = list_engines()
        # 'local' is an internal alias, should not appear in list
        assert "local" not in engines


class TestGetEngine:
    """Tests for get_engine function."""

    def test_get_faster_whisper(self) -> None:
        """get_engine returns FasterWhisperEngine for 'faster-whisper'."""
        engine_class = get_engine("faster-whisper")
        assert engine_class is FasterWhisperEngine

    def test_get_local_alias(self) -> None:
        """get_engine returns FasterWhisperEngine for 'local' alias."""
        engine_class = get_engine("local")
        assert engine_class is FasterWhisperEngine

    def test_get_openai_engine(self) -> None:
        """get_engine returns OpenAITranscriptionEngine for 'openai'."""
        engine_class = get_engine("openai")
        assert issubclass(engine_class, BaseTranscriptionEngine)
        assert engine_class.__name__ == "OpenAITranscriptionEngine"

    def test_get_gemini_engine(self) -> None:
        """get_engine returns GeminiTranscriptionEngine for 'gemini'."""
        engine_class = get_engine("gemini")
        assert issubclass(engine_class, BaseTranscriptionEngine)
        assert engine_class.__name__ == "GeminiTranscriptionEngine"

    def test_unknown_engine_raises_error(self) -> None:
        """get_engine raises ValueError for unknown engine name."""
        with pytest.raises(ValueError, match="Unknown engine"):
            get_engine("nonexistent")

    def test_unknown_engine_lists_available(self) -> None:
        """get_engine error message includes available engines."""
        with pytest.raises(ValueError) as exc_info:
            get_engine("nonexistent")

        error_message = str(exc_info.value)
        assert "faster-whisper" in error_message
        assert "openai" in error_message
        assert "gemini" in error_message


class TestEngineClasses:
    """Tests for engine class structure."""

    def test_faster_whisper_is_base_engine(self) -> None:
        """FasterWhisperEngine inherits from BaseTranscriptionEngine."""
        assert issubclass(FasterWhisperEngine, BaseTranscriptionEngine)

    def test_all_engines_have_required_methods(self) -> None:
        """All registered engines have required interface methods."""
        engine_names = list_engines()
        for name in engine_names:
            engine_class = get_engine(name)
            assert hasattr(engine_class, "load")
            assert hasattr(engine_class, "unload")
            assert hasattr(engine_class, "transcribe")
            assert hasattr(engine_class, "is_loaded")
