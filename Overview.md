# inf3-analytics Overview

## What it is

**inf3-analytics** is a video analytics pipeline for **infrastructure inspections** (think: bridges, tunnels, pipes). You feed it an inspection video and it produces structured, actionable findings — what defects were found, where, how severe, with visual evidence.

## What it does (the pipeline)

The system processes a video through a series of steps, each building on the last:

1. **Transcription** — Extracts speech from the video (inspector narration) into timestamped text. Supports local (Faster-Whisper) or cloud (OpenAI, Gemini) engines.

2. **Event Extraction** — Identifies meaningful moments from the transcript: observations, structural anomalies, safety risks, measurements, etc. Uses both rule-based keyword matching and LLM-powered extraction.

3. **Frame Extraction** — Pulls video frames aligned to each detected event, so you get visual evidence for every finding.

4. **Frame Analytics** — Sends those frames to vision-language models (Gemini, GPT) to detect defects: cracks, corrosion, spalling, leaks, vegetation encroachment, etc. Each detection gets a confidence score, severity rating, and optional bounding box.

## Key design principles

- **Timestamp as spine** — Everything (words, events, frames, detections) is anchored to precise video timestamps. This lets you click an event and jump to exactly that moment in the video.
- **Engine-agnostic** — Each step supports multiple backends (local, OpenAI, Gemini), so you're not locked to one provider.
- **Full traceability** — Every output records which model, prompt version, and config produced it. Important for auditing and reproducibility.

## What's built

- 5 CLI tools to run each pipeline step
- A **FastAPI backend** with async job queue, video streaming, and SSE progress updates
- A **Next.js frontend** for browsing runs, viewing events on a timeline, and watching video alongside findings
- ~9k lines of Python, 20+ test files, strict typing

## What's planned but not built yet

- Multimodal detection (combining audio + visual signals)
- 3D reconstruction from video
- Comparing detected conditions against design models

## Who it's for

Field inspection teams and asset managers who review hours of infrastructure video. Instead of manually scrubbing through footage, they get a structured report with timestamped findings, severity ratings, and frame evidence — all cross-referenced between what the inspector *said* and what the camera *saw*.
