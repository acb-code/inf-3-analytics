"""Tests for artifact retrieval endpoints."""

from pathlib import Path

from fastapi.testclient import TestClient


def test_get_transcript_success(
    client: TestClient,
    sample_run_with_artifacts: tuple[str, Path],
) -> None:
    """Test getting transcript artifact."""
    run_id, _ = sample_run_with_artifacts

    response = client.get(f"/runs/{run_id}/artifacts/transcript")

    assert response.status_code == 200
    data = response.json()
    assert data["full_text"] == "Test transcript"
    assert len(data["segments"]) == 1
    assert data["metadata"]["engine"] == "faster-whisper"


def test_get_events_success(
    client: TestClient,
    sample_run_with_artifacts: tuple[str, Path],
) -> None:
    """Test getting events artifact."""
    run_id, _ = sample_run_with_artifacts

    response = client.get(f"/runs/{run_id}/artifacts/events")

    assert response.status_code == 200
    data = response.json()
    assert len(data["events"]) == 1
    assert data["events"][0]["event_id"] == "evt_001"
    assert data["extraction_engine"] == "rule-based"


def test_get_event_frames_manifest_success(
    client: TestClient,
    sample_run_with_artifacts: tuple[str, Path],
) -> None:
    """Test getting event frames manifest."""
    run_id, _ = sample_run_with_artifacts

    response = client.get(f"/runs/{run_id}/artifacts/event-frames/manifest")

    assert response.status_code == 200
    data = response.json()
    assert "metadata" in data
    assert data["metadata"]["policy_name"] == "n_frames"


def test_get_frame_analytics_manifest_success(
    client: TestClient,
    sample_run_with_artifacts: tuple[str, Path],
) -> None:
    """Test getting frame analytics manifest."""
    run_id, _ = sample_run_with_artifacts

    response = client.get(f"/runs/{run_id}/artifacts/frame-analytics/manifest")

    assert response.status_code == 200
    data = response.json()
    assert data["run_id"] == run_id
    assert data["engine"]["name"] == "vlm"
    assert data["engine"]["provider"] == "gemini"


def test_get_transcript_not_found(
    client: TestClient,
    tmp_data_root: Path,
    sample_video: Path,
) -> None:
    """Test getting transcript when it doesn't exist."""
    # Create a run without artifacts
    run_root = tmp_data_root / "empty_outputs"
    run_root.mkdir(parents=True, exist_ok=True)

    create_response = client.post(
        "/runs",
        json={
            "video_path": str(sample_video),
            "run_root": str(run_root),
            "run_id": "empty_run",
        },
    )
    assert create_response.status_code == 201

    response = client.get("/runs/empty_run/artifacts/transcript")

    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_get_artifact_run_not_found(client: TestClient) -> None:
    """Test getting artifact for non-existent run."""
    response = client.get("/runs/nonexistent/artifacts/transcript")

    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()
