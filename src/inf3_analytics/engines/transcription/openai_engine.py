"""OpenAI Whisper API transcription engine implementation."""

import os
from pathlib import Path
from typing import TYPE_CHECKING, Any

from inf3_analytics.engines.transcription.base import (
    BaseTranscriptionEngine,
    TranscriptionConfig,
)
from inf3_analytics.types.transcript import (
    Segment,
    Transcript,
    TranscriptionEngineType,
    TranscriptMetadata,
    Word,
)
from inf3_analytics.utils.time import seconds_to_timestamp

if TYPE_CHECKING:
    from openai import OpenAI


class CredentialsError(RuntimeError):
    """Raised when API credentials are missing or invalid."""

    pass


class APIError(RuntimeError):
    """Raised when API call fails."""

    pass


class OpenAITranscriptionEngine(BaseTranscriptionEngine):
    """Transcription engine using OpenAI Whisper API.

    Requires OPENAI_API_KEY environment variable to be set.
    Uses gpt-5-mini or configurable model with verbose_json format
    for word-level timestamps.
    """

    # OpenAI Whisper API file size limit
    MAX_FILE_SIZE_MB = 25

    def __init__(self, config: TranscriptionConfig | None = None) -> None:
        """Initialize the OpenAI transcription engine.

        Args:
            config: Transcription configuration
        """
        super().__init__(config)
        self._client: OpenAI | None = None

    def load(self) -> None:
        """Initialize the OpenAI client.

        Raises:
            CredentialsError: If OPENAI_API_KEY is not set
        """
        if self._loaded:
            return

        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise CredentialsError(
                "OPENAI_API_KEY environment variable is not set. "
                "Get your API key from https://platform.openai.com/api-keys"
            )

        try:
            from openai import OpenAI

            self._client = OpenAI(api_key=api_key)
            self._loaded = True
        except ImportError as e:
            raise ImportError(
                "openai package is not installed. Install with: uv add openai or pip install openai"
            ) from e

    def unload(self) -> None:
        """Unload the OpenAI client."""
        self._client = None
        self._loaded = False

    def _get_audio_duration(self, audio_path: Path) -> float:
        """Get audio duration using ffprobe.

        Args:
            audio_path: Path to audio file

        Returns:
            Duration in seconds
        """
        import subprocess

        result = subprocess.run(
            [
                "ffprobe",
                "-v",
                "quiet",
                "-show_entries",
                "format=duration",
                "-of",
                "csv=p=0",
                str(audio_path),
            ],
            capture_output=True,
            text=True,
        )
        return float(result.stdout.strip())

    def _parse_verbose_response(
        self, response: Any, audio_path: Path, source_video: Path | None
    ) -> Transcript:
        """Parse OpenAI verbose_json response to Transcript.

        Args:
            response: OpenAI transcription response
            audio_path: Path to the audio file
            source_video: Optional source video path

        Returns:
            Parsed Transcript object
        """
        segments_list: list[Segment] = []
        full_text_parts: list[str] = []

        # Process segments from response
        for idx, seg in enumerate(response.segments):
            words: tuple[Word, ...] | None = None

            # Extract word-level timestamps if available
            if hasattr(seg, "words") and seg.words:
                words = tuple(
                    Word(
                        word=w.word,
                        start_s=w.start,
                        end_s=w.end,
                        probability=getattr(w, "probability", 1.0),
                    )
                    for w in seg.words
                )

            segment = Segment(
                id=idx,
                start_s=seg.start,
                end_s=seg.end,
                start_ts=seconds_to_timestamp(seg.start),
                end_ts=seconds_to_timestamp(seg.end),
                text=seg.text.strip(),
                words=words,
                avg_logprob=getattr(seg, "avg_logprob", 0.0),
                no_speech_prob=getattr(seg, "no_speech_prob", 0.0),
            )
            segments_list.append(segment)
            full_text_parts.append(seg.text.strip())

        # Get duration from response or calculate
        duration = getattr(response, "duration", None)
        if duration is None:
            duration = self._get_audio_duration(audio_path)

        metadata = TranscriptMetadata(
            engine=TranscriptionEngineType.OPENAI,
            model_name=self.config.model_name,
            language=self.config.language,
            detected_language=getattr(response, "language", None),
            language_probability=None,  # Not provided by OpenAI API
            duration_s=duration,
            source_video=source_video,
            source_audio=audio_path,
        )

        return Transcript(
            full_text=" ".join(full_text_parts),
            segments=tuple(segments_list),
            metadata=metadata,
        )

    def transcribe(self, audio_path: Path, source_video: Path | None = None) -> Transcript:
        """Transcribe audio file using OpenAI Whisper API.

        Args:
            audio_path: Path to the audio file
            source_video: Optional path to the original video file

        Returns:
            Transcript with segments and metadata

        Raises:
            RuntimeError: If client is not loaded
            FileNotFoundError: If audio file doesn't exist
            APIError: If API call fails
        """
        if not self._loaded or self._client is None:
            raise RuntimeError("Client not loaded. Call load() first or use context manager.")

        if not audio_path.exists():
            raise FileNotFoundError(f"Audio file not found: {audio_path}")

        # Check file size
        file_size_mb = audio_path.stat().st_size / (1024 * 1024)
        if file_size_mb > self.MAX_FILE_SIZE_MB:
            raise APIError(
                f"Audio file too large: {file_size_mb:.1f}MB (max: {self.MAX_FILE_SIZE_MB}MB). "
                "Consider using the local faster-whisper engine for large files."
            )

        # Determine model name - map local model names to OpenAI equivalents
        model_name = self.config.model_name
        if model_name in ("tiny", "base", "small", "medium", "large-v3", "turbo"):
            # OpenAI uses "whisper-1" as the model name
            api_model = "whisper-1"
        else:
            api_model = model_name

        try:
            with open(audio_path, "rb") as audio_file:
                response = self._client.audio.transcriptions.create(
                    model=api_model,
                    file=audio_file,
                    response_format="verbose_json",
                    timestamp_granularities=["segment", "word"],
                    language=self.config.language,
                )
        except Exception as e:
            raise APIError(f"OpenAI API call failed: {e}") from e

        return self._parse_verbose_response(response, audio_path, source_video)
