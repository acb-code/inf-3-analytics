"""CLI for video transcription."""

import argparse
import sys
from pathlib import Path

from inf3_analytics.engines.transcription import get_engine, list_engines
from inf3_analytics.engines.transcription.base import TranscriptionConfig
from inf3_analytics.io.transcript_writer import write_json, write_srt, write_txt
from inf3_analytics.media.audio_extract import extract_audio
from inf3_analytics.utils.time import format_duration


def parse_args(args: list[str] | None = None) -> argparse.Namespace:
    """Parse command line arguments.

    Args:
        args: Command line arguments (uses sys.argv if None)

    Returns:
        Parsed arguments namespace
    """
    parser = argparse.ArgumentParser(
        prog="inf3-transcribe",
        description="Transcribe video files with synchronized timestamps",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --video inspection.mp4
  %(prog)s --video inspection.mp4 --out outputs/run1
  %(prog)s --video inspection.mp4 --model large-v3 --device cuda
  %(prog)s --video inspection.mp4 --language en --format json,srt
        """,
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
        default=Path("./outputs"),
        help="Output directory (default: ./outputs)",
    )

    parser.add_argument(
        "--language",
        type=str,
        default=None,
        help="Language code (e.g., 'en', 'es') or auto-detect if not specified",
    )

    parser.add_argument(
        "--model",
        type=str,
        default="base",
        choices=["tiny", "base", "small", "medium", "large-v3", "turbo"],
        help="Whisper model size (default: base)",
    )

    parser.add_argument(
        "--engine",
        type=str,
        default="faster-whisper",
        choices=list_engines(),
        help="Transcription engine (default: faster-whisper)",
    )

    parser.add_argument(
        "--device",
        type=str,
        default="auto",
        choices=["auto", "cpu", "cuda"],
        help="Compute device (default: auto)",
    )

    parser.add_argument(
        "--compute-type",
        type=str,
        default="default",
        choices=["default", "int8", "float16", "float32"],
        help="Model precision (default: auto-select based on device)",
    )

    parser.add_argument(
        "--no-words",
        action="store_true",
        help="Disable word-level timestamps",
    )

    parser.add_argument(
        "--format",
        type=str,
        default="json,txt,srt",
        help="Output formats, comma-separated (default: json,txt,srt)",
    )

    parser.add_argument(
        "--no-vad",
        action="store_true",
        help="Disable voice activity detection filter",
    )

    return parser.parse_args(args)


def main(args: list[str] | None = None) -> int:
    """Main entry point for transcription CLI.

    Args:
        args: Command line arguments (uses sys.argv if None)

    Returns:
        Exit code (0 for success, non-zero for errors)
    """
    parsed = parse_args(args)

    # Validate input
    video_path: Path = parsed.video
    if not video_path.exists():
        print(f"Error: Video file not found: {video_path}", file=sys.stderr)
        return 1

    # Set up output directory
    output_dir: Path = parsed.out
    output_dir.mkdir(parents=True, exist_ok=True)

    # Determine base name for output files
    base_name = video_path.stem

    # Parse output formats
    formats = [f.strip().lower() for f in parsed.format.split(",")]
    valid_formats = {"json", "txt", "srt"}
    for fmt in formats:
        if fmt not in valid_formats:
            print(f"Error: Unknown format '{fmt}'. Valid: {valid_formats}", file=sys.stderr)
            return 1

    print(f"Processing: {video_path}")
    print(f"Output directory: {output_dir}")

    # Step 1: Extract audio
    audio_path = output_dir / f"{base_name}.wav"
    print(f"Extracting audio to: {audio_path}")

    try:
        audio_info = extract_audio(video_path, audio_path)
        print(f"Audio extracted: {format_duration(audio_info.duration_s)}")
    except Exception as e:
        print(f"Error extracting audio: {e}", file=sys.stderr)
        return 1

    # Step 2: Configure and run transcription
    config = TranscriptionConfig(
        model_name=parsed.model,
        language=parsed.language,
        word_timestamps=not parsed.no_words,
        device=parsed.device,
        compute_type=parsed.compute_type,
        vad_filter=not parsed.no_vad,
    )

    print(f"Loading model: {parsed.model} (engine: {parsed.engine})")

    try:
        engine_class = get_engine(parsed.engine)
        with engine_class(config) as engine:
            print("Transcribing...")
            transcript = engine.transcribe(audio_path, source_video=video_path)
    except Exception as e:
        print(f"Error during transcription: {e}", file=sys.stderr)
        return 1

    print(f"Transcription complete: {len(transcript.segments)} segments")

    if transcript.metadata.detected_language:
        lang = transcript.metadata.detected_language
        prob = transcript.metadata.language_probability
        prob_str = f" ({prob:.1%})" if prob else ""
        print(f"Detected language: {lang}{prob_str}")

    # Step 3: Write outputs
    try:
        if "json" in formats:
            json_path = output_dir / f"{base_name}.json"
            write_json(transcript, json_path)
            print(f"Written: {json_path}")

        if "txt" in formats:
            txt_path = output_dir / f"{base_name}.txt"
            write_txt(transcript, txt_path)
            print(f"Written: {txt_path}")

        if "srt" in formats:
            srt_path = output_dir / f"{base_name}.srt"
            write_srt(transcript, srt_path)
            print(f"Written: {srt_path}")
    except Exception as e:
        print(f"Error writing output: {e}", file=sys.stderr)
        return 1

    print("Done!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
