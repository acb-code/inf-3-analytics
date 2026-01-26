"""Simple CLI for video-to-text transcription."""

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

from faster_whisper import WhisperModel


class FFmpegNotFoundError(RuntimeError):
    """Raised when ffmpeg is not installed or not found in PATH."""


def _check_ffmpeg() -> None:
    if shutil.which("ffmpeg") is None:
        raise FFmpegNotFoundError(
            "ffmpeg not found. Install it and ensure it is available on PATH."
        )


def extract_audio(video_path: Path, output_path: Path) -> None:
    """Extract mono 16kHz WAV audio from a video file."""
    _check_ffmpeg()

    if not video_path.exists():
        raise FileNotFoundError(f"Video file not found: {video_path}")

    output_path.parent.mkdir(parents=True, exist_ok=True)

    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        str(video_path),
        "-vn",
        "-acodec",
        "pcm_s16le",
        "-ar",
        "16000",
        "-ac",
        "1",
        str(output_path),
    ]

    try:
        subprocess.run(cmd, capture_output=True, text=True, check=True)
    except subprocess.CalledProcessError as exc:
        message = exc.stderr.strip() if exc.stderr else "ffmpeg failed"
        raise RuntimeError(message) from exc


def parse_args(args: list[str] | None = None) -> argparse.Namespace:
    """Parse CLI arguments."""
    parser = argparse.ArgumentParser(
        prog="inf3-transcribe",
        description="Transcribe a video file to plain text using faster-whisper.",
    )

    parser.add_argument("--video", type=Path, required=True, help="Input video file path")
    parser.add_argument(
        "--out",
        type=Path,
        default=Path("./outputs"),
        help="Output directory (default: ./outputs)",
    )
    parser.add_argument(
        "--model",
        type=str,
        default="base",
        help="Whisper model size or path (default: base)",
    )
    parser.add_argument(
        "--language",
        type=str,
        default=None,
        help="Language code (e.g., 'en'). Leave empty for auto-detect.",
    )

    return parser.parse_args(args)


def main(args: list[str] | None = None) -> int:
    """Run the transcription pipeline."""
    parsed = parse_args(args)

    video_path: Path = parsed.video
    if not video_path.exists():
        print(f"Error: Video file not found: {video_path}", file=sys.stderr)
        return 1

    output_dir: Path = parsed.out
    output_dir.mkdir(parents=True, exist_ok=True)

    base_name = video_path.stem
    audio_path = output_dir / f"{base_name}.wav"
    output_path = output_dir / f"{base_name}.txt"

    print(f"Extracting audio: {audio_path}")
    try:
        extract_audio(video_path, audio_path)
    except Exception as exc:
        print(f"Error extracting audio: {exc}", file=sys.stderr)
        return 1

    print(f"Transcribing with model: {parsed.model}")
    model = WhisperModel(parsed.model, device="auto")
    segments, _info = model.transcribe(str(audio_path), language=parsed.language)

    lines = [segment.text.strip() for segment in segments if segment.text.strip()]
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(f"Transcript written: {output_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
