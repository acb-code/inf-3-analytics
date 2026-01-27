"""Tests for Gemini transcription engine."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from inf3_analytics.engines.transcription.gemini_engine import (
    APIError,
    CredentialsError,
    GeminiTranscriptionEngine,
)
from inf3_analytics.engines.transcription.base import TranscriptionConfig
from inf3_analytics.types.transcript import TranscriptionEngineType


class MockGeminiResponse:
    """Mock Gemini API response."""

    def __init__(self, text: str) -> None:
        self.text = text


class TestGeminiEngineLoad:
    """Tests for Gemini engine load method."""

    def test_load_without_api_key_raises_error(self) -> None:
        """load() raises CredentialsError when API key is not set."""
        engine = GeminiTranscriptionEngine()
        with patch.dict("os.environ", {}, clear=True):
            with pytest.raises(CredentialsError, match="GEMINI_API_KEY"):
                engine.load()

    def test_load_with_gemini_api_key_succeeds(self) -> None:
        """load() succeeds when GEMINI_API_KEY is set."""
        engine = GeminiTranscriptionEngine()
        mock_genai = MagicMock()
        mock_genai.Client.return_value = MagicMock()
        mock_types = MagicMock()
        mock_google = MagicMock()
        mock_google.genai = mock_genai

        with patch.dict("os.environ", {"GEMINI_API_KEY": "test-key"}):
            with patch.dict(
                "sys.modules",
                {
                    "google": mock_google,
                    "google.genai": mock_genai,
                    "google.genai.types": mock_types,
                },
            ):
                engine.load()
                assert engine.is_loaded

    def test_load_with_google_api_key_succeeds(self) -> None:
        """load() succeeds when GOOGLE_API_KEY is set (fallback)."""
        engine = GeminiTranscriptionEngine()
        mock_genai = MagicMock()
        mock_genai.Client.return_value = MagicMock()
        mock_types = MagicMock()
        mock_google = MagicMock()
        mock_google.genai = mock_genai

        with patch.dict("os.environ", {"GOOGLE_API_KEY": "test-key"}, clear=True):
            with patch.dict(
                "sys.modules",
                {
                    "google": mock_google,
                    "google.genai": mock_genai,
                    "google.genai.types": mock_types,
                },
            ):
                engine.load()
                assert engine.is_loaded

    def test_load_is_idempotent(self) -> None:
        """load() can be called multiple times safely."""
        engine = GeminiTranscriptionEngine()
        mock_genai = MagicMock()
        mock_genai.Client.return_value = MagicMock()
        mock_types = MagicMock()
        mock_google = MagicMock()
        mock_google.genai = mock_genai

        with patch.dict("os.environ", {"GEMINI_API_KEY": "test-key"}):
            with patch.dict(
                "sys.modules",
                {
                    "google": mock_google,
                    "google.genai": mock_genai,
                    "google.genai.types": mock_types,
                },
            ):
                engine.load()
                engine.load()
                # Client should only be created once
                assert mock_genai.Client.call_count == 1


class TestGeminiEngineUnload:
    """Tests for Gemini engine unload method."""

    def test_unload_clears_state(self) -> None:
        """unload() clears the loaded state."""
        engine = GeminiTranscriptionEngine()
        mock_genai = MagicMock()
        mock_genai.Client.return_value = MagicMock()
        mock_types = MagicMock()
        mock_google = MagicMock()
        mock_google.genai = mock_genai

        with patch.dict("os.environ", {"GEMINI_API_KEY": "test-key"}):
            with patch.dict(
                "sys.modules",
                {
                    "google": mock_google,
                    "google.genai": mock_genai,
                    "google.genai.types": mock_types,
                },
            ):
                engine.load()
                assert engine.is_loaded

                engine.unload()
                assert not engine.is_loaded


class TestGeminiTimestampApproximation:
    """Tests for Gemini timestamp approximation logic."""

    def test_split_into_sentences(self) -> None:
        """_split_into_sentences correctly splits text."""
        engine = GeminiTranscriptionEngine()

        text = "Hello world. This is a test! How are you?"
        sentences = engine._split_into_sentences(text)

        assert sentences == ["Hello world.", "This is a test!", "How are you?"]

    def test_split_into_sentences_handles_empty(self) -> None:
        """_split_into_sentences handles empty text."""
        engine = GeminiTranscriptionEngine()

        sentences = engine._split_into_sentences("")
        assert sentences == []

    def test_approximate_timestamps_proportional(self) -> None:
        """_approximate_timestamps distributes time proportionally."""
        engine = GeminiTranscriptionEngine()

        # Two segments of equal length
        segments = ["Hello world.", "Goodbye now."]
        duration = 10.0

        timestamps = engine._approximate_timestamps(segments, duration)

        assert len(timestamps) == 2
        # Equal length segments should get equal time
        assert timestamps[0] == (0.0, 5.0)
        assert timestamps[1] == (5.0, 10.0)

    def test_approximate_timestamps_unequal(self) -> None:
        """_approximate_timestamps handles unequal segment lengths."""
        engine = GeminiTranscriptionEngine()

        # First segment is 10 chars, second is 20 chars
        segments = ["1234567890", "12345678901234567890"]
        duration = 30.0

        timestamps = engine._approximate_timestamps(segments, duration)

        assert len(timestamps) == 2
        # First segment: 10/(10+20) = 1/3 of 30s = 10s
        assert timestamps[0][0] == 0.0
        assert timestamps[0][1] == 10.0
        # Second segment: 20/(10+20) = 2/3 of 30s = 20s (10 to 30)
        assert timestamps[1][0] == 10.0
        assert timestamps[1][1] == 30.0

    def test_approximate_timestamps_empty(self) -> None:
        """_approximate_timestamps handles empty segments."""
        engine = GeminiTranscriptionEngine()

        timestamps = engine._approximate_timestamps([], 10.0)
        assert timestamps == []


class TestGeminiEngineTranscribe:
    """Tests for Gemini engine transcribe method."""

    def test_transcribe_without_load_raises_error(self, tmp_path: Path) -> None:
        """transcribe() raises RuntimeError if not loaded."""
        engine = GeminiTranscriptionEngine()
        audio_path = tmp_path / "test.wav"
        audio_path.touch()

        with pytest.raises(RuntimeError, match="not loaded"):
            engine.transcribe(audio_path)

    def test_transcribe_file_not_found(self, tmp_path: Path) -> None:
        """transcribe() raises FileNotFoundError for missing audio file."""
        engine = GeminiTranscriptionEngine()
        engine._loaded = True
        engine._client = MagicMock()
        engine._types = MagicMock()

        with pytest.raises(FileNotFoundError):
            engine.transcribe(tmp_path / "nonexistent.wav")

    def test_transcribe_returns_transcript(self, tmp_path: Path) -> None:
        """transcribe() returns a valid Transcript object."""
        engine = GeminiTranscriptionEngine()
        audio_path = tmp_path / "test.wav"
        audio_path.write_bytes(b"fake audio data")

        mock_response = MockGeminiResponse("Hello world. This is a test.")
        mock_client = MagicMock()
        mock_client.models.generate_content.return_value = mock_response

        mock_types = MagicMock()
        mock_types.Part.from_bytes.return_value = MagicMock()

        engine._loaded = True
        engine._client = mock_client
        engine._types = mock_types
        engine._model_name = "gemini-3-flash-preview"

        with patch.object(engine, "_get_audio_duration", return_value=10.0):
            transcript = engine.transcribe(audio_path)

        assert "Hello world" in transcript.full_text
        assert "This is a test" in transcript.full_text
        assert len(transcript.segments) == 2
        assert transcript.metadata.engine == TranscriptionEngineType.GEMINI

    def test_transcribe_approximates_timestamps(self, tmp_path: Path) -> None:
        """transcribe() creates approximate timestamps for segments."""
        engine = GeminiTranscriptionEngine()
        audio_path = tmp_path / "test.wav"
        audio_path.write_bytes(b"fake audio data")

        mock_response = MockGeminiResponse("Hello world. Goodbye now.")
        mock_client = MagicMock()
        mock_client.models.generate_content.return_value = mock_response

        mock_types = MagicMock()
        mock_types.Part.from_bytes.return_value = MagicMock()

        engine._loaded = True
        engine._client = mock_client
        engine._types = mock_types
        engine._model_name = "gemini-3-flash-preview"

        with patch.object(engine, "_get_audio_duration", return_value=10.0):
            transcript = engine.transcribe(audio_path)

        # Segments should have timestamps
        assert transcript.segments[0].start_s == 0.0
        assert transcript.segments[0].end_s > 0.0
        assert transcript.segments[1].end_s == 10.0

    def test_transcribe_no_word_timestamps(self, tmp_path: Path) -> None:
        """transcribe() does not include word-level timestamps (not supported)."""
        engine = GeminiTranscriptionEngine()
        audio_path = tmp_path / "test.wav"
        audio_path.write_bytes(b"fake audio data")

        mock_response = MockGeminiResponse("Hello world.")
        mock_client = MagicMock()
        mock_client.models.generate_content.return_value = mock_response

        mock_types = MagicMock()
        mock_types.Part.from_bytes.return_value = MagicMock()

        engine._loaded = True
        engine._client = mock_client
        engine._types = mock_types
        engine._model_name = "gemini-3-flash-preview"

        with patch.object(engine, "_get_audio_duration", return_value=5.0):
            transcript = engine.transcribe(audio_path)

        # Words should be None since Gemini doesn't provide word timestamps
        assert transcript.segments[0].words is None

    def test_transcribe_with_source_video(self, tmp_path: Path) -> None:
        """transcribe() includes source_video in metadata."""
        engine = GeminiTranscriptionEngine()
        audio_path = tmp_path / "test.wav"
        audio_path.write_bytes(b"fake audio data")
        video_path = tmp_path / "test.mp4"

        mock_response = MockGeminiResponse("Test transcription.")
        mock_model = MagicMock()
        mock_model.generate_content.return_value = mock_response

        mock_types = MagicMock()
        mock_types.Part.from_bytes.return_value = MagicMock()

        engine._loaded = True
        engine._client = mock_model
        engine._types = mock_types
        engine._model_name = "gemini-3-flash-preview"

        with patch.object(engine, "_get_audio_duration", return_value=5.0):
            transcript = engine.transcribe(audio_path, source_video=video_path)

        assert transcript.metadata.source_video == video_path
        assert transcript.metadata.source_audio == audio_path

    def test_transcribe_api_failure_raises_error(self, tmp_path: Path) -> None:
        """transcribe() raises APIError on API failure."""
        engine = GeminiTranscriptionEngine()
        audio_path = tmp_path / "test.wav"
        audio_path.write_bytes(b"fake audio data")

        mock_client = MagicMock()
        mock_client.models.generate_content.side_effect = Exception("API Error")

        mock_types = MagicMock()
        mock_types.Part.from_bytes.return_value = MagicMock()

        engine._loaded = True
        engine._client = mock_client
        engine._types = mock_types
        engine._model_name = "gemini-3-flash-preview"

        with patch.object(engine, "_get_audio_duration", return_value=5.0):
            with pytest.raises(APIError, match="Gemini API call failed"):
                engine.transcribe(audio_path)


class TestGeminiEngineContextManager:
    """Tests for Gemini engine context manager support."""

    def test_context_manager_loads_and_unloads(self) -> None:
        """Context manager properly loads and unloads the engine."""
        mock_genai = MagicMock()
        mock_genai.Client.return_value = MagicMock()
        mock_types = MagicMock()
        mock_google = MagicMock()
        mock_google.genai = mock_genai

        with patch.dict("os.environ", {"GEMINI_API_KEY": "test-key"}):
            with patch.dict(
                "sys.modules",
                {
                    "google": mock_google,
                    "google.genai": mock_genai,
                    "google.genai.types": mock_types,
                },
            ):
                with GeminiTranscriptionEngine() as engine:
                    assert engine.is_loaded

                assert not engine.is_loaded
