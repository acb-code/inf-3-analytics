"""Faster-Whisper transcription engine implementation."""

from pathlib import Path
from typing import TYPE_CHECKING

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
    from faster_whisper import WhisperModel


class FasterWhisperEngine(BaseTranscriptionEngine):
    """Transcription engine using faster-whisper library."""

    def __init__(self, config: TranscriptionConfig | None = None) -> None:
        """Initialize the Faster-Whisper engine.

        Args:
            config: Transcription configuration
        """
        super().__init__(config)
        self._model: WhisperModel | None = None

    def load(self) -> None:
        """Load the Whisper model into memory."""
        if self._loaded:
            return

        from faster_whisper import WhisperModel

        device = self.config.device
        if device == "auto":
            device = "cuda"  # Will fall back to CPU if CUDA unavailable

        compute_type = self.config.compute_type
        if compute_type == "default":
            compute_type = "float16" if device == "cuda" else "int8"

        self._model = WhisperModel(
            self.config.model_name,
            device=device,
            compute_type=compute_type,
        )
        self._loaded = True

    def unload(self) -> None:
        """Unload the model from memory."""
        self._model = None
        self._loaded = False

    def transcribe(self, audio_path: Path, source_video: Path | None = None) -> Transcript:
        """Transcribe audio file using faster-whisper.

        Args:
            audio_path: Path to the audio file
            source_video: Optional path to the original video file

        Returns:
            Transcript with segments and metadata

        Raises:
            RuntimeError: If model is not loaded
            FileNotFoundError: If audio file doesn't exist
        """
        if not self._loaded or self._model is None:
            raise RuntimeError("Model not loaded. Call load() first or use context manager.")

        if not audio_path.exists():
            raise FileNotFoundError(f"Audio file not found: {audio_path}")

        # Prepare transcription options
        temp_config = self.config.temperature
        if isinstance(temp_config, (int, float)):
            temp_list: list[float] = [float(temp_config)]
        else:
            temp_list = list(temp_config)

        segments_iter, info = self._model.transcribe(
            str(audio_path),
            language=self.config.language,
            beam_size=self.config.beam_size,
            word_timestamps=self.config.word_timestamps,
            vad_filter=self.config.vad_filter,
            initial_prompt=self.config.initial_prompt,
            temperature=temp_list,
        )

        # Convert segments to our format
        segments_list: list[Segment] = []
        full_text_parts: list[str] = []

        for idx, seg in enumerate(segments_iter):
            words: tuple[Word, ...] | None = None
            if seg.words:
                words = tuple(
                    Word(
                        word=w.word,
                        start_s=w.start,
                        end_s=w.end,
                        probability=w.probability,
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
                avg_logprob=seg.avg_logprob,
                no_speech_prob=seg.no_speech_prob,
            )
            segments_list.append(segment)
            full_text_parts.append(seg.text.strip())

        metadata = TranscriptMetadata(
            engine=TranscriptionEngineType.FASTER_WHISPER,
            model_name=self.config.model_name,
            language=self.config.language,
            detected_language=info.language,
            language_probability=info.language_probability,
            duration_s=info.duration,
            source_video=source_video,
            source_audio=audio_path,
        )

        return Transcript(
            full_text=" ".join(full_text_parts),
            segments=tuple(segments_list),
            metadata=metadata,
        )
