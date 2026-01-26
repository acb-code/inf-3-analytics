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

# Use OpenAI Whisper API (model can be set in .env)
export OPENAI_API_KEY=your-key
echo "OPENAI_MODEL=whisper-1" >> .env
uv run --extra openai inf3-transcribe --video inspection.mp4 --engine openai

# Use Gemini (model can be set in .env)
export GEMINI_API_KEY=your-key
echo "GEMINI_MODEL=gemini-1.5-flash" >> .env
uv run --extra gemini inf3-transcribe --video inspection.mp4 --engine gemini
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
