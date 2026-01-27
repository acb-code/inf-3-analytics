# inf3-analytics

Infrastructure inspection video analytics pipeline with synchronized timestamps.

## Prerequisites

- Python 3.11+
- [FFmpeg](https://ffmpeg.org/) (required for audio extraction)
- CUDA-compatible GPU (optional, for faster transcription)

### Installing FFmpeg

```bash
# Ubuntu/Debian
sudo apt install ffmpeg

# macOS
brew install ffmpeg

# Windows
# Download from https://ffmpeg.org/download.html
```

## Installation

```bash
# Clone the repository
git clone <repository-url>
cd inf-3-analytics

# Install with uv (recommended)
uv sync

# Or install with pip
pip install -e ".[dev]"
```

## Quick Start

### CLI Usage

```bash
# Basic transcription
uv run inf3-transcribe --video inspection.mp4

# Specify output directory
uv run inf3-transcribe --video inspection.mp4 --out outputs/run1

# With GPU acceleration and larger model
uv run inf3-transcribe --video inspection.mp4 --model large-v3 --device cuda

# Specify language (skip auto-detection)
uv run inf3-transcribe --video inspection.mp4 --language en

# Select output formats
uv run inf3-transcribe --video inspection.mp4 --format json,srt
```

### Python API

```python
from pathlib import Path
from inf3_analytics.media import extract_audio
from inf3_analytics.engines.transcription import FasterWhisperEngine, TranscriptionConfig
from inf3_analytics.io import write_json, write_srt

# Extract audio from video
video_path = Path("inspection.mp4")
audio_info = extract_audio(video_path, Path("outputs/audio.wav"))

# Configure and run transcription
config = TranscriptionConfig(
    model_name="base",
    language="en",
    word_timestamps=True,
    device="auto",
)

with FasterWhisperEngine(config) as engine:
    transcript = engine.transcribe(audio_info.path, source_video=video_path)

# Write outputs
write_json(transcript, Path("outputs/transcript.json"))
write_srt(transcript, Path("outputs/transcript.srt"))

# Access transcript data
print(f"Duration: {transcript.metadata.duration_s:.1f}s")
print(f"Segments: {len(transcript.segments)}")

for segment in transcript.segments:
    print(f"[{segment.start_ts}] {segment.text}")
```

## Output Formats

| Format | Description |
|--------|-------------|
| JSON | Full structured output with metadata, segments, and word-level timestamps |
| TXT | Plain text with timestamps |
| SRT | SubRip subtitle format for video players |

### Output Structure

```
outputs/
├── video_name.wav      # Extracted audio (mono 16kHz)
├── video_name.json     # Full transcript with metadata
├── video_name.txt      # Plain text with timestamps
└── video_name.srt      # SubRip subtitles
```

## Models

| Model | Size | Speed | Accuracy | Use Case |
|-------|------|-------|----------|----------|
| tiny | 74 MB | Fastest | Lower | Quick previews |
| base | 145 MB | Fast | Good | Development, testing |
| small | 488 MB | Medium | Better | General use |
| medium | 1.5 GB | Slow | High | Quality transcription |
| large-v3 | 3.1 GB | Slowest | Highest | Best accuracy |
| turbo | 1.6 GB | Fast | High | Production (balanced) |

## Cloud Transcription (Optional)

In addition to the local `faster-whisper` engine, you can use cloud-based transcription services.

### OpenAI Engine

Uses OpenAI's Whisper API for transcription. Returns accurate word-level timestamps.

```bash
# Set API key
export OPENAI_API_KEY=your-api-key

# Install OpenAI dependency
uv sync --extra openai

# Run transcription
uv run --env-file .env inf3-transcribe --video inspection.MOV --engine openai
```

### Gemini Engine

Uses Google's Gemini API for transcription. Note: timestamps are approximated since Gemini doesn't provide native audio timestamps.

```bash
# Set API key
export GEMINI_API_KEY=your-api-key

# Install Gemini dependency
uv sync --extra gemini

# Run transcription
uv run inf3-transcribe --video inspection.mp4 --engine gemini
```

### Cloud Engine Comparison

| Engine | Timestamps | Word-level | Cost | Notes |
|--------|------------|------------|------|-------|
| faster-whisper | Native | Yes | Free | Requires local compute (GPU optional) |
| openai | Native | Yes | ~$0.006/min | Requires internet, 25MB file limit |
| gemini | Approximated | No | Variable | Requires internet, timestamps estimated |

## Step 2: Event Extraction

After transcription, extract events from the transcript:

### CLI Usage

```bash
# Basic rule-based extraction
uv run inf3-extract-events --transcript outputs/video.json

# OpenAI LLM extraction
uv run inf3-extract-events --transcript outputs/video.json --engine openai

# Gemini LLM extraction
uv run inf3-extract-events --transcript outputs/video.json --engine gemini

# Combined: LLM + rules with correlation
uv run inf3-extract-events --transcript outputs/video.json --engine openai --include-rules

# Custom confidence threshold
uv run inf3-extract-events --transcript outputs/video.json --min-confidence 0.5
```

### Python API

```python
from pathlib import Path
from inf3_analytics.engines.event_extraction import EventExtractionConfig
from inf3_analytics.engines.event_extraction.rules import RuleBasedEventEngine
from inf3_analytics.io.transcript_writer import read_json as read_transcript
from inf3_analytics.io.event_writer import write_json, write_markdown

# Load transcript
transcript = read_transcript(Path("outputs/video.json"))

# Configure extraction
config = EventExtractionConfig(
    context_window=1,
    min_confidence=0.3,
    merge_gap_s=5.0,
)

# Extract events with rules engine
with RuleBasedEventEngine(config) as engine:
    events = engine.extract(transcript)

print(f"Found {len(events)} events")
for event in events:
    print(f"[{event.start_ts}] {event.event_type.value}: {event.title}")
```

### LLM Extraction with Correlation

```python
from inf3_analytics.engines.event_extraction.llm import OpenAIEventEngine
from inf3_analytics.engines.event_extraction.rules import RuleBasedEventEngine

# First, run rules-based extraction
with RuleBasedEventEngine(config) as rules_engine:
    rule_events = rules_engine.extract(transcript)

# Then run LLM extraction with correlation
config.llm_model = "gpt-5-mini"
with OpenAIEventEngine(config) as llm_engine:
    llm_events = llm_engine.extract(transcript, rule_events=rule_events)

# LLM events include correlation info
for event in llm_events:
    if event.related_rule_events:
        print(f"LLM event correlates with: {event.related_rule_events.rule_event_ids}")
```

### Event Types

| Type | Description |
|------|-------------|
| structural_anomaly | Crack, corrosion, deformation, damage |
| safety_risk | Dangerous conditions, hazards |
| maintenance_note | Repair recommendations, service needs |
| measurement | Numeric measurements reported |
| location_reference | Location or position mentioned |
| uncertainty | Questions or unclear observations |
| observation | General inspection observation |
| other | Uncategorized events |

### Event Extraction Engines

| Engine | Description | API Key |
|--------|-------------|---------|
| rules | Keyword matching (fast, offline) | None |
| openai | GPT-based extraction (gpt-5-mini default) | OPENAI_API_KEY |
| gemini | Gemini-based extraction (gemini-3-flash-preview default) | GEMINI_API_KEY |

### Event Output Formats

| Format | Description |
|--------|-------------|
| JSON | Full structured output with events, metadata, and correlations |
| Markdown | Human-readable summary grouped by event type |
| NDJSON | One event per line (streaming format) |

### Visualize Event Outputs

Use the visualization utility to see a quick summary and timeline:

```bash
uv run python examples/event_visualize.py --events outputs/events/inspection_events.json
uv run python examples/event_visualize.py --events outputs/events/*.json --bin-size 10
```

## CLI Options

### Transcription (inf3-transcribe)

```
usage: inf3-transcribe [-h] --video VIDEO [--out OUT] [--language LANGUAGE]
                       [--model {tiny,base,small,medium,large-v3,turbo}]
                       [--engine {faster-whisper,openai,gemini}]
                       [--device {auto,cpu,cuda}]
                       [--compute-type {default,int8,float16,float32}]
                       [--no-words] [--format FORMAT] [--no-vad]

Options:
  --video         Input video file path (required)
  --out           Output directory (default: ./outputs/events)
  --language      Language code (e.g., 'en', 'es') or auto-detect
  --model         Whisper model size (default: base)
  --engine        Transcription engine (default: faster-whisper)
                  - faster-whisper: Local Whisper (no API key needed)
                  - openai: OpenAI Whisper API (requires OPENAI_API_KEY)
                  - gemini: Google Gemini (requires GEMINI_API_KEY)
  --device        Compute device: auto, cpu, cuda (default: auto)
  --compute-type  Model precision (default: auto-select)
  --no-words      Disable word-level timestamps
  --format        Output formats, comma-separated (default: json,txt,srt)
  --no-vad        Disable voice activity detection filter
```

### Event Extraction (inf3-extract-events)

```
usage: inf3-extract-events [-h] --transcript TRANSCRIPT [--out OUT]
                           [--engine {rules,openai,gemini}]
                           [--llm-model LLM_MODEL] [--include-rules]
                           [--context-window CONTEXT_WINDOW]
                           [--min-confidence MIN_CONFIDENCE]
                           [--merge-gap MERGE_GAP] [--format FORMAT]

Options:
  --transcript    Input transcript JSON file (required)
  --out           Output directory (default: ./outputs)
  --engine        Extraction engine: rules, openai, gemini (default: rules)
  --llm-model     LLM model name (default: gpt-5-mini or gemini-3-flash-preview)
  --include-rules When using LLM, also run rules and correlate events
  --context-window Context segments around triggers (default: 1)
  --min-confidence Minimum confidence threshold (default: 0.3)
  --merge-gap     Max gap to merge adjacent events (default: 5.0s)
  --format        Output formats: json,md,ndjson (default: json,md)
```

## Development

```bash
# Run tests
uv run pytest

# Run tests with coverage
uv run pytest --cov=inf3_analytics

# Type checking
uv run mypy src/

# Linting
uv run ruff check src/

# Format code
uv run ruff format src/
```

## License

MIT
