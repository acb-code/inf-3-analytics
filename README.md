# inf3-analytics

Infrastructure inspection video analytics pipeline with synchronized timestamps.

## Quick Start (Gemini Pipeline + Frontend)

This walks through a full AI analytics pipeline using Gemini, then runs the frontend UI.

### 1) Prereqs (minimal)

- Python 3.11+
- Node.js 18+
- [FFmpeg](https://ffmpeg.org/) on PATH
- A sample video at `data/inspection.MOV`

### 2) Install dependencies

```bash
uv sync --extra gemini --extra api
```

Available extras:
- `dev` (tests, lint, typing)
- `openai` (OpenAI APIs)
- `gemini` (Google Gemini APIs)
- `cloud` (OpenAI + Gemini)
- `cv` (OpenCV + NumPy)
- `api` (FastAPI + Uvicorn)

### 3) .env setup

Create a `.env` file at the repo root:

```bash
GEMINI_API_KEY=your-api-key
# Optional:
# OPENAI_API_KEY=your-api-key
# INF3_DATA_ROOT=/absolute/path/to/inf-3-analytics
```

### 3) Run the Gemini pipeline

```bash
# Step 1: Transcribe (Gemini)
uv run --env-file .env inf3-transcribe --video data/inspection.MOV --out outputs --engine gemini

# Step 2: Extract events (Gemini)
uv run --env-file .env inf3-extract-events --transcript outputs/inspection.json --engine gemini

# Step 3: Extract frames for each event
uv run inf3-extract-event-frames \
  --video data/inspection.MOV \
  --events outputs/events/inspection_events.json

# Step 4: Frame analytics (Gemini VLM)
uv run --env-file .env inf3-frame-analytics --event-frames outputs/event_frames --out outputs/frame_analytics
```

### 4) Start API + Frontend

```bash
# API (serves artifacts + video)
uv run python -m inf3_analytics.api
```

In another terminal:

```bash
cd frontend
npm install
cp .env.local.example .env.local
npm run dev
```

Then open `http://localhost:3000/runs`.

---

## Remote Testing (Option A: Cloudflare Quick Tunnel + Caddy)

This option gives you a public HTTPS URL without a domain name and keeps the pipeline running on your local machine.

### 1) Start the API with an isolated data root

```bash
mkdir -p demo_data
export INF3_DATA_ROOT="$PWD/demo_data"
export INF3_REGISTRY_PATH="$PWD/demo_data/registry.json"
export INF3_MAX_UPLOAD_SIZE_MB=300
uv run --extra cloud --extra api uvicorn inf3_analytics.api.app:app --host 127.0.0.1 --port 8000
```

### 2) Start the frontend (same-origin API)

```bash
cd frontend
export NEXT_PUBLIC_INF3_API_BASE=
npm run dev -- --hostname 127.0.0.1 --port 3000
```

### 3) Run Caddy as a local reverse proxy with basic auth

```bash
export BASIC_AUTH_USER=tester
export BASIC_AUTH_HASH="$(caddy hash-password --plaintext 'your-strong-password')"
caddy run --config ../Caddyfile.tunnel.example
```

### 4) Create the public HTTPS URL (Quick Tunnel)

```bash
cloudflared tunnel --url http://127.0.0.1:8080
```

Share the printed `https://*.trycloudflare.com` URL and the basic-auth credentials with your tester.

### Security notes

- Keep `INF3_DATA_ROOT` pointed at an isolated folder (like `demo_data`) so uploads/outputs are the only accessible files.
- Shut down the tunnel when testing is done.
- Use a strong password in `BASIC_AUTH_HASH`.

### Cost notes

- Quick Tunnel is typically free; compute runs on your machine.
- API usage is billed to your OpenAI/Gemini keys.

---

## Prerequisites (Full)

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

## CLI Usage (Reference)

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

## Python API (Reference)

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
uv run inf3-extract-events --transcript outputs/inspection.json

# OpenAI LLM extraction
uv run --env-file .env inf3-extract-events --transcript outputs/inspection.json --engine openai

# Gemini LLM extraction
uv run --env-file .env inf3-extract-events --transcript outputs/inspection.json --engine gemini

# Combined: LLM + rules with correlation
uv run --env-file .env inf3-extract-events --transcript outputs/inspection.json --engine openai --include-rules

# Custom confidence threshold
uv run inf3-extract-events --transcript outputs/inspection.json --min-confidence 0.5
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

### LLM Smoke Tests (examples/)

Quick scripts that validate `.env` loading and model connectivity (direct API only).

```bash
# Install provider SDKs
uv sync --extra openai
uv sync --extra gemini

# OpenAI smoke test (direct API)
uv run python examples/llm_openai_smoke.py

# Gemini smoke test (direct API)
uv run python examples/llm_gemini_smoke.py
```

Make sure `.env` includes the relevant API keys:

```bash
OPENAI_API_KEY=your-openai-api-key
GEMINI_API_KEY=your-gemini-api-key
```

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

## Step 3: Frame Extraction

Extract video frames for each event's time window:

### CLI Usage

```bash
# Extract 5 frames per event (default)
uv run inf3-extract-event-frames --video data/inspection.MOV --events outputs/inspection_events.json

# Extract 10 frames per event
uv run inf3-extract-event-frames --video data/inspection.MOV --events outputs/inspection_events.json --n 10

# Use fixed FPS sampling (2 FPS, max 20 frames)
uv run inf3-extract-event-frames --video data/inspection.MOV --events outputs/inspection_events.json --policy fps --fps 2 --max-frames 20
```

### Output Structure

```
outputs/event_frames/
├── manifest.json                    # Top-level manifest
├── evt_001_crack_detected/
│   ├── frames.json                  # Per-event frame metadata
│   └── frames/
│       ├── 000_00-00-10.500.jpg
│       ├── 001_00-00-12.250.jpg
│       └── ...
└── evt_002_corrosion_found/
    └── ...
```

## Step 4: Frame Analytics (VLM-first)

Run VLM-based analysis on extracted frames to detect infrastructure issues:

### Setup

```bash
# For OpenAI (GPT-5-mini)
export OPENAI_API_KEY=your-api-key
uv sync --extra openai

# For Gemini (gemini-3-flash-preview)
export GEMINI_API_KEY=your-api-key
uv sync --extra gemini

# For baseline quality metrics (no API required)
uv sync --extra cv
```

### CLI Usage

```bash
# Analyze with Gemini (default VLM engine)
uv run --env-file .env inf3-frame-analytics --event-frames outputs/event_frames --out outputs/frame_analytics

# Analyze with OpenAI GPT-5-mini
uv run --env-file .env inf3-frame-analytics --event-frames outputs/event_frames --engine openai

# Use baseline quality metrics (no API, local only)
uv run inf3-frame-analytics --event-frames outputs/event_frames --engine baseline_quality

# With event context for richer prompts
uv run --env-file .env inf3-frame-analytics --event-frames outputs/event_frames --events outputs/events.json

# Rate limiting for cost control
uv run --env-file .env inf3-frame-analytics --event-frames outputs/event_frames \
  --max-frames-per-event 5 \
  --max-total-frames 50 \
  --sleep-ms 500

# Dry run - see what would be processed without API calls
uv run inf3-frame-analytics --event-frames outputs/event_frames --dry-run
```

### Output Structure

```
outputs/frame_analytics/
├── manifest_analytics.json          # Run manifest with traceability
├── analytics_report.md              # Human-readable summary
├── evt_001_crack/
│   ├── frame_analyses.jsonl         # Per-frame results (one JSON per line)
│   └── event_summary.json           # Aggregated event summary
└── evt_002_corrosion/
    └── ...
```

### Detection Types

| Type | Description |
|------|-------------|
| structural_anomaly | Deformation, displacement, general structural issues |
| corrosion | Rust, oxidation, material degradation |
| crack | Cracks, fractures, splits |
| spalling | Concrete spalling, surface deterioration |
| leak | Water damage, staining, moisture |
| obstruction | Blockages, debris |
| safety_risk | Safety hazards |
| equipment_issue | Camera/image quality issues (baseline engine) |

### Analytics Engines

| Engine | Description | API Key | Use Case |
|--------|-------------|---------|----------|
| gemini | Gemini-3-Flash-Preview VLM | GEMINI_API_KEY | Primary (recommended) |
| openai | GPT-5-mini VLM | OPENAI_API_KEY | Primary alternative |
| baseline_quality | OpenCV quality metrics | None | Fallback, image QA |

### Cost and Latency Considerations

VLM APIs incur costs per image analyzed. Use these options to control:

- `--max-frames-per-event N`: Limit frames analyzed per event
- `--max-total-frames N`: Cap total frames in a run
- `--sleep-ms N`: Rate limit between API calls
- `--dry-run`: Preview what would be processed

The baseline_quality engine is free and instant but only detects image quality issues (blur, exposure), not infrastructure defects.

### Traceability

Every analysis result includes full traceability:

```json
{
  "engine": {
    "name": "vlm",
    "provider": "gemini",
    "model": "gemini-3-flash-preview",
    "prompt_version": "v1",
    "version": "0.1.0"
  },
  "event_id": "evt_001",
  "frame_idx": 0,
  "timestamp_s": 10.5
}
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

### Frame Extraction (inf3-extract-event-frames)

```
usage: inf3-extract-event-frames [-h] --video VIDEO --events EVENTS [--out OUT]
                                 [--policy {nframes,fps}] [--n N] [--fps FPS]
                                 [--max-frames MAX_FRAMES] [--quality 1-31]

Options:
  --video         Input video file (required)
  --events        Input events JSON file (required)
  --out           Output directory (default: ./outputs/event_frames)
  --policy        Frame sampling policy: nframes or fps (default: nframes)
  --n             Frames per event for nframes policy (default: 5)
  --fps           Frames per second for fps policy (default: 1.0)
  --max-frames    Max frames per event for fps policy (default: 30)
  --quality       JPEG quality 1-31, lower is better (default: 2)
```

### Frame Analytics (inf3-frame-analytics)

```
usage: inf3-frame-analytics [-h] --event-frames EVENT_FRAMES [--events EVENTS]
                            [--out OUT] [--engine {gemini,openai,baseline_quality}]
                            [--model MODEL] [--max-frames-per-event N]
                            [--max-total-frames N] [--sleep-ms N]
                            [--fallback-to-baseline] [--dry-run]

Options:
  --event-frames  Directory with event frames and manifest.json (required)
  --events        Optional events.json for richer context
  --out           Output directory (default: ./outputs/frame_analytics)
  --engine        Analytics engine: gemini, openai, baseline_quality (default: gemini)
  --model         Override model name (e.g., gpt-5-mini, gemini-3-flash-preview)
  --max-frames-per-event  Max frames to analyze per event (default: 10)
  --max-total-frames      Max total frames to analyze (default: 100)
  --sleep-ms              Delay between API requests in ms (default: 200)
  --fallback-to-baseline  Fall back to baseline if VLM fails
  --dry-run               Show what would be processed without API calls
```

## REST API

The pipeline includes a FastAPI-based REST API for managing runs and retrieving artifacts.

### Starting the Server

```bash
# Start the API server (default: http://0.0.0.0:8000)
uv run python -m inf3_analytics.api

# With uvicorn options
uv run uvicorn inf3_analytics.api.app:app --reload --port 8000
```

### Configuration

Configure via environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `INF3_DATA_ROOT` | Current directory | Root path for security validation |
| `INF3_REGISTRY_PATH` | `.inf3-analytics/registry.json` | Path to run registry file |
| `INF3_CORS_ORIGINS` | `["http://localhost:3000", "http://localhost:8080"]` | Allowed CORS origins |

### API Endpoints

#### Runs

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/runs` | Register a new pipeline run |
| `GET` | `/runs` | List all registered runs |
| `GET` | `/runs/{run_id}` | Get run details and available artifacts |

#### Artifacts

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/runs/{run_id}/artifacts/transcript` | Get transcript JSON |
| `GET` | `/runs/{run_id}/artifacts/events` | Get events JSON |
| `GET` | `/runs/{run_id}/artifacts/event-frames/manifest` | Get event frames manifest |
| `GET` | `/runs/{run_id}/artifacts/frame-analytics/manifest` | Get frame analytics manifest |

#### Video Streaming

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/runs/{run_id}/video` | Stream video with HTTP Range support |

### Example Usage

```bash
# Create a new run
curl -X POST http://localhost:8000/runs \
  -H "Content-Type: application/json" \
  -d '{"video_path": "/path/to/video.mp4", "run_root": "/path/to/outputs"}'

# List all runs
curl http://localhost:8000/runs

# Get run details with artifact availability
curl http://localhost:8000/runs/{run_id}

# Fetch transcript
curl http://localhost:8000/runs/{run_id}/artifacts/transcript

# Fetch events
curl http://localhost:8000/runs/{run_id}/artifacts/events
```

### OpenAPI Documentation

When the server is running, interactive API docs are available at:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

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
