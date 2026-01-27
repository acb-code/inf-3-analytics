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

### Step 1: Video Transcription (Current)
- Audio extraction via FFmpeg
- Faster-Whisper transcription with word-level timestamps
- Output: JSON, TXT, SRT formats

### Step 2: Frame Extraction (Planned)
- Configurable frame sampling (FPS-based, scene change, keyframes)
- Frame metadata with timestamps
- Thumbnail generation

### Step 3: Vision Analysis (Planned)
- Frame description using vision models
- Object detection integration
- Defect/anomaly detection for infrastructure

### Step 4: Event Detection (Planned)
- Audio event detection (alarms, impacts, speech patterns)
- Visual event detection (motion, scene changes)
- Event timeline generation

### Step 5: Multimodal Alignment (Planned)
- Cross-modal timestamp alignment
- Unified timeline with all modalities
- Conflict resolution strategies

### Step 6: Search & Query (Planned)
- Text search across transcripts
- Semantic search with embeddings
- Time-range queries

### Step 7: Report Generation (Planned)
- Summary generation
- Highlight extraction
- Export to various formats

### Step 8: Streaming Support (Planned)
- Real-time processing
- Incremental updates
- WebSocket API

### Step 9: API Service (Planned)
- REST API
- Job queue
- Progress tracking


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
