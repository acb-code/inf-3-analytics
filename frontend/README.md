# Inf3 Analytics Frontend

Minimal Next.js frontend for viewing infrastructure inspection video runs with synchronized event navigation.

## Quick Start

### Prerequisites

- Node.js 18+
- Python 3.11+ with `uv` package manager
- A processed video run (see Data Setup below)

---

## Data Setup

The frontend displays data from the backend API, which serves processed video runs. Before using the frontend, you need:

1. **Source video** in `data/`
2. **Processed artifacts** in `outputs/`
3. **Registered run** in the API registry

### Directory Structure

```
inf-3-analytics/
├── data/
│   └── inspection.MOV              # Source video file
├── outputs/                         # Processing outputs (run_root)
│   ├── inspection.json              # Transcript (Step 1)
│   ├── inspection.txt
│   ├── inspection.srt
│   ├── inspection.wav
│   ├── events/
│   │   ├── inspection_events.json   # Events (Step 2)
│   │   └── inspection_events.md
│   ├── event_frames/
│   │   ├── manifest.json            # Frame manifest (Step 3)
│   │   └── evt_*/                   # Frame directories
│   │       ├── frames.json
│   │       └── frames/*.jpg
│   └── frame_analytics/
│       ├── manifest_analytics.json  # Analytics manifest (Step 4)
│       └── */event_summary.json
└── .inf3-analytics/
    └── registry.json                # Run registry (created by API)
```

### Processing Pipeline

Run these commands from the project root to process a video:

```bash
# Step 1: Transcribe video
uv run inf3-transcribe --video data/inspection.MOV --out outputs/

# Step 2: Extract events from transcript
uv run inf3-extract-events --transcript outputs/inspection.json

# Step 3: Extract frames for each event
uv run inf3-extract-event-frames \
  --video data/inspection.MOV \
  --events outputs/events/inspection_events.json

# Step 4: Analyze frames with VLM (optional)
uv run inf3-frame-analytics --event-frames outputs/event_frames
```

### Register Run with API

After processing, register the run so the API can serve it:

```bash
# Start the API first
uv run python -m inf3_analytics.api &

# Register the run
curl -X POST http://localhost:8000/runs \
  -H "Content-Type: application/json" \
  -d '{
    "video_path": "data/inspection.MOV",
    "run_root": "outputs"
  }'
```

This creates `.inf3-analytics/registry.json` with the run metadata.

### Verify Setup

Check what the API sees:

```bash
# List runs
curl http://localhost:8000/runs

# Get run details (use run_id from above)
curl http://localhost:8000/runs/{run_id}
```

A properly configured run shows artifacts with `"available": true`:

```json
{
  "run": { "run_id": "run_20260129_...", ... },
  "artifacts": [
    { "type": "transcript", "available": true, "url": "/runs/.../artifacts/transcript" },
    { "type": "events", "available": true, "url": "/runs/.../artifacts/events" },
    ...
  ]
}
```

### Minimum Required Artifacts

For the frontend to work, you need at minimum:

| Artifact | File | Required For |
|----------|------|--------------|
| Video | `data/*.MOV` | Video playback |
| Events | `outputs/events/*_events.json` | Event list display |

Optional but recommended:
- Transcript (`outputs/*.json`) - for transcript excerpts in events
- Event frames (`outputs/event_frames/manifest.json`) - for frame thumbnails
- Frame analytics (`outputs/frame_analytics/manifest_analytics.json`) - for detection overlays

---

## Running the Application

### Step 1: Start the Backend API

```bash
cd /path/to/inf-3-analytics

# Start API server
uv run python -m inf3_analytics.api
```

You should see:
```
INFO:     Uvicorn running on http://0.0.0.0:8000
```

### Step 2: Start the Frontend

In a separate terminal:

```bash
cd frontend

# First time only
npm install
cp .env.local.example .env.local

# Start dev server
npm run dev
```

Frontend runs on http://localhost:3000.

### Step 3: Test the Application

1. **Open the runs list**: http://localhost:3000/runs
   - You should see run cards with: run ID, status badge, filename, date
   - If empty, ensure you've registered runs via `POST /runs`

2. **Click a run** to open the detail view
   - Left (2/3): Video player with native controls
   - Right (1/3): Scrollable event list

3. **Test event navigation**:
   - Click any event card → video seeks to that timestamp and plays
   - Events show: time range, type badge, severity badge, title, summary

4. **Test active highlighting**:
   - Play video normally
   - Current event highlights with blue border
   - List auto-scrolls to keep active event visible

---

## Configuration

Edit `.env.local`:

```bash
NEXT_PUBLIC_INF3_API_BASE=http://localhost:8000
```

---

## Troubleshooting

| Issue | Cause | Solution |
|-------|-------|----------|
| "Error loading runs" | Backend not running | Start API with `uv run python -m inf3_analytics.api` |
| Empty runs list | No runs registered | Register with `curl -X POST .../runs` |
| Run shows but no events | Events not processed | Run `inf3-extract-events` |
| Video won't play | Video path invalid | Check `video_path` in registration matches actual file |
| CORS errors | Origin not allowed | Backend allows localhost:3000 by default |

### Common Setup Issues

**"Video file not found" on registration:**
```bash
# Use paths relative to where you start the API
curl -X POST http://localhost:8000/runs \
  -d '{"video_path": "data/inspection.MOV", "run_root": "outputs"}'
```

**Artifacts show `"available": false`:**
- Check file naming matches video basename
- Transcript: `outputs/{basename}.json` (not `{basename}_transcript.json`)
- Events: `outputs/events/{basename}_events.json`

**No registry.json:**
- Created automatically on first `POST /runs`
- Located at `.inf3-analytics/registry.json`

---

## Project Structure

```
src/
├── app/
│   ├── layout.tsx
│   ├── page.tsx              # Redirects to /runs
│   └── runs/
│       ├── page.tsx          # Runs list
│       └── [run_id]/
│           └── page.tsx      # Run detail view
├── components/
│   ├── EventCard.tsx
│   ├── EventList.tsx
│   ├── LoadingSpinner.tsx
│   ├── RunCard.tsx
│   └── VideoPlayer.tsx
├── lib/
│   ├── api.ts
│   └── format.ts
└── types/
    └── api.ts
```

---

## Backend API Reference

| Endpoint | Description |
|----------|-------------|
| `POST /runs` | Register a run (video_path, run_root) |
| `GET /runs` | List all registered runs |
| `GET /runs/{run_id}` | Run details + artifact availability |
| `GET /runs/{run_id}/video` | Stream video (HTTP Range support) |
| `GET /runs/{run_id}/artifacts/transcript` | Transcript JSON |
| `GET /runs/{run_id}/artifacts/events` | Events JSON |
| `GET /runs/{run_id}/artifacts/event-frames/manifest` | Frame manifest |
| `GET /runs/{run_id}/artifacts/frame-analytics/manifest` | Analytics manifest |
