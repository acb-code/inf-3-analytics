# inf3-analytics Development Context

## Project Overview

This is an infrastructure inspection video analytics pipeline. The core philosophy is **timestamp as spine**: every piece of analysis (transcription, object detection, frame descriptions, events) is anchored to precise video timestamps, enabling synchronization across modalities.

## Architecture Philosophy

1. **Timestamp Spine**: All data types include both seconds (`start_s`, `end_s`) and formatted timestamps (`start_ts`, `end_ts`) for flexibility
2. **Immutable Data**: Core types use frozen dataclasses with tuple collections
3. **Engine Abstraction**: Processing engines (transcription, vision, etc.) follow a common protocol pattern
4. **Modular IO**: Separate readers/writers for each output format

Prefer conciseness and simplicity.

## Project Roadmap

### Step 1: Video Transcription (Complete)
- Audio extraction via FFmpeg
- Faster-Whisper transcription with word-level timestamps
- Cloud engines: OpenAI, Gemini
- Output: JSON, TXT, SRT formats

### Step 2: Event Extraction (Complete)
- Rule-based keyword extraction
- LLM-based extraction (OpenAI, Gemini)
- Event correlation between engines
- Output: JSON, Markdown, NDJSON

### Step 3: Frame Extraction (Complete)
- Configurable frame sampling (N-frames, fixed FPS)
- Frame metadata with timestamps aligned to events
- JPEG output with quality control

### Step 4: Frame Analytics (Complete)
- **VLM-first approach**: Primary analysis via vision-language models
- Engines: Gemini-3-Flash-Preview, GPT-5-mini
- Fallback: Baseline quality metrics (OpenCV)
- Per-frame detections with bounding boxes
- Event-level aggregation and summaries

### Step 5: Video Pipeline Alignment (Planned)
- Frame extraction with transcript timestamp alignment
- Unified timeline across modalities

### Step 6: Multimodal Detection (Planned)
- Combined audio + visual event detection
- Cross-modal reconciliation

### Step 7: 3D Reconstruction (Planned)
- Point cloud generation from video
- Spatial analysis

### Step 8: Design Model Comparison (Planned)
- Tag events in 3D space
- Compare to design models

### Step 9: API Service (Planned)
- FastAPI integration
- Job queue
- Progress tracking

## VLM-First Approach (Step 4)

Frame analytics prioritizes vision-language models for infrastructure inspection:

### Engine Priority
1. **Primary**: OpenAI (default for frame analytics and site analytics)
2. **Secondary**: Gemini VLM for semantic understanding
3. **Fallback**: Baseline quality metrics for image QA when VLM unavailable; YOLO for local site analytics

### Prompt Versioning
Prompts are versioned and stored in code (`prompting.py`):
- `PROMPT_VERSION = "v1"` tracks prompt changes
- Version recorded in all outputs for reproducibility
- Enables A/B testing of prompt improvements

### Traceability Fields
Every frame analysis includes:
```python
EngineInfo(
    name="vlm",                    # Engine type
    provider="gemini",             # API provider
    model="gemini-3-flash-preview", # Model name
    prompt_version="v1",           # Prompt version
    version="0.1.0",               # Engine code version
    config={...}                   # Runtime config
)
```

### Detection Schema
Structured output with validation:
- Detection type enum (crack, corrosion, leak, etc.)
- Confidence scores (0-1)
- Optional bounding boxes (normalized coordinates)
- Severity levels (low/medium/high)
- QA pairs from inspection checklist


## Coding Conventions

- **Type hints**: All functions have full type annotations
- **Docstrings**: Google-style docstrings for public APIs
- **Immutability**: Prefer frozen dataclasses and tuples
- **Error handling**: Custom exceptions with clear messages
- **Testing**: Unit tests that don't require network/model downloads

## Running the Project

```bash
# Install dependencies
uv sync

# Run transcription
uv run inf3-transcribe --video <path> --out outputs/

# Run tests
uv run pytest

# Type check
uv run mypy src/
```
