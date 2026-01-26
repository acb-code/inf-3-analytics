# inf3-analytics

Minimal video-to-text transcription pipeline built on `faster-whisper`.

## Prerequisites

- Python 3.11+
- [FFmpeg](https://ffmpeg.org/) (required for audio extraction)

## Installation

```bash
# Clone the repository
git clone <repository-url>
cd inf-3-analytics

# Install dependencies (uv or pip)
uv sync
# or
pip install -e ".[dev]"
```

## Quick Start

```bash
# Basic transcription
uv run inf3-transcribe --video inspection.mp4

# Specify output directory
uv run inf3-transcribe --video inspection.mp4 --out outputs/run1

# Specify language or model
uv run inf3-transcribe --video inspection.mp4 --language en --model medium
```

## Output

The CLI writes two files into the output directory:

```
outputs/
├── video_name.wav  # extracted audio (mono 16kHz)
└── video_name.txt  # transcript (one segment per line)
```

## Development

```bash
# Run tests
uv run pytest

# Lint
uv run ruff check src/
```

## License

MIT
