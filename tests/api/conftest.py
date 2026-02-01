"""Shared fixtures for API tests."""

import json
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from inf3_analytics.api.app import create_app
from inf3_analytics.api.config import Settings
from inf3_analytics.api.dependencies import get_registry
from inf3_analytics.api.registry import RunRegistry


@pytest.fixture
def tmp_data_root(tmp_path: Path) -> Path:
    """Create a temporary data root directory."""
    return tmp_path


@pytest.fixture
def test_settings(tmp_data_root: Path) -> Settings:
    """Create test settings with temporary paths."""
    return Settings(
        inf3_data_root=tmp_data_root,
        inf3_registry_path=tmp_data_root / ".inf3-analytics" / "registry.json",
        inf3_cors_origins=["http://localhost:3000"],
    )


@pytest.fixture
def test_registry(test_settings: Settings) -> RunRegistry:
    """Create a test registry with temporary path."""
    return RunRegistry(test_settings.inf3_registry_path)


@pytest.fixture
def client(test_settings: Settings, test_registry: RunRegistry) -> Iterator[TestClient]:
    """Create a test client with dependency overrides."""
    app = create_app()

    def override_settings() -> Settings:
        return test_settings

    def override_registry() -> RunRegistry:
        return test_registry

    from inf3_analytics.api.config import get_settings

    app.dependency_overrides[get_settings] = override_settings
    app.dependency_overrides[get_registry] = override_registry

    with TestClient(app) as c:
        yield c


@pytest.fixture
def sample_video(tmp_data_root: Path) -> Path:
    """Create a minimal sample video file."""
    video_path = tmp_data_root / "test_video.mp4"
    # Create a minimal MP4-like file (just needs to exist for tests)
    video_path.write_bytes(b"\x00\x00\x00\x1cftypisom" + b"\x00" * 100)
    return video_path


@pytest.fixture
def sample_run_with_artifacts(
    tmp_data_root: Path,
    sample_video: Path,
    test_registry: RunRegistry,
) -> tuple[str, Path]:
    """Create a sample run with all artifact files."""
    run_root = tmp_data_root / "outputs"
    run_root.mkdir(parents=True, exist_ok=True)

    # Create run in registry
    run = test_registry.create_run(
        video_path=str(sample_video),
        run_root=str(run_root),
        run_id="test_run_001",
    )

    basename = sample_video.stem

    # Create transcript file
    transcript_data = {
        "full_text": "Test transcript",
        "segments": [
            {
                "id": 0,
                "start_s": 0.0,
                "end_s": 5.0,
                "start_ts": "00:00:00.000",
                "end_ts": "00:00:05.000",
                "text": "Test transcript",
                "words": None,
                "avg_logprob": -0.5,
                "no_speech_prob": 0.1,
            }
        ],
        "metadata": {
            "engine": "faster-whisper",
            "model_name": "base",
            "language": "en",
            "detected_language": "en",
            "language_probability": 0.99,
            "duration_s": 5.0,
            "source_video": str(sample_video),
            "source_audio": None,
        },
    }
    transcript_path = run_root / f"{basename}.json"
    transcript_path.write_text(json.dumps(transcript_data))

    # Create events file
    events_dir = run_root / "events"
    events_dir.mkdir(parents=True, exist_ok=True)
    events_data = {
        "events": [
            {
                "event_id": "evt_001",
                "event_type": "observation",
                "severity": "low",
                "confidence": 0.9,
                "start_s": 0.0,
                "end_s": 5.0,
                "start_ts": "00:00:00.000",
                "end_ts": "00:00:05.000",
                "title": "Test event",
                "summary": "A test event",
                "transcript_ref": {
                    "segment_ids": [0],
                    "excerpt": "Test transcript",
                    "keywords": ["test"],
                },
                "suggested_actions": None,
                "metadata": {
                    "extractor_engine": "rule-based",
                    "extractor_version": "0.1.0",
                    "created_at": "2024-01-01T00:00:00Z",
                    "source_transcript_path": str(transcript_path),
                },
                "related_rule_events": None,
            }
        ],
        "source_transcript_path": str(transcript_path),
        "extraction_engine": "rule-based",
        "extraction_timestamp": "2024-01-01T00:00:00Z",
    }
    events_path = events_dir / f"{basename}_events.json"
    events_path.write_text(json.dumps(events_data))

    # Create event frames manifest
    frames_dir = run_root / "event_frames"
    frames_dir.mkdir(parents=True, exist_ok=True)
    frames_manifest = {
        "event_frame_sets": [],
        "metadata": {
            "policy_name": "n_frames",
            "policy_params": {"n_frames": 5},
            "video_path": str(sample_video),
            "video_duration_s": 60.0,
            "video_fps": 30.0,
            "video_width": 1920,
            "video_height": 1080,
            "events_path": str(events_path),
            "extraction_timestamp": "2024-01-01T00:00:00Z",
            "jpeg_quality": 85,
        },
        "total_frames": 0,
        "total_events": 0,
        "successful_events": 0,
        "skipped_events": 0,
        "failed_events": 0,
    }
    frames_manifest_path = frames_dir / "manifest.json"
    frames_manifest_path.write_text(json.dumps(frames_manifest))

    # Create frame analytics manifest
    analytics_dir = run_root / "frame_analytics"
    analytics_dir.mkdir(parents=True, exist_ok=True)
    analytics_manifest = {
        "run_id": run.run_id,
        "engine": {
            "name": "vlm",
            "provider": "gemini",
            "model": "gemini-3-flash-preview",
            "prompt_version": "v1",
            "version": "0.1.0",
            "config": {},
        },
        "source_event_frames_manifest": str(frames_manifest_path),
        "events_file": str(events_path),
        "total_events": 0,
        "total_frames": 0,
        "analyzed_frames": 0,
        "failed_frames": 0,
        "event_summaries": [],
        "created_at": "2024-01-01T00:00:00Z",
    }
    analytics_manifest_path = analytics_dir / "manifest_analytics.json"
    analytics_manifest_path.write_text(json.dumps(analytics_manifest))

    return run.run_id, run_root
