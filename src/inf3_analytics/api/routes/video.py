"""Video streaming endpoint with Range support."""

import mimetypes
import re
from collections.abc import Iterator
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import StreamingResponse

from inf3_analytics.api.config import Settings, get_settings
from inf3_analytics.api.dependencies import get_run_or_404, validate_path_security
from inf3_analytics.api.models import RunMetadata

router = APIRouter(prefix="/runs/{run_id}", tags=["video"])

CHUNK_SIZE = 1024 * 1024  # 1MB chunks


def _parse_range_header(range_header: str, file_size: int) -> tuple[int, int]:
    """Parse HTTP Range header.

    Args:
        range_header: Range header value (e.g., "bytes=0-1023")
        file_size: Total file size

    Returns:
        Tuple of (start, end) byte positions

    Raises:
        HTTPException: 416 if range is invalid
    """
    match = re.match(r"bytes=(\d*)-(\d*)", range_header)
    if not match:
        raise HTTPException(
            status_code=status.HTTP_416_RANGE_NOT_SATISFIABLE,
            detail="Invalid range format",
        )

    start_str, end_str = match.groups()

    if start_str == "" and end_str == "":
        raise HTTPException(
            status_code=status.HTTP_416_RANGE_NOT_SATISFIABLE,
            detail="Invalid range: both start and end are empty",
        )

    if start_str == "":
        # Suffix range: -500 means last 500 bytes
        suffix_length = int(end_str)
        start = max(0, file_size - suffix_length)
        end = file_size - 1
    elif end_str == "":
        # Open-ended range: 500- means from byte 500 to end
        start = int(start_str)
        end = file_size - 1
    else:
        start = int(start_str)
        end = int(end_str)

    if start > end or start >= file_size:
        raise HTTPException(
            status_code=status.HTTP_416_RANGE_NOT_SATISFIABLE,
            detail=f"Invalid range: {start}-{end} for file of size {file_size}",
        )

    # Clamp end to file size
    end = min(end, file_size - 1)

    return start, end


def _file_iterator(path: Path, start: int, end: int) -> Iterator[bytes]:
    """Generate file chunks for streaming.

    Args:
        path: Path to file
        start: Start byte position
        end: End byte position (inclusive)

    Yields:
        File chunks
    """
    with open(path, "rb") as f:
        f.seek(start)
        remaining = end - start + 1
        while remaining > 0:
            chunk_size = min(CHUNK_SIZE, remaining)
            data = f.read(chunk_size)
            if not data:
                break
            remaining -= len(data)
            yield data


@router.get("/video")
def stream_video(
    request: Request,
    run: Annotated[RunMetadata, Depends(get_run_or_404)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> StreamingResponse:
    """Stream the video file with HTTP Range support."""
    video_path = Path(run.video_path)
    validate_path_security(video_path, settings)

    if not video_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Video file not found",
        )

    file_size = video_path.stat().st_size
    content_type = mimetypes.guess_type(str(video_path))[0] or "application/octet-stream"

    range_header = request.headers.get("range")

    if range_header:
        start, end = _parse_range_header(range_header, file_size)
        content_length = end - start + 1

        return StreamingResponse(
            _file_iterator(video_path, start, end),
            status_code=status.HTTP_206_PARTIAL_CONTENT,
            media_type=content_type,
            headers={
                "Content-Range": f"bytes {start}-{end}/{file_size}",
                "Accept-Ranges": "bytes",
                "Content-Length": str(content_length),
            },
        )
    else:
        return StreamingResponse(
            _file_iterator(video_path, 0, file_size - 1),
            status_code=status.HTTP_200_OK,
            media_type=content_type,
            headers={
                "Accept-Ranges": "bytes",
                "Content-Length": str(file_size),
            },
        )
