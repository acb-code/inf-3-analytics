"""Structured progress output for CLI commands."""

import json
import sys

PROGRESS_PREFIX = "##PROGRESS##"
PROGRESS_SUFFIX = "##"


def emit_progress(
    current: int,
    total: int,
    unit: str,
    message: str | None = None,
) -> None:
    """Emit a structured progress line for parsing by pipeline executor.

    Progress is output in the format:
        ##PROGRESS##{"current":5,"total":10,"unit":"frames","message":"Processing"}##

    Args:
        current: Current progress count
        total: Total items to process
        unit: Unit label (e.g., "frames", "events")
        message: Optional progress message
    """
    data: dict[str, int | str] = {
        "current": current,
        "total": total,
        "unit": unit,
    }
    if message:
        data["message"] = message

    # Use compact JSON format, flush immediately for real-time updates
    line = f"{PROGRESS_PREFIX}{json.dumps(data, separators=(',', ':'))}{PROGRESS_SUFFIX}"
    print(line, file=sys.stdout, flush=True)
