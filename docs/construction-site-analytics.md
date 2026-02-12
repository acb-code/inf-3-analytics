# Construction Site Analytics

Automated counting and classification of construction equipment, personnel, and hardhats from video or extracted frames.

## Overview

The `inf3-site-analytics` CLI analyzes construction site video to produce:

- **Per-frame counts** of equipment, people, and hardhats (with colors)
- **Time series** tracking how counts change over the video
- **Summary statistics** (peak counts, averages)
- **Markdown report** for quick review

## Architecture

Three engine modes are available:

| Engine | Flag | Requires | Speed | Accuracy |
|--------|------|----------|-------|----------|
| **YOLO-World** (default) | `--engine yolo` | GPU recommended (`uv sync --extra yolo`) | Fast (~10-30 fps) | Good for counting, weak on hardhat colors |
| **Gemini VLM** | `--engine gemini` | `GEMINI_API_KEY` (`uv sync --extra gemini`) | Slow (~0.5-2 fps) | High semantic accuracy |
| **OpenAI VLM** | `--engine openai` | `OPENAI_API_KEY` (`uv sync --extra openai`) | Slow (~0.5-2 fps) | High semantic accuracy |

### When to use each engine

- **YOLO-World**: Large videos, real-time needs, budget-conscious. Best when you have a GPU.
- **Gemini VLM**: No GPU available, need accurate equipment classification, small frame counts.
- **OpenAI VLM**: Same as Gemini, if you prefer OpenAI or need a second opinion.

### Hybrid mode

Use YOLO-World for fast detection with VLM verification for uncertain results:

```bash
inf3-site-analytics --video site.mp4 --engine yolo --verify-colors
```

This runs YOLO-World locally, then sends hardhat crops to Gemini Flash for color verification.

## Installation

```bash
# Core (always needed)
uv sync

# YOLO-World engine (GPU recommended)
uv sync --extra yolo

# Gemini VLM engine
uv sync --extra gemini

# OpenAI VLM engine
uv sync --extra openai

# All cloud providers
uv sync --extra cloud
```

## CLI Usage

```
inf3-site-analytics [OPTIONS]
```

### Input (required, mutually exclusive)

| Flag | Description |
|------|-------------|
| `--video PATH` | Video file to analyze (frames extracted at `--fps` rate) |
| `--frames-dir PATH` | Directory of pre-extracted JPEG frames |

### Engine selection

| Flag | Description |
|------|-------------|
| `--engine {yolo,gemini,openai}` | Detection engine (default: `yolo`) |
| `--device {cpu,cuda}` | Device for YOLO-World (default: auto-detect) |
| `--model NAME` | Override model name |
| `--confidence FLOAT` | Min detection confidence for YOLO (default: 0.15) |
| `--sleep-ms INT` | Rate limiting between VLM API calls in ms (default: 200) |

### Output & limits

| Flag | Description |
|------|-------------|
| `--out PATH` | Output directory (default: `./outputs/site_analytics`) |
| `--fps FLOAT` | Frame extraction rate from video (default: 0.5) |
| `--max-frames INT` | Max frames to process |
| `--parallel-workers INT` | Parallel workers (default: 1) |
| `--dry-run` | Show plan without running inference |

### YOLO-specific options

| Flag | Description |
|------|-------------|
| `--verify-colors` | Use Gemini Flash to verify hardhat colors |
| `--verify-with-vlm` | Use VLM to verify low-confidence detections |
| `--equipment-classes NAME...` | Custom equipment class names |

### Examples

```bash
# Basic YOLO-World analysis (default)
inf3-site-analytics --video site_video.mp4

# Gemini VLM (no GPU needed)
inf3-site-analytics --video site_video.mp4 --engine gemini --sleep-ms 500

# OpenAI VLM with cost preview
inf3-site-analytics --video site_video.mp4 --engine openai --dry-run

# Pre-extracted frames with YOLO
inf3-site-analytics --frames-dir outputs/frames --engine yolo --device cuda

# Limit to first 50 frames
inf3-site-analytics --video site_video.mp4 --max-frames 50 --engine gemini
```

## Output Formats

All outputs are written to the `--out` directory:

### `site_counts.json`

Time series with per-frame counts and summary statistics:

```json
{
  "engine": { "name": "yolo_world", "model": "yolov8x-worldv2", ... },
  "frames": [
    {
      "frame_idx": 0,
      "timestamp_s": 0.0,
      "timestamp_ts": "00:00:00,000",
      "equipment_counts": { "excavator": 1, "crane": 1 },
      "person_count": 3,
      "hardhat_counts": { "yellow": 2, "white": 1 }
    }
  ],
  "summary": {
    "peak_equipment": { "excavator": 2, "crane": 1 },
    "peak_persons": 5,
    "peak_hardhats": { "yellow": 3, "white": 2 },
    "avg_persons": 3.2,
    "total_frames": 60
  }
}
```

### `frame_detections.ndjson`

One JSON object per line, one line per frame. Contains full detection details including bounding boxes and attributes.

### `site_report.md`

Human-readable markdown report with tables for personnel, equipment, and hardhat summaries.

## Cost Comparison

Approximate costs per 100 frames:

| Engine | Cost | Notes |
|--------|------|-------|
| YOLO-World | $0.00 | Local inference, requires GPU for speed |
| Gemini Flash | ~$0.008 | ~$0.000083/frame |
| OpenAI GPT-5-mini | ~$0.030 | ~$0.0003/frame |
| YOLO + color verify | ~$0.003 | Only ~30% of frames need VLM |

Use `--dry-run` to see cost estimates before running.
