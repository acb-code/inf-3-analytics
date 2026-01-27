"""Transcription example focused on the OpenAI engine.

This script showcases:
- Input: video file path
- Function calls: extract_audio -> transcribe -> write outputs
- Output: JSON, TXT, and SRT transcript files

Run:
  uv run python examples/transcription_openai_example.py --video inspection.MOV

Notes:
- Requires OPENAI_API_KEY when using --engine openai (default).
- You can switch engines to compare behavior.
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path

from inf3_analytics.engines.transcription import TranscriptionConfig, get_engine, list_engines
from inf3_analytics.io.transcript_writer import write_json, write_srt, write_txt
from inf3_analytics.media import extract_audio
from inf3_analytics.utils.time import format_duration


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Example: OpenAI-focused transcription pipeline usage",
    )
    parser.add_argument(
        "--video",
        type=Path,
        required=True,
        help="Input video file path",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=Path("./outputs/transcription-example"),
        help="Output directory (default: ./outputs/transcription-example)",
    )
    parser.add_argument(
        "--engine",
        type=str,
        default="openai",
        choices=list_engines(),
        help="Transcription engine (default: openai)",
    )
    parser.add_argument(
        "--model",
        type=str,
        default="whisper-1",
        help="Model name (default: whisper-1 for OpenAI)",
    )
    parser.add_argument(
        "--language",
        type=str,
        default=None,
        help="Language code (e.g., 'en'). Leave empty for auto-detect.",
    )
    return parser.parse_args()


def _validate_env(engine_name: str) -> None:
    if engine_name == "openai" and not os.environ.get("OPENAI_API_KEY"):
        raise RuntimeError("OPENAI_API_KEY is not set. Export it before running.")

    if engine_name == "gemini" and not (
        os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    ):
        raise RuntimeError("GEMINI_API_KEY or GOOGLE_API_KEY is not set.")


def main() -> int:
    args = parse_args()

    _validate_env(args.engine)

    video_path = args.video
    output_dir = args.out
    output_dir.mkdir(parents=True, exist_ok=True)

    # 1) Extract audio from video
    audio_path = output_dir / f"{video_path.stem}.wav"
    print(f"Extracting audio -> {audio_path}")
    audio_info = extract_audio(video_path, audio_path)
    print(f"Audio duration: {format_duration(audio_info.duration_s)}")

    # 2) Configure transcription
    config = TranscriptionConfig(
        model_name=args.model,
        language=args.language,
        word_timestamps=True,
        device="auto",
    )

    # 3) Run transcription (default: OpenAI engine)
    engine_class = get_engine(args.engine)
    print(f"Transcribing with engine: {args.engine} (model: {config.model_name})")
    with engine_class(config) as engine:
        transcript = engine.transcribe(audio_info.path, source_video=video_path)

    print(f"Segments: {len(transcript.segments)}")
    if transcript.metadata.detected_language:
        print(f"Detected language: {transcript.metadata.detected_language}")

    # 4) Write outputs
    json_path = output_dir / f"{video_path.stem}.json"
    txt_path = output_dir / f"{video_path.stem}.txt"
    srt_path = output_dir / f"{video_path.stem}.srt"

    write_json(transcript, json_path)
    write_txt(transcript, txt_path)
    write_srt(transcript, srt_path)

    print("Written outputs:")
    print(f"- {json_path}")
    print(f"- {txt_path}")
    print(f"- {srt_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
