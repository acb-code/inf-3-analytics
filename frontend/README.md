# Inf3 Analytics Frontend

Minimal Next.js frontend for viewing infrastructure inspection video runs with synchronized event navigation.

## Quick Start

### Prerequisites

- Node.js 18+
- Python 3.11+ with `uv` package manager
- Processed video runs in the backend `outputs/` directory

### Step 1: Start the Backend API

From the project root directory:

```bash
# Navigate to project root
cd /path/to/inf-3-analytics

# Ensure you have processed at least one video run
# (The outputs/ directory should contain run folders)

# Start the API server
uv run python -m inf3_analytics.api
```

The backend runs on http://localhost:8000. You should see:

```
INFO:     Uvicorn running on http://0.0.0.0:8000
```

Verify it's working:

```bash
curl http://localhost:8000/runs
```

### Step 2: Start the Frontend

In a separate terminal:

```bash
cd frontend

# First time only: install dependencies
npm install

# Copy environment config (first time only)
cp .env.local.example .env.local

# Start development server
npm run dev
```

The frontend runs on http://localhost:3000.

### Step 3: Test the Application

1. **Open the runs list**: http://localhost:3000/runs
   - You should see a grid of run cards
   - Each card shows: run ID (truncated), status badge, filename, date, duration
   - If no runs appear, ensure the backend has processed videos in `outputs/`

2. **Click a run** to open the detail view
   - Left side (2/3 width): Video player with native controls
   - Right side (1/3 width): Scrollable event list

3. **Test event navigation**:
   - Click any event card - video seeks to that timestamp and plays
   - Events show: time range, type badge, severity badge, title, summary, transcript excerpt

4. **Test active event highlighting**:
   - Play the video normally
   - Watch the event list - the current event highlights with a blue border
   - The list auto-scrolls to keep the active event visible

## Configuration

Edit `.env.local` to change the backend API URL:

```
NEXT_PUBLIC_INF3_API_BASE=http://localhost:8000
```

## Troubleshooting

| Issue | Solution |
|-------|----------|
| "Error loading runs" | Check backend is running on port 8000 |
| Empty runs list | Process a video with the backend pipeline first |
| Video won't play | Check browser console; ensure video file exists |
| Events not loading | Verify the run has events artifact (`/artifacts/events`) |
| CORS errors | Backend should allow localhost:3000 origin |

## Features

- **Runs list**: View all inspection runs with status and metadata
- **Run detail**: Video player with synchronized event list
- **Event navigation**: Click events to seek video to that timestamp
- **Active highlighting**: Current event highlights as video plays
- **Responsive layout**: Stacked on mobile, side-by-side on desktop

## Project Structure

```
src/
├── app/                  # Next.js App Router pages
│   ├── layout.tsx        # Root layout
│   ├── page.tsx          # Redirects to /runs
│   └── runs/
│       ├── page.tsx      # Runs list
│       └── [run_id]/
│           └── page.tsx  # Run detail view
├── components/           # React components
│   ├── EventCard.tsx     # Single event display
│   ├── EventList.tsx     # Scrollable event list
│   ├── LoadingSpinner.tsx
│   ├── RunCard.tsx       # Run card for list view
│   └── VideoPlayer.tsx   # HTML5 video wrapper
├── lib/                  # Utilities
│   ├── api.ts            # API client
│   └── format.ts         # Time/severity formatters
└── types/
    └── api.ts            # TypeScript types
```

## Backend API Endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /runs` | List all runs |
| `GET /runs/{run_id}` | Run details |
| `GET /runs/{run_id}/video` | Video stream (supports HTTP Range) |
| `GET /runs/{run_id}/artifacts/events` | Event list JSON |
