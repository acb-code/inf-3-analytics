"""Tests for video upload endpoint."""

import io
from pathlib import Path

import pytest
from fastapi.testclient import TestClient


def test_upload_valid_video(client: TestClient, tmp_data_root: Path) -> None:
    """Test uploading a valid video file."""
    # Create a minimal fake video file
    video_content = b"\x00\x00\x00\x1cftypisom" + b"\x00" * 100
    files = {"file": ("test_video.mp4", io.BytesIO(video_content), "video/mp4")}

    response = client.post("/upload", files=files)

    assert response.status_code == 201
    data = response.json()
    assert "run_id" in data
    assert data["run_id"].startswith("run_")
    assert "video_path" in data
    assert "run_root" in data
    assert "message" in data

    # Verify file was saved
    video_path = Path(data["video_path"])
    assert video_path.exists()
    assert video_path.read_bytes() == video_content


def test_upload_invalid_extension(client: TestClient) -> None:
    """Test rejecting invalid file extensions."""
    files = {"file": ("test.txt", io.BytesIO(b"not a video"), "text/plain")}

    response = client.post("/upload", files=files)

    assert response.status_code == 400
    assert "Invalid file type" in response.json()["detail"]


def test_upload_no_filename(client: TestClient) -> None:
    """Test rejecting upload without filename."""
    files = {"file": ("", io.BytesIO(b"content"), "video/mp4")}

    response = client.post("/upload", files=files)

    # FastAPI returns 422 for validation errors or 400 for our custom validation
    assert response.status_code in (400, 422)


def test_upload_creates_run_in_registry(
    client: TestClient, test_registry, tmp_data_root: Path
) -> None:
    """Test that upload creates a run in the registry."""
    video_content = b"\x00\x00\x00\x1cftypisom" + b"\x00" * 100
    files = {"file": ("my_video.mp4", io.BytesIO(video_content), "video/mp4")}

    response = client.post("/upload", files=files)

    assert response.status_code == 201
    run_id = response.json()["run_id"]

    # Verify run exists in registry
    run = test_registry.get_run(run_id)
    assert run is not None
    assert run.run_id == run_id


def test_upload_initializes_pipeline_steps(
    client: TestClient, test_registry, tmp_data_root: Path
) -> None:
    """Test that upload initializes pipeline steps."""
    video_content = b"\x00\x00\x00\x1cftypisom" + b"\x00" * 100
    files = {"file": ("pipeline_test.mp4", io.BytesIO(video_content), "video/mp4")}

    response = client.post("/upload", files=files)

    assert response.status_code == 201
    run_id = response.json()["run_id"]

    # Verify pipeline steps are initialized
    steps = test_registry.get_pipeline_steps(run_id)
    assert len(steps) == 5  # 5 pipeline steps

    # All should be pending
    for step in steps:
        assert step.status.value == "pending"


def test_upload_unique_filenames(client: TestClient, tmp_data_root: Path) -> None:
    """Test that multiple uploads get unique filenames."""
    video_content = b"\x00\x00\x00\x1cftypisom" + b"\x00" * 100

    # Upload same file twice
    files1 = {"file": ("same_name.mp4", io.BytesIO(video_content), "video/mp4")}
    files2 = {"file": ("same_name.mp4", io.BytesIO(video_content), "video/mp4")}

    response1 = client.post("/upload", files=files1)
    response2 = client.post("/upload", files=files2)

    assert response1.status_code == 201
    assert response2.status_code == 201

    # Should have different run IDs and paths
    data1 = response1.json()
    data2 = response2.json()
    assert data1["run_id"] != data2["run_id"]
    assert data1["video_path"] != data2["video_path"]


def test_upload_allowed_extensions(client: TestClient, tmp_data_root: Path) -> None:
    """Test that various video extensions are accepted."""
    video_content = b"\x00\x00\x00\x1cftypisom" + b"\x00" * 100

    for ext in [".mp4", ".mov", ".avi", ".mkv", ".webm"]:
        files = {"file": (f"video{ext}", io.BytesIO(video_content), "video/mp4")}
        response = client.post("/upload", files=files)
        assert response.status_code == 201, f"Extension {ext} should be allowed"
