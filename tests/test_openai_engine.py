"""Tests for OpenAI transcription engine."""

from pathlib import Path
from unittest.mock import MagicMock, mock_open, patch

import pytest

from inf3_analytics.engines.transcription.openai_engine import (
    APIError,
    CredentialsError,
    OpenAITranscriptionEngine,
)
from inf3_analytics.engines.transcription.base import TranscriptionConfig
from inf3_analytics.types.transcript import TranscriptionEngineType


class MockWord:
    """Mock OpenAI word object."""

    def __init__(self, word: str, start: float, end: float, probability: float = 1.0) -> None:
        self.word = word
        self.start = start
        self.end = end
        self.probability = probability


class MockSegment:
    """Mock OpenAI segment object."""

    def __init__(
        self,
        text: str,
        start: float,
        end: float,
        words: list[MockWord] | None = None,
    ) -> None:
        self.text = text
        self.start = start
        self.end = end
        self.words = words
        self.avg_logprob = -0.25
        self.no_speech_prob = 0.01


class MockTranscriptionResponse:
    """Mock OpenAI transcription response."""

    def __init__(
        self,
        text: str,
        segments: list[MockSegment],
        language: str = "en",
        duration: float = 10.0,
    ) -> None:
        self.text = text
        self.segments = segments
        self.language = language
        self.duration = duration


class TestOpenAIEngineLoad:
    """Tests for OpenAI engine load method."""

    def test_load_without_api_key_raises_error(self) -> None:
        """load() raises CredentialsError when OPENAI_API_KEY is not set."""
        engine = OpenAITranscriptionEngine()
        with patch.dict("os.environ", {}, clear=True):
            with pytest.raises(CredentialsError, match="OPENAI_API_KEY"):
                engine.load()

    def test_load_with_api_key_succeeds(self) -> None:
        """load() succeeds when OPENAI_API_KEY is set."""
        engine = OpenAITranscriptionEngine()
        mock_openai = MagicMock()
        with patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"}):
            with patch.dict("sys.modules", {"openai": mock_openai}):
                engine.load()
                assert engine.is_loaded

    def test_load_is_idempotent(self) -> None:
        """load() can be called multiple times safely."""
        engine = OpenAITranscriptionEngine()
        mock_openai = MagicMock()
        with patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"}):
            with patch.dict("sys.modules", {"openai": mock_openai}):
                engine.load()
                engine.load()
                # OpenAI client should only be created once
                assert mock_openai.OpenAI.call_count == 1


class TestOpenAIEngineUnload:
    """Tests for OpenAI engine unload method."""

    def test_unload_clears_state(self) -> None:
        """unload() clears the loaded state."""
        engine = OpenAITranscriptionEngine()
        mock_openai = MagicMock()
        with patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"}):
            with patch.dict("sys.modules", {"openai": mock_openai}):
                engine.load()
                assert engine.is_loaded

                engine.unload()
                assert not engine.is_loaded


class TestOpenAIEngineTranscribe:
    """Tests for OpenAI engine transcribe method."""

    @pytest.fixture
    def mock_response(self) -> MockTranscriptionResponse:
        """Create a mock transcription response."""
        segments = [
            MockSegment(
                text=" Hello world.",
                start=0.0,
                end=2.0,
                words=[
                    MockWord("Hello", 0.0, 1.0, 0.98),
                    MockWord("world.", 1.0, 2.0, 0.95),
                ],
            ),
            MockSegment(
                text=" This is a test.",
                start=2.0,
                end=4.5,
                words=[
                    MockWord("This", 2.0, 2.5, 0.97),
                    MockWord("is", 2.5, 2.8, 0.99),
                    MockWord("a", 2.8, 3.0, 0.98),
                    MockWord("test.", 3.0, 4.5, 0.96),
                ],
            ),
        ]
        return MockTranscriptionResponse(
            text="Hello world. This is a test.",
            segments=segments,
            language="en",
            duration=4.5,
        )

    def test_transcribe_without_load_raises_error(self, tmp_path: Path) -> None:
        """transcribe() raises RuntimeError if not loaded."""
        engine = OpenAITranscriptionEngine()
        audio_path = tmp_path / "test.wav"
        audio_path.touch()

        with pytest.raises(RuntimeError, match="not loaded"):
            engine.transcribe(audio_path)

    def test_transcribe_file_not_found(self, tmp_path: Path) -> None:
        """transcribe() raises FileNotFoundError for missing audio file."""
        engine = OpenAITranscriptionEngine()
        mock_openai = MagicMock()
        with patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"}):
            with patch.dict("sys.modules", {"openai": mock_openai}):
                engine.load()

                with pytest.raises(FileNotFoundError):
                    engine.transcribe(tmp_path / "nonexistent.wav")

    def test_transcribe_file_too_large(self, tmp_path: Path) -> None:
        """transcribe() raises APIError for files exceeding size limit."""
        engine = OpenAITranscriptionEngine()
        audio_path = tmp_path / "large.wav"
        # Create a file larger than 25MB limit
        audio_path.write_bytes(b"x" * (26 * 1024 * 1024))

        mock_openai = MagicMock()
        with patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"}):
            with patch.dict("sys.modules", {"openai": mock_openai}):
                engine.load()

                with pytest.raises(APIError, match="too large"):
                    engine.transcribe(audio_path)

    def test_transcribe_returns_transcript(
        self, tmp_path: Path, mock_response: MockTranscriptionResponse
    ) -> None:
        """transcribe() returns a valid Transcript object."""
        engine = OpenAITranscriptionEngine()
        audio_path = tmp_path / "test.wav"
        audio_path.write_bytes(b"fake audio data")

        mock_client = MagicMock()
        mock_client.audio.transcriptions.create.return_value = mock_response

        mock_openai = MagicMock()
        mock_openai.OpenAI.return_value = mock_client

        with patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"}):
            with patch.dict("sys.modules", {"openai": mock_openai}):
                engine.load()
                transcript = engine.transcribe(audio_path)

        assert transcript.full_text == "Hello world. This is a test."
        assert len(transcript.segments) == 2
        assert transcript.metadata.engine == TranscriptionEngineType.OPENAI

    def test_transcribe_preserves_timestamps(
        self, tmp_path: Path, mock_response: MockTranscriptionResponse
    ) -> None:
        """transcribe() preserves segment timestamps from API response."""
        engine = OpenAITranscriptionEngine()
        audio_path = tmp_path / "test.wav"
        audio_path.write_bytes(b"fake audio data")

        mock_client = MagicMock()
        mock_client.audio.transcriptions.create.return_value = mock_response

        mock_openai = MagicMock()
        mock_openai.OpenAI.return_value = mock_client

        with patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"}):
            with patch.dict("sys.modules", {"openai": mock_openai}):
                engine.load()
                transcript = engine.transcribe(audio_path)

        # Check first segment timestamps
        seg1 = transcript.segments[0]
        assert seg1.start_s == 0.0
        assert seg1.end_s == 2.0

        # Check second segment timestamps
        seg2 = transcript.segments[1]
        assert seg2.start_s == 2.0
        assert seg2.end_s == 4.5

    def test_transcribe_preserves_word_timestamps(
        self, tmp_path: Path, mock_response: MockTranscriptionResponse
    ) -> None:
        """transcribe() preserves word-level timestamps from API response."""
        engine = OpenAITranscriptionEngine()
        audio_path = tmp_path / "test.wav"
        audio_path.write_bytes(b"fake audio data")

        mock_client = MagicMock()
        mock_client.audio.transcriptions.create.return_value = mock_response

        mock_openai = MagicMock()
        mock_openai.OpenAI.return_value = mock_client

        with patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"}):
            with patch.dict("sys.modules", {"openai": mock_openai}):
                engine.load()
                transcript = engine.transcribe(audio_path)

        # Check word timestamps in first segment
        seg1 = transcript.segments[0]
        assert seg1.words is not None
        assert len(seg1.words) == 2
        assert seg1.words[0].word == "Hello"
        assert seg1.words[0].start_s == 0.0
        assert seg1.words[0].end_s == 1.0

    def test_transcribe_with_source_video(
        self, tmp_path: Path, mock_response: MockTranscriptionResponse
    ) -> None:
        """transcribe() includes source_video in metadata."""
        engine = OpenAITranscriptionEngine()
        audio_path = tmp_path / "test.wav"
        audio_path.write_bytes(b"fake audio data")
        video_path = tmp_path / "test.mp4"

        mock_client = MagicMock()
        mock_client.audio.transcriptions.create.return_value = mock_response

        mock_openai = MagicMock()
        mock_openai.OpenAI.return_value = mock_client

        with patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"}):
            with patch.dict("sys.modules", {"openai": mock_openai}):
                engine.load()
                transcript = engine.transcribe(audio_path, source_video=video_path)

        assert transcript.metadata.source_video == video_path
        assert transcript.metadata.source_audio == audio_path


class TestOpenAIEngineContextManager:
    """Tests for OpenAI engine context manager support."""

    def test_context_manager_loads_and_unloads(self) -> None:
        """Context manager properly loads and unloads the engine."""
        mock_openai = MagicMock()
        with patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"}):
            with patch.dict("sys.modules", {"openai": mock_openai}):
                with OpenAITranscriptionEngine() as engine:
                    assert engine.is_loaded

                assert not engine.is_loaded
