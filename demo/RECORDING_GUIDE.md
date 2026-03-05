# Demo GIF Recording Guide

A step-by-step script for capturing a screen recording of the inf3-analytics frontend.

## Prerequisites

Start both servers before recording:

```bash
# Terminal 1 — API backend
export INF3_DATA_ROOT="$PWD/demo_data"
export INF3_REGISTRY_PATH="$PWD/demo_data/registry.json"
uv run --extra api uvicorn inf3_analytics.api.app:app --host 127.0.0.1 --port 8000

# Terminal 2 — Frontend dev server
cd frontend
npm run dev
```

Open `http://localhost:3000/runs` in a browser. Use the demo run:
`demo_data/outputs/run_20260205_092050_f7691363_inspection2/`

## Window Setup

- Browser window: **1280x720** (hide bookmarks bar, use full-screen or a clean profile)
- Hide any system notifications/overlays before recording
- Use a mouse cursor that is visible on screen

## Recommended Recording Tools

| Platform | Tool | Notes |
|----------|------|-------|
| macOS | [Kap](https://getkap.co/) | Free, exports GIF directly |
| Linux | [Peek](https://github.com/phw/peek) or OBS | Peek is simplest for GIF |
| Windows | [ShareX](https://getsharex.com/) | Free, excellent GIF support |

Record as **MP4** at your screen's native resolution, then use `gif-convert.sh` to produce the final GIF.

---

## Recording Script (~40 seconds)

### Scene 1: Run List + Run Detail (15s)

1. **Start** at `/runs` — pause 1s so the run grid is visible
2. **Hover** over the demo run card to show the hover state
3. **Click** the demo run card to navigate to `/runs/{run_id}`
4. **Wait** ~1s for the page to load — the video player appears on the left, events list on the right
5. **Click** the play button on the video to start playback — let it play ~3s
6. **Click** an event in the events list — the video seeks to that timestamp

### Scene 2: Frame Analytics Viewer (15s)

1. **Scroll** the events list to find an event that has a "View Frames" button (an event with detections)
2. **Click "View Frames"** — the `EventFrameViewer` modal opens full-screen
3. **Press the right arrow key** 2–3 times to advance through frames — bounding boxes should be visible on the images
4. **Click a detection checkbox** in the `DetectionToggleList` on the right to toggle a detection type off, then back on
5. **Glance** at the Q&A section and scene summary text in the side panel

### Scene 3: Site Analytics Viewer (10s)

1. **Close** the frame viewer modal (press Escape or click X)
2. **Click "View Site Analytics"** button on the run detail page
3. The `SiteAnalyticsViewer` modal opens
4. **Press the right arrow key** 2–3 times — equipment and personnel bounding boxes visible
5. **Show** the site summary stats panel (frame count, personnel count, equipment count)
6. **Close** the modal

---

## Tips for a Clean Recording

- Move the mouse **slowly and deliberately** — fast movements look jittery in GIFs
- Pause **1 second** after each navigation before the next action
- Keep the cursor **away from UI elements** you are not interacting with
- Disable browser extensions that add overlays or badges
- If using Chrome, open in an Incognito window for a clean look

---

## Converting to GIF

After recording, run the conversion script:

```bash
bash demo/gif-convert.sh path/to/recording.mp4
```

This produces `demo/demo.gif`. Check that it is under 10 MB — GitHub will not display GIFs larger than 10 MB inline.

If the file is too large:
- Lower the framerate: `FRAMERATE=8 bash demo/gif-convert.sh recording.mp4`
- Lower the width: `WIDTH=720 bash demo/gif-convert.sh recording.mp4`
- Trim the recording to remove dead time before converting
