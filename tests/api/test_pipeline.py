"""Tests for pipeline execution endpoints."""

import io
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from inf3_analytics.api.models import PipelineStep, StepStatus


@pytest.fixture
def uploaded_run(client: TestClient, tmp_data_root: Path):
    """Create a run via upload for pipeline tests."""
    video_content = b"\x00\x00\x00\x1cftypisom" + b"\x00" * 100
    files = {"file": ("pipeline_video.mp4", io.BytesIO(video_content), "video/mp4")}

    response = client.post("/upload", files=files)
    assert response.status_code == 201
    return response.json()


def test_get_pipeline_status(client: TestClient, uploaded_run: dict) -> None:
    """Test getting pipeline status for a run."""
    run_id = uploaded_run["run_id"]

    response = client.get(f"/runs/{run_id}/pipeline/status")

    assert response.status_code == 200
    data = response.json()
    assert data["run_id"] == run_id
    assert "steps" in data
    assert len(data["steps"]) == 4
    assert "progress_percent" in data
    assert data["progress_percent"] == 0  # All pending


def test_get_pipeline_status_not_found(client: TestClient) -> None:
    """Test getting pipeline status for non-existent run."""
    response = client.get("/runs/nonexistent/pipeline/status")

    assert response.status_code == 404


def test_start_pipeline(client: TestClient, uploaded_run: dict) -> None:
    """Test starting the pipeline."""
    run_id = uploaded_run["run_id"]

    # Mock the background task to avoid running actual pipeline
    with patch("inf3_analytics.api.routes.pipeline.execute_pipeline"):
        response = client.post(f"/runs/{run_id}/pipeline/start")

    assert response.status_code == 202
    data = response.json()
    assert data["message"] == "Pipeline started"
    assert data["run_id"] == run_id
    assert "status_url" in data


def test_start_pipeline_with_config(client: TestClient, uploaded_run: dict) -> None:
    """Test starting the pipeline with custom configuration."""
    run_id = uploaded_run["run_id"]

    config = {
        "transcription_engine": "gemini",
        "event_engine": "gemini",
        "frame_analytics_engine": "openai",
    }

    with patch("inf3_analytics.api.routes.pipeline.execute_pipeline"):
        response = client.post(f"/runs/{run_id}/pipeline/start", json=config)

    assert response.status_code == 202


def test_run_single_step(client: TestClient, uploaded_run: dict) -> None:
    """Test running a single pipeline step."""
    run_id = uploaded_run["run_id"]

    with patch("inf3_analytics.api.routes.pipeline.execute_single_step"):
        response = client.post(f"/runs/{run_id}/pipeline/step/transcribe")

    assert response.status_code == 202
    data = response.json()
    assert data["step"] == "transcribe"


def test_run_single_step_invalid_step(client: TestClient, uploaded_run: dict) -> None:
    """Test running an invalid step name."""
    run_id = uploaded_run["run_id"]

    response = client.post(f"/runs/{run_id}/pipeline/step/invalid_step")

    assert response.status_code == 400
    assert "Invalid step" in response.json()["detail"]


def test_run_step_requires_prerequisites(
    client: TestClient, uploaded_run: dict, test_registry
) -> None:
    """Test that steps require prerequisites to be completed."""
    run_id = uploaded_run["run_id"]

    # Try to run extract_events without transcription
    response = client.post(f"/runs/{run_id}/pipeline/step/extract_events")

    assert response.status_code == 400
    assert "requires" in response.json()["detail"]


def test_run_step_after_prerequisite_completed(
    client: TestClient, uploaded_run: dict, test_registry
) -> None:
    """Test running a step after prerequisite is completed."""
    run_id = uploaded_run["run_id"]

    # Mark transcription as completed
    test_registry.update_step_status(
        run_id, PipelineStep.TRANSCRIBE, StepStatus.COMPLETED
    )

    # Now extract_events should be allowed
    with patch("inf3_analytics.api.routes.pipeline.execute_single_step"):
        response = client.post(f"/runs/{run_id}/pipeline/step/extract_events")

    assert response.status_code == 202


def test_pipeline_progress_calculation(
    client: TestClient, uploaded_run: dict, test_registry
) -> None:
    """Test that progress is calculated correctly."""
    run_id = uploaded_run["run_id"]

    # Initially 0%
    response = client.get(f"/runs/{run_id}/pipeline/status")
    assert response.json()["progress_percent"] == 0

    # After 1 step completed (1/4 = 25%)
    test_registry.update_step_status(
        run_id, PipelineStep.TRANSCRIBE, StepStatus.COMPLETED
    )
    response = client.get(f"/runs/{run_id}/pipeline/status")
    assert response.json()["progress_percent"] == 25

    # After 2 steps completed (2/4 = 50%)
    test_registry.update_step_status(
        run_id, PipelineStep.EXTRACT_EVENTS, StepStatus.COMPLETED
    )
    response = client.get(f"/runs/{run_id}/pipeline/status")
    assert response.json()["progress_percent"] == 50


def test_pipeline_status_shows_running_step(
    client: TestClient, uploaded_run: dict, test_registry
) -> None:
    """Test that running step status is reflected correctly."""
    run_id = uploaded_run["run_id"]

    # Mark transcription as running
    test_registry.update_step_status(
        run_id, PipelineStep.TRANSCRIBE, StepStatus.RUNNING
    )

    response = client.get(f"/runs/{run_id}/pipeline/status")
    data = response.json()

    transcribe_step = next(s for s in data["steps"] if s["step"] == "transcribe")
    assert transcribe_step["status"] == "running"
    assert transcribe_step["started_at"] is not None
    # Progress should be ~12% (0.5/4 * 100)
    assert data["progress_percent"] == 12


def test_pipeline_status_shows_error(
    client: TestClient, uploaded_run: dict, test_registry
) -> None:
    """Test that failed step shows error message."""
    run_id = uploaded_run["run_id"]

    error_msg = "Transcription engine not available"
    test_registry.update_step_status(
        run_id, PipelineStep.TRANSCRIBE, StepStatus.FAILED, error_msg
    )

    response = client.get(f"/runs/{run_id}/pipeline/status")
    data = response.json()

    transcribe_step = next(s for s in data["steps"] if s["step"] == "transcribe")
    assert transcribe_step["status"] == "failed"
    assert transcribe_step["error_message"] == error_msg


def test_legacy_run_gets_steps_initialized(
    client: TestClient, sample_run_with_artifacts, test_registry
) -> None:
    """Test that a run without steps gets them initialized on status request."""
    run_id, _ = sample_run_with_artifacts

    # The sample_run_with_artifacts fixture creates a run without pipeline steps
    # Getting status should initialize them
    response = client.get(f"/runs/{run_id}/pipeline/status")

    assert response.status_code == 200
    data = response.json()
    assert len(data["steps"]) == 4
