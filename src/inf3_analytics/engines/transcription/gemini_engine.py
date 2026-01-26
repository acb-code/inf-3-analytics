"""Google Gemini API transcription engine implementation."""

import os
import re
from pathlib import Path
from typing import Any

from inf3_analytics.engines.transcription.base import (
    BaseTranscriptionEngine,
    TranscriptionConfig,
)
from inf3_analytics.types.transcript import (
    Segment,
    Transcript,
    TranscriptionEngineType,
    TranscriptMetadata,
)
from inf3_analytics.utils.time import seconds_to_timestamp


class CredentialsError(RuntimeError):
    """Raised when API credentials are missing or invalid."""

    pass


class APIError(RuntimeError):
    """Raised when API call fails."""

    pass


class GeminiTranscriptionEngine(BaseTranscriptionEngine):
    """Transcription engine using Google Gemini API.

    Requires GEMINI_API_KEY or GOOGLE_API_KEY environment variable to be set.

    Note: Gemini does NOT provide native timestamps for audio transcription.
    Timestamps are approximated based on audio duration and text length.
    """

    # Gemini inline audio size limit (approximate)
    MAX_INLINE_SIZE_MB = 20

    def __init__(self, config: TranscriptionConfig | None = None) -> None:
        """Initialize the Gemini transcription engine.

        Args:
            config: Transcription configuration
        """
        super().__init__(config)
        self._genai: Any = None
        self._model: Any = None

    def load(self) -> None:
        """Initialize the Gemini client.

        Raises:
            CredentialsError: If GEMINI_API_KEY/GOOGLE_API_KEY is not set
        """
        if self._loaded:
            return

        api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
        if not api_key:
            raise CredentialsError(
                "GEMINI_API_KEY or GOOGLE_API_KEY environment variable is not set. "
                "Get your API key from https://aistudio.google.com/app/apikey"
            )

        try:
            import google.generativeai as genai

            genai.configure(api_key=api_key)
            self._genai = genai

            # Use configurable model or default to gemini-2.0-flash
            model_name = self.config.model_name
            if model_name in ("tiny", "base", "small", "medium", "large-v3", "turbo"):
                # Map Whisper model names to Gemini model
                model_name = "gemini-2.0-flash"

            self._model = genai.GenerativeModel(model_name)
            self._loaded = True
        except ImportError as e:
            raise ImportError(
                "google-generativeai package is not installed. "
                "Install with: uv add google-generativeai or pip install google-generativeai"
            ) from e

    def unload(self) -> None:
        """Unload the Gemini client."""
        self._genai = None
        self._model = None
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

    def _split_into_sentences(self, text: str) -> list[str]:
        """Split text into sentences for segment creation.

        Args:
            text: Full transcript text

        Returns:
            List of sentences/segments
        """
        # Split on sentence boundaries while keeping the delimiter
        sentences = re.split(r"(?<=[.!?])\s+", text.strip())
        # Filter empty strings and strip whitespace
        return [s.strip() for s in sentences if s.strip()]

    def _approximate_timestamps(
        self, segments_text: list[str], duration_s: float
    ) -> list[tuple[float, float]]:
        """Approximate timestamps for segments based on text length.

        Distributes time proportionally across segments based on character count.

        Args:
            segments_text: List of segment texts
            duration_s: Total audio duration in seconds

        Returns:
            List of (start_s, end_s) tuples
        """
        if not segments_text:
            return []

        # Calculate total character count
        total_chars = sum(len(s) for s in segments_text)
        if total_chars == 0:
            # Edge case: empty segments
            return [(0.0, duration_s)]

        timestamps: list[tuple[float, float]] = []
        current_time = 0.0

        for segment_text in segments_text:
            # Proportional duration based on character count
            segment_duration = (len(segment_text) / total_chars) * duration_s
            end_time = min(current_time + segment_duration, duration_s)

            timestamps.append((current_time, end_time))
            current_time = end_time

        return timestamps

    def transcribe(self, audio_path: Path, source_video: Path | None = None) -> Transcript:
        """Transcribe audio file using Google Gemini API.

        Note: Timestamps are approximated since Gemini doesn't provide
        native audio timestamps.

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
        if not self._loaded or self._model is None or self._genai is None:
            raise RuntimeError("Client not loaded. Call load() first or use context manager.")

        if not audio_path.exists():
            raise FileNotFoundError(f"Audio file not found: {audio_path}")

        # Get audio duration first
        duration_s = self._get_audio_duration(audio_path)

        # Check file size and determine upload method
        file_size_mb = audio_path.stat().st_size / (1024 * 1024)

        try:
            if file_size_mb > self.MAX_INLINE_SIZE_MB:
                # Upload file for larger audio
                audio_file = self._genai.upload_file(audio_path)
                audio_content = audio_file
            else:
                # Inline for smaller files
                with open(audio_path, "rb") as f:
                    audio_data = f.read()

                # Determine MIME type
                suffix = audio_path.suffix.lower()
                mime_types = {
                    ".wav": "audio/wav",
                    ".mp3": "audio/mpeg",
                    ".m4a": "audio/mp4",
                    ".flac": "audio/flac",
                    ".ogg": "audio/ogg",
                }
                mime_type = mime_types.get(suffix, "audio/wav")

                audio_content = {
                    "mime_type": mime_type,
                    "data": audio_data,
                }

            # Build transcription prompt
            language_hint = ""
            if self.config.language:
                language_hint = f" The audio is in {self.config.language}."

            prompt = (
                f"Transcribe this audio file accurately.{language_hint} "
                "Return only the transcription text, without any additional commentary, "
                "formatting, or markdown. Preserve natural paragraph breaks where "
                "there are clear pauses or topic changes."
            )

            response = self._model.generate_content([prompt, audio_content])
            transcript_text = response.text.strip()

        except Exception as e:
            raise APIError(f"Gemini API call failed: {e}") from e

        # Split into segments and approximate timestamps
        segments_text = self._split_into_sentences(transcript_text)
        timestamps = self._approximate_timestamps(segments_text, duration_s)

        segments_list: list[Segment] = []
        for idx, (seg_text, (start_s, end_s)) in enumerate(
            zip(segments_text, timestamps, strict=True)
        ):
            segment = Segment(
                id=idx,
                start_s=start_s,
                end_s=end_s,
                start_ts=seconds_to_timestamp(start_s),
                end_ts=seconds_to_timestamp(end_s),
                text=seg_text,
                words=None,  # Gemini doesn't provide word-level timestamps
                avg_logprob=0.0,  # Not available from Gemini
                no_speech_prob=0.0,  # Not available from Gemini
            )
            segments_list.append(segment)

        metadata = TranscriptMetadata(
            engine=TranscriptionEngineType.GEMINI,
            model_name=self.config.model_name,
            language=self.config.language,
            detected_language=None,  # Not reliably provided by Gemini
            language_probability=None,
            duration_s=duration_s,
            source_video=source_video,
            source_audio=audio_path,
        )

        return Transcript(
            full_text=transcript_text,
            segments=tuple(segments_list),
            metadata=metadata,
        )
