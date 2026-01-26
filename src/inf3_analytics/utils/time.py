"""Time formatting utilities for timestamp handling."""

import re


class TimestampFormatError(ValueError):
    """Raised when a timestamp string has an invalid format."""

    pass


def seconds_to_timestamp(seconds: float) -> str:
    """Convert seconds to SRT-style timestamp format.

    Args:
        seconds: Time in seconds (can include milliseconds as decimal)

    Returns:
        Timestamp string in "hh:mm:ss,mmm" format

    Examples:
        >>> seconds_to_timestamp(0)
        '00:00:00,000'
        >>> seconds_to_timestamp(61.5)
        '00:01:01,500'
        >>> seconds_to_timestamp(3661.123)
        '01:01:01,123'
    """
    if seconds < 0:
        raise ValueError("Seconds cannot be negative")

    total_ms = int(round(seconds * 1000))
    ms = total_ms % 1000
    total_seconds = total_ms // 1000
    s = total_seconds % 60
    total_minutes = total_seconds // 60
    m = total_minutes % 60
    h = total_minutes // 60

    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def timestamp_to_seconds(timestamp: str) -> float:
    """Parse SRT-style timestamp to seconds.

    Args:
        timestamp: Timestamp string in "hh:mm:ss,mmm" format

    Returns:
        Time in seconds as float

    Raises:
        TimestampFormatError: If timestamp format is invalid

    Examples:
        >>> timestamp_to_seconds('00:00:00,000')
        0.0
        >>> timestamp_to_seconds('00:01:01,500')
        61.5
        >>> timestamp_to_seconds('01:01:01,123')
        3661.123
    """
    pattern = r"^(\d{2}):(\d{2}):(\d{2}),(\d{3})$"
    match = re.match(pattern, timestamp)

    if not match:
        raise TimestampFormatError(
            f"Invalid timestamp format: '{timestamp}'. Expected 'hh:mm:ss,mmm'"
        )

    hours, minutes, seconds, milliseconds = map(int, match.groups())

    if minutes >= 60:
        raise TimestampFormatError(f"Invalid minutes value: {minutes}")
    if seconds >= 60:
        raise TimestampFormatError(f"Invalid seconds value: {seconds}")

    total_seconds = hours * 3600 + minutes * 60 + seconds + milliseconds / 1000
    return total_seconds


def format_duration(seconds: float) -> str:
    """Format duration in human-readable format.

    Args:
        seconds: Duration in seconds

    Returns:
        Human-readable duration string

    Examples:
        >>> format_duration(45)
        '45s'
        >>> format_duration(125)
        '2m 5s'
        >>> format_duration(3725)
        '1h 2m 5s'
    """
    if seconds < 0:
        raise ValueError("Duration cannot be negative")

    total_seconds = int(seconds)
    s = total_seconds % 60
    total_minutes = total_seconds // 60
    m = total_minutes % 60
    h = total_minutes // 60

    parts = []
    if h > 0:
        parts.append(f"{h}h")
    if m > 0 or h > 0:
        parts.append(f"{m}m")
    parts.append(f"{s}s")

    return " ".join(parts)
