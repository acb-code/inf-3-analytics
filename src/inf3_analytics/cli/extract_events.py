"""CLI for event extraction from transcripts."""

import argparse
import sys
from datetime import datetime
from pathlib import Path

from inf3_analytics.engines.event_extraction import get_engine, list_engines
from inf3_analytics.engines.event_extraction.base import EventExtractionConfig
from inf3_analytics.io.event_writer import (
    write_json,
    write_markdown,
    write_ndjson,
)
from inf3_analytics.io.transcript_writer import read_json as read_transcript_json
from inf3_analytics.types.event import Event, EventList


def parse_args(args: list[str] | None = None) -> argparse.Namespace:
    """Parse command line arguments.

    Args:
        args: Command line arguments (uses sys.argv if None)

    Returns:
        Parsed arguments namespace
    """
    parser = argparse.ArgumentParser(
        prog="inf3-extract-events",
        description="Extract events from transcript files",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Rule-based extraction
  %(prog)s --transcript outputs/video.json

  # LLM-based extraction with OpenAI
  %(prog)s --transcript outputs/video.json --engine openai

  # Combined: rules + LLM with correlation
  %(prog)s --transcript outputs/video.json --engine openai --include-rules

  # Gemini with custom model
  %(prog)s --transcript outputs/video.json --engine gemini --llm-model gemini-2.0-flash

  # Output all formats
  %(prog)s --transcript outputs/video.json --format json,md,ndjson
        """,
    )

    parser.add_argument(
        "--transcript",
        "-t",
        type=Path,
        required=True,
        help="Input transcript JSON file",
    )

    parser.add_argument(
        "--out",
        "-o",
        type=Path,
        default=Path("./outputs/events"),
        help="Output directory (default: ./outputs/events)",
    )

    parser.add_argument(
        "--engine",
        type=str,
        default="rules",
        choices=list_engines(),
        help="Event extraction engine: rules (keyword-based), openai (GPT), gemini (default: rules)",
    )

    parser.add_argument(
        "--llm-model",
        type=str,
        default=None,
        help="LLM model name (default: gpt-5-mini for openai, gemini-3-flash-preview for gemini)",
    )

    parser.add_argument(
        "--include-rules",
        action="store_true",
        help="When using LLM engine, also run rules-based extraction and correlate events",
    )

    parser.add_argument(
        "--context-window",
        type=int,
        default=1,
        help="Context segments to include around triggers (default: 1)",
    )

    parser.add_argument(
        "--min-confidence",
        type=float,
        default=0.3,
        help="Minimum confidence threshold 0.0-1.0 (default: 0.3)",
    )

    parser.add_argument(
        "--merge-gap",
        type=float,
        default=5.0,
        help="Maximum gap in seconds to merge adjacent events (default: 5.0)",
    )

    parser.add_argument(
        "--max-segments-per-batch",
        type=int,
        default=20,
        help="Max segments per LLM batch (default: 20)",
    )

    parser.add_argument(
        "--format",
        type=str,
        default="json,md",
        help="Output formats, comma-separated: json,md,ndjson (default: json,md)",
    )

    parser.add_argument(
        "--language",
        type=str,
        default="en",
        help="Language code for output: en (English), fr (French) (default: en)",
    )

    return parser.parse_args(args)


def main(args: list[str] | None = None) -> int:
    """Main entry point for event extraction CLI.

    Args:
        args: Command line arguments (uses sys.argv if None)

    Returns:
        Exit code (0 for success, non-zero for errors)
    """
    parsed = parse_args(args)

    # Validate input
    transcript_path: Path = parsed.transcript
    if not transcript_path.exists():
        print(f"Error: Transcript file not found: {transcript_path}", file=sys.stderr)
        return 1

    # Parse output formats
    formats = [f.strip().lower() for f in parsed.format.split(",")]
    valid_formats = {"json", "md", "ndjson"}
    for fmt in formats:
        if fmt not in valid_formats:
            print(f"Error: Unknown format '{fmt}'. Valid: {valid_formats}", file=sys.stderr)
            return 1

    # Set up output directory
    output_dir: Path = parsed.out
    if output_dir in (Path("outputs"), Path("./outputs")):
        output_dir = output_dir / "events"
    output_dir.mkdir(parents=True, exist_ok=True)

    # Determine base name for output files
    base_name = transcript_path.stem
    if base_name.endswith("_transcript") or base_name.endswith(".transcript"):
        base_name = base_name.rsplit("_transcript", 1)[0].rsplit(".transcript", 1)[0]
    base_name = f"{base_name}_events"

    print(f"Loading transcript: {transcript_path}")

    # Load transcript
    try:
        transcript = read_transcript_json(transcript_path)
        print(f"Loaded {len(transcript.segments)} segments")
    except Exception as e:
        print(f"Error loading transcript: {e}", file=sys.stderr)
        return 1

    # Determine LLM model
    llm_model = parsed.llm_model
    if llm_model is None:
        if parsed.engine == "openai":
            llm_model = "gpt-5-mini"
        elif parsed.engine == "gemini":
            llm_model = "gemini-3-flash-preview"
        else:
            llm_model = "gpt-5-mini"  # Default

    # Configure engine
    config = EventExtractionConfig(
        context_window=parsed.context_window,
        min_confidence=parsed.min_confidence,
        merge_gap_s=parsed.merge_gap,
        llm_model=llm_model,
        max_segments_per_batch=parsed.max_segments_per_batch,
        language=parsed.language,
    )

    all_events: list[Event] = []
    rule_events: tuple[Event, ...] | None = None
    engines_used: list[str] = []

    # Step 1: Run rules-based extraction if needed
    if parsed.engine == "rules" or parsed.include_rules:
        print("Extracting events with rules engine...")
        try:
            from inf3_analytics.engines.event_extraction.rules import RuleBasedEventEngine

            with RuleBasedEventEngine(config) as rules_engine:
                rule_events = rules_engine.extract(transcript)
            print(f"Rules engine found {len(rule_events)} events")

            if parsed.engine == "rules":
                all_events.extend(rule_events)
                engines_used.append("rules")
        except Exception as e:
            print(f"Error during rules extraction: {e}", file=sys.stderr)
            return 1

    # Step 2: Run LLM-based extraction if selected
    if parsed.engine in ("openai", "gemini"):
        print(f"Extracting events with {parsed.engine} engine (model: {llm_model})...")
        try:
            engine_class = get_engine(parsed.engine)
            with engine_class(config) as llm_engine:
                # Pass rule events for correlation if available
                llm_events = llm_engine.extract(transcript, rule_events=rule_events)
            print(f"LLM engine found {len(llm_events)} events")

            all_events.extend(llm_events)
            engines_used.append(f"{parsed.engine}/{llm_model}")

            # If include_rules, add rule events that weren't correlated
            if parsed.include_rules and rule_events:
                # Find rule events that are already correlated
                correlated_ids: set[str] = set()
                for event in llm_events:
                    if event.related_rule_events:
                        correlated_ids.update(event.related_rule_events.rule_event_ids)

                # Add uncorrelated rule events
                for rule_event in rule_events:
                    if rule_event.event_id not in correlated_ids:
                        all_events.append(rule_event)
                        print(f"Added uncorrelated rule event: {rule_event.event_id}")

                engines_used.append("rules")

        except Exception as e:
            print(f"Error during LLM extraction: {e}", file=sys.stderr)
            return 1

    print(f"Total events: {len(all_events)}")

    # Sort events by start time
    all_events.sort(key=lambda e: e.start_s)

    # Create EventList
    engine_str = "+".join(sorted(set(engines_used)))
    event_list = EventList(
        events=tuple(all_events),
        source_transcript_path=str(transcript_path),
        extraction_engine=engine_str,
        extraction_timestamp=datetime.now().isoformat(),
    )

    # Write outputs
    try:
        if "json" in formats:
            json_path = output_dir / f"{base_name}.json"
            write_json(event_list, json_path)
            print(f"Written: {json_path}")

        if "md" in formats:
            md_path = output_dir / f"{base_name}.md"
            write_markdown(event_list, md_path)
            print(f"Written: {md_path}")

        if "ndjson" in formats:
            ndjson_path = output_dir / f"{base_name}.ndjson"
            write_ndjson(event_list, ndjson_path)
            print(f"Written: {ndjson_path}")
    except Exception as e:
        print(f"Error writing output: {e}", file=sys.stderr)
        return 1

    print("Done!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
