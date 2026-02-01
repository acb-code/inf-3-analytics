"""Tests for run management endpoints."""

from pathlib import Path

from fastapi.testclient import TestClient


def test_create_run_success(
    client: TestClient,
    tmp_data_root: Path,
    sample_video: Path,
) -> None:
    """Test creating a run successfully."""
    run_root = tmp_data_root / "outputs"

    response = client.post(
        "/runs",
        json={
            "video_path": str(sample_video),
            "run_root": str(run_root),
        },
    )

    assert response.status_code == 201
    data = response.json()
    assert data["video_path"] == str(sample_video)
    assert data["run_root"] == str(run_root)
    assert data["video_basename"] == sample_video.stem
    assert data["status"] == "created"
    assert "run_id" in data
    assert run_root.exists()


def test_create_run_with_custom_id(
    client: TestClient,
    tmp_data_root: Path,
    sample_video: Path,
) -> None:
    """Test creating a run with a custom run_id."""
    run_root = tmp_data_root / "outputs"

    response = client.post(
        "/runs",
        json={
            "video_path": str(sample_video),
            "run_root": str(run_root),
            "run_id": "my_custom_run_id",
        },
    )

    assert response.status_code == 201
    data = response.json()
    assert data["run_id"] == "my_custom_run_id"


def test_create_run_video_not_found(
    client: TestClient,
    tmp_data_root: Path,
) -> None:
    """Test creating a run with non-existent video."""
    response = client.post(
        "/runs",
        json={
            "video_path": str(tmp_data_root / "nonexistent.mp4"),
            "run_root": str(tmp_data_root / "outputs"),
        },
    )

    assert response.status_code == 400
    assert "not found" in response.json()["detail"].lower()


def test_create_run_path_outside_data_root(
    client: TestClient,
    sample_video: Path,
) -> None:
    """Test creating a run with path outside data root."""
    response = client.post(
        "/runs",
        json={
            "video_path": str(sample_video),
            "run_root": "/tmp/outside_data_root",
        },
    )

    assert response.status_code == 403
    assert "outside" in response.json()["detail"].lower()


def test_list_runs_empty(client: TestClient) -> None:
    """Test listing runs when none exist."""
    response = client.get("/runs")

    assert response.status_code == 200
    data = response.json()
    assert data["runs"] == []


def test_list_runs_with_data(
    client: TestClient,
    tmp_data_root: Path,
    sample_video: Path,
) -> None:
    """Test listing runs with data."""
    run_root = tmp_data_root / "outputs"

    # Create a run first
    client.post(
        "/runs",
        json={
            "video_path": str(sample_video),
            "run_root": str(run_root),
            "run_id": "test_list_run",
        },
    )

    response = client.get("/runs")

    assert response.status_code == 200
    data = response.json()
    assert len(data["runs"]) == 1
    assert data["runs"][0]["run_id"] == "test_list_run"


def test_get_run_success(
    client: TestClient,
    sample_run_with_artifacts: tuple[str, Path],
) -> None:
    """Test getting a run by ID."""
    run_id, _ = sample_run_with_artifacts

    response = client.get(f"/runs/{run_id}")

    assert response.status_code == 200
    data = response.json()
    assert data["run"]["run_id"] == run_id
    assert len(data["artifacts"]) == 4

    # Check all artifacts are available
    artifact_types = {a["type"] for a in data["artifacts"]}
    assert artifact_types == {
        "transcript",
        "events",
        "event_frames_manifest",
        "frame_analytics_manifest",
    }

    for artifact in data["artifacts"]:
        assert artifact["available"] is True
        assert artifact["url"] is not None


def test_get_run_not_found(client: TestClient) -> None:
    """Test getting a non-existent run."""
    response = client.get("/runs/nonexistent_run_id")

    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()
