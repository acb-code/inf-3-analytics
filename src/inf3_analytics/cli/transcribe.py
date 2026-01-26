"""Simple CLI for video-to-text transcription."""

import argparse
import os
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


def _load_env_file(path: Path) -> None:
    if not path.exists():
        return

    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


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
        "--engine",
        type=str,
        default="local",
        choices=["local", "openai", "gemini"],
        help="Transcription engine: local (faster-whisper), openai, or gemini.",
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
    _load_env_file(Path(".env"))

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

    try:
        if parsed.engine == "local":
            print(f"Transcribing with model: {parsed.model}")
            model = WhisperModel(parsed.model, device="auto")
            segments, _info = model.transcribe(str(audio_path), language=parsed.language)
            lines = [segment.text.strip() for segment in segments if segment.text.strip()]
            text = "\n".join(lines).strip()
        elif parsed.engine == "openai":
            api_key = os.environ.get("OPENAI_API_KEY")
            if not api_key:
                print("Error: OPENAI_API_KEY is not set.", file=sys.stderr)
                return 1
            from openai import OpenAI

            client = OpenAI(api_key=api_key)
            openai_model = os.environ.get("OPENAI_MODEL", "whisper-1")
            with open(audio_path, "rb") as audio_file:
                response = client.audio.transcriptions.create(
                    model=openai_model,
                    file=audio_file,
                )
            text = response.text.strip()
        else:
            api_key = os.environ.get("GEMINI_API_KEY")
            if not api_key:
                print("Error: GEMINI_API_KEY is not set.", file=sys.stderr)
                return 1
            import google.generativeai as genai

            genai.configure(api_key=api_key)
            gemini_model = os.environ.get("GEMINI_MODEL", "gemini-1.5-flash")
            model = genai.GenerativeModel(gemini_model)
            audio_file = genai.upload_file(audio_path)
            response = model.generate_content(
                [
                    "Transcribe the audio. Return only the transcript text.",
                    audio_file,
                ]
            )
            text = response.text.strip()
    except Exception as exc:
        print(f"Error during transcription: {exc}", file=sys.stderr)
        return 1

    output_path.write_text(f"{text}\n", encoding="utf-8")

    print(f"Transcript written: {output_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
