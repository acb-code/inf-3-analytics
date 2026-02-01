"""Tests for video streaming endpoint."""

from pathlib import Path

from fastapi.testclient import TestClient


def test_stream_video_full_request(
    client: TestClient,
    sample_run_with_artifacts: tuple[str, Path],
) -> None:
    """Test streaming full video without Range header."""
    run_id, _ = sample_run_with_artifacts

    response = client.get(f"/runs/{run_id}/video")

    assert response.status_code == 200
    assert "Accept-Ranges" in response.headers
    assert response.headers["Accept-Ranges"] == "bytes"
    assert "Content-Length" in response.headers


def test_stream_video_partial_request(
    client: TestClient,
    sample_run_with_artifacts: tuple[str, Path],
) -> None:
    """Test streaming video with Range header (206 Partial Content)."""
    run_id, _ = sample_run_with_artifacts

    response = client.get(
        f"/runs/{run_id}/video",
        headers={"Range": "bytes=0-10"},
    )

    assert response.status_code == 206
    assert "Content-Range" in response.headers
    assert response.headers["Content-Range"].startswith("bytes 0-10/")
    assert response.headers["Content-Length"] == "11"


def test_stream_video_open_ended_range(
    client: TestClient,
    sample_run_with_artifacts: tuple[str, Path],
) -> None:
    """Test streaming video with open-ended Range header."""
    run_id, _ = sample_run_with_artifacts

    response = client.get(
        f"/runs/{run_id}/video",
        headers={"Range": "bytes=50-"},
    )

    assert response.status_code == 206
    assert "Content-Range" in response.headers


def test_stream_video_suffix_range(
    client: TestClient,
    sample_run_with_artifacts: tuple[str, Path],
) -> None:
    """Test streaming video with suffix Range header (last N bytes)."""
    run_id, _ = sample_run_with_artifacts

    response = client.get(
        f"/runs/{run_id}/video",
        headers={"Range": "bytes=-20"},
    )

    assert response.status_code == 206
    assert "Content-Range" in response.headers


def test_stream_video_invalid_range(
    client: TestClient,
    sample_run_with_artifacts: tuple[str, Path],
) -> None:
    """Test streaming video with invalid Range header."""
    run_id, _ = sample_run_with_artifacts

    response = client.get(
        f"/runs/{run_id}/video",
        headers={"Range": "bytes=1000000-2000000"},  # Beyond file size
    )

    assert response.status_code == 416  # Range Not Satisfiable


def test_stream_video_run_not_found(client: TestClient) -> None:
    """Test streaming video for non-existent run."""
    response = client.get("/runs/nonexistent/video")

    assert response.status_code == 404


def test_stream_video_file_not_found(
    client: TestClient,
    tmp_data_root: Path,
) -> None:
    """Test streaming video when file has been deleted."""
    run_root = tmp_data_root / "outputs"
    run_root.mkdir(parents=True, exist_ok=True)

    # Create a video file then delete it
    temp_video = tmp_data_root / "temp_video.mp4"
    temp_video.write_bytes(b"\x00" * 100)

    # Create run
    response = client.post(
        "/runs",
        json={
            "video_path": str(temp_video),
            "run_root": str(run_root),
            "run_id": "deleted_video_run",
        },
    )
    assert response.status_code == 201

    # Delete the video
    temp_video.unlink()

    # Try to stream
    response = client.get("/runs/deleted_video_run/video")

    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()
