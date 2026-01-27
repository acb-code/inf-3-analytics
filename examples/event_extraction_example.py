"""Event extraction example using OpenAI and rule-based engines.

This script showcases:
- Input: transcript JSON file (from transcription step)
- Function calls: rules extraction -> LLM extraction with correlation
- Output: JSON and Markdown event files

Run:
  # First, create a transcript (if you don't have one)
  uv run inf3-transcribe --video inspection.MOV --out outputs

  # Then run event extraction with rules only
  uv run python examples/event_extraction_example.py --transcript outputs/inspection.json

  # Or with OpenAI LLM + rules correlation
  uv run python examples/event_extraction_example.py --transcript outputs/inspection.json --use-llm

Notes:
- Requires OPENAI_API_KEY when using --use-llm flag.
- The --include-rules flag runs rules first, then correlates with LLM events.
"""

from __future__ import annotations

import argparse
import os
from datetime import datetime
from pathlib import Path

from inf3_analytics.engines.event_extraction import EventExtractionConfig
from inf3_analytics.engines.event_extraction.rules import RuleBasedEventEngine
from inf3_analytics.io.event_writer import write_json, write_markdown
from inf3_analytics.io.transcript_writer import read_json as read_transcript_json
from inf3_analytics.types.event import Event, EventList


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Example: Event extraction from transcripts",
    )
    parser.add_argument(
        "--transcript",
        type=Path,
        required=True,
        help="Input transcript JSON file (from transcription step)",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=Path("./outputs/events-example"),
        help="Output directory (default: ./outputs/events-example)",
    )
    parser.add_argument(
        "--use-llm",
        action="store_true",
        help="Use OpenAI LLM for extraction in addition to rules",
    )
    parser.add_argument(
        "--llm-model",
        type=str,
        default="gpt-5-mini",
        help="LLM model name (default: gpt-5-mini)",
    )
    parser.add_argument(
        "--min-confidence",
        type=float,
        default=0.3,
        help="Minimum confidence threshold (default: 0.3)",
    )
    return parser.parse_args()


def _validate_env(use_llm: bool) -> None:
    if use_llm and not os.environ.get("OPENAI_API_KEY"):
        raise RuntimeError(
            "OPENAI_API_KEY is not set. Export it before running with --use-llm."
        )


def main() -> int:
    args = parse_args()

    _validate_env(args.use_llm)

    transcript_path = args.transcript
    output_dir = args.out
    output_dir.mkdir(parents=True, exist_ok=True)

    # 1) Load transcript
    print(f"Loading transcript: {transcript_path}")
    transcript = read_transcript_json(transcript_path)
    print(f"Loaded {len(transcript.segments)} segments")

    # 2) Configure extraction
    config = EventExtractionConfig(
        context_window=1,
        min_confidence=args.min_confidence,
        merge_gap_s=5.0,
        llm_model=args.llm_model,
        max_segments_per_batch=20,
    )

    all_events: list[Event] = []
    engines_used: list[str] = []

    # 3) Run rules-based extraction
    print("Running rules-based extraction...")
    with RuleBasedEventEngine(config) as rules_engine:
        rule_events = rules_engine.extract(transcript)
    print(f"Rules engine found {len(rule_events)} events")

    if not args.use_llm:
        # Rules only mode
        all_events.extend(rule_events)
        engines_used.append("rules")
    else:
        # 4) Run LLM extraction with correlation
        print(f"Running OpenAI LLM extraction (model: {args.llm_model})...")

        from inf3_analytics.engines.event_extraction.llm import OpenAIEventEngine

        with OpenAIEventEngine(config) as llm_engine:
            llm_events = llm_engine.extract(transcript, rule_events=rule_events)
        print(f"LLM engine found {len(llm_events)} events")

        # Add LLM events
        all_events.extend(llm_events)
        engines_used.append(f"openai/{args.llm_model}")

        # Add uncorrelated rule events
        correlated_ids: set[str] = set()
        for event in llm_events:
            if event.related_rule_events:
                correlated_ids.update(event.related_rule_events.rule_event_ids)
                print(
                    f"LLM event '{event.title}' correlates with rule events: "
                    f"{event.related_rule_events.rule_event_ids}"
                )

        uncorrelated_count = 0
        for rule_event in rule_events:
            if rule_event.event_id not in correlated_ids:
                all_events.append(rule_event)
                uncorrelated_count += 1

        if uncorrelated_count > 0:
            print(f"Added {uncorrelated_count} uncorrelated rule events")
            engines_used.append("rules")

    # Sort by start time
    all_events.sort(key=lambda e: e.start_s)

    print(f"\nTotal events: {len(all_events)}")

    # 5) Create EventList and write outputs
    engine_str = "+".join(sorted(set(engines_used)))
    event_list = EventList(
        events=tuple(all_events),
        source_transcript_path=str(transcript_path),
        extraction_engine=engine_str,
        extraction_timestamp=datetime.now().isoformat(),
    )

    base_name = transcript_path.stem
    json_path = output_dir / f"{base_name}_events.json"
    md_path = output_dir / f"{base_name}_events.md"

    write_json(event_list, json_path)
    write_markdown(event_list, md_path)

    print("\nWritten outputs:")
    print(f"- {json_path}")
    print(f"- {md_path}")

    # 6) Print summary
    print("\n--- Event Summary ---")
    event_types: dict[str, int] = {}
    for event in all_events:
        event_type = event.event_type.value
        event_types[event_type] = event_types.get(event_type, 0) + 1

    for event_type, count in sorted(event_types.items()):
        print(f"  {event_type}: {count}")

    # Show correlated events if any
    correlated_events = [e for e in all_events if e.related_rule_events]
    if correlated_events:
        print(f"\nCorrelated events (LLM + rules): {len(correlated_events)}")
        for event in correlated_events[:5]:  # Show first 5
            print(f"  - {event.title}")
            print(f"    Related rules: {event.related_rule_events.rule_event_ids}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
