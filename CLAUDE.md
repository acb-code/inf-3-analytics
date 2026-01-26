# inf3-analytics Development Context

## Project Overview

This is an infrastructure inspection video analytics pipeline. The core philosophy is **timestamp as spine**: every piece of analysis (transcription, object detection, frame descriptions, events) is anchored to precise video timestamps, enabling synchronization across modalities.

## Architecture Philosophy

1. **Timestamp Spine**: All data types include both seconds (`start_s`, `end_s`) and formatted timestamps (`start_ts`, `end_ts`) for flexibility
2. **Immutable Data**: Core types use frozen dataclasses with tuple collections
3. **Engine Abstraction**: Processing engines (transcription, vision, etc.) follow a common protocol pattern
4. **Modular IO**: Separate readers/writers for each output format

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

## Directory Structure

```
src/inf3_analytics/
├── types/          # Core data types (dataclasses)
├── utils/          # Shared utilities (time formatting, etc.)
├── media/          # Media processing (audio/video extraction)
├── engines/        # Processing engines (transcription, vision, etc.)
│   └── transcription/
├── io/             # Input/output handlers
└── cli/            # Command-line interfaces
```

## Coding Conventions

- **Type hints**: All functions have full type annotations
- **Docstrings**: Google-style docstrings for public APIs
- **Immutability**: Prefer frozen dataclasses and tuples
- **Error handling**: Custom exceptions with clear messages
- **Testing**: Unit tests that don't require network/model downloads

## Key Types

### Transcript Types
- `Word`: Single word with timing and probability
- `Segment`: Transcript segment with optional word-level detail
- `Transcript`: Complete transcript with metadata
- `TranscriptMetadata`: Engine, model, language, duration info

### Media Types
- `AudioInfo`: Extracted audio file details
- `VideoInfo`: Video file metadata

### Engine Types
- `TranscriptionConfig`: Engine configuration
- `TranscriptionEngine`: Protocol for transcription backends

## Dependencies Rationale

- **faster-whisper**: CTranslate2-based Whisper, 4x faster than OpenAI implementation
- **pydantic**: For future API validation and settings management
- **FFmpeg**: Industry standard for audio/video processing

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

## When to Use Each Transcription Engine

| Engine | Best For | Limitations |
|--------|----------|-------------|
| faster-whisper | Offline use, privacy-sensitive data, best accuracy | Requires local compute; GPU recommended for speed |
| openai | Quick setup, no GPU available, accurate timestamps | Costs money, requires internet, 25MB file limit |
| gemini | Cost-effective cloud option, large files | Timestamps are approximated, no word-level timing |

### Decision Guide

1. **Use faster-whisper** (default) when:
   - You have a GPU or don't mind slower CPU processing
   - Data privacy is important
   - You need the most accurate timestamps
   - Working offline

2. **Use openai** when:
   - You need cloud processing without GPU
   - Accurate word-level timestamps are required
   - Files are under 25MB
   - You have an OpenAI API key

3. **Use gemini** when:
   - You want cloud processing with potentially lower costs
   - Exact timestamps are not critical
   - Processing large files that exceed OpenAI's limit

## Notes for Future Development

1. **Model caching**: faster-whisper downloads models to `~/.cache/huggingface/`
2. **GPU memory**: Large models need 4-8GB VRAM; use smaller models or CPU for limited hardware
3. **Audio format**: Whisper expects 16kHz mono; extraction handles conversion
4. **Timestamp precision**: Using milliseconds throughout; SRT format uses comma separator
5. **Cloud dependencies**: Install with `uv sync --extra openai` or `uv sync --extra gemini` or `uv sync --extra cloud` for both
