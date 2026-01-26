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

## CLI Options

```
usage: inf3-transcribe [-h] --video VIDEO [--out OUT] [--language LANGUAGE]
                       [--model {tiny,base,small,medium,large-v3,turbo}]
                       [--engine {faster-whisper}] [--device {auto,cpu,cuda}]
                       [--compute-type {default,int8,float16,float32}]
                       [--no-words] [--format FORMAT] [--no-vad]

Options:
  --video         Input video file path (required)
  --out           Output directory (default: ./outputs)
  --language      Language code (e.g., 'en', 'es') or auto-detect
  --model         Whisper model size (default: base)
  --engine        Transcription engine (default: faster-whisper)
  --device        Compute device: auto, cpu, cuda (default: auto)
  --compute-type  Model precision (default: auto-select)
  --no-words      Disable word-level timestamps
  --format        Output formats, comma-separated (default: json,txt,srt)
  --no-vad        Disable voice activity detection filter
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
