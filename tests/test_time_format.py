"""Tests for time formatting utilities."""

import pytest

from inf3_analytics.utils.time import (
    TimestampFormatError,
    format_duration,
    seconds_to_timestamp,
    timestamp_to_seconds,
)


class TestSecondsToTimestamp:
    """Tests for seconds_to_timestamp function."""

    def test_zero(self) -> None:
        """Test conversion of zero seconds."""
        assert seconds_to_timestamp(0) == "00:00:00,000"

    def test_milliseconds_only(self) -> None:
        """Test conversion with only milliseconds."""
        assert seconds_to_timestamp(0.123) == "00:00:00,123"
        assert seconds_to_timestamp(0.5) == "00:00:00,500"
        assert seconds_to_timestamp(0.001) == "00:00:00,001"

    def test_seconds_only(self) -> None:
        """Test conversion with full seconds."""
        assert seconds_to_timestamp(1) == "00:00:01,000"
        assert seconds_to_timestamp(30) == "00:00:30,000"
        assert seconds_to_timestamp(59) == "00:00:59,000"

    def test_seconds_with_milliseconds(self) -> None:
        """Test conversion with seconds and milliseconds."""
        assert seconds_to_timestamp(1.5) == "00:00:01,500"
        assert seconds_to_timestamp(30.123) == "00:00:30,123"

    def test_minutes(self) -> None:
        """Test conversion with minutes."""
        assert seconds_to_timestamp(60) == "00:01:00,000"
        assert seconds_to_timestamp(90) == "00:01:30,000"
        assert seconds_to_timestamp(125.5) == "00:02:05,500"

    def test_hours(self) -> None:
        """Test conversion with hours."""
        assert seconds_to_timestamp(3600) == "01:00:00,000"
        assert seconds_to_timestamp(3661.123) == "01:01:01,123"
        assert seconds_to_timestamp(36000) == "10:00:00,000"

    def test_large_hours(self) -> None:
        """Test conversion with large hour values."""
        assert seconds_to_timestamp(360000) == "100:00:00,000"

    def test_negative_raises(self) -> None:
        """Test that negative values raise ValueError."""
        with pytest.raises(ValueError, match="cannot be negative"):
            seconds_to_timestamp(-1)

    def test_rounding(self) -> None:
        """Test millisecond rounding behavior."""
        # Should round to nearest millisecond
        assert seconds_to_timestamp(0.9999) == "00:00:01,000"
        assert seconds_to_timestamp(0.9994) == "00:00:00,999"


class TestTimestampToSeconds:
    """Tests for timestamp_to_seconds function."""

    def test_zero(self) -> None:
        """Test parsing of zero timestamp."""
        assert timestamp_to_seconds("00:00:00,000") == 0.0

    def test_milliseconds_only(self) -> None:
        """Test parsing with only milliseconds."""
        assert timestamp_to_seconds("00:00:00,123") == 0.123
        assert timestamp_to_seconds("00:00:00,500") == 0.5

    def test_seconds(self) -> None:
        """Test parsing with seconds."""
        assert timestamp_to_seconds("00:00:01,000") == 1.0
        assert timestamp_to_seconds("00:00:30,500") == 30.5

    def test_minutes(self) -> None:
        """Test parsing with minutes."""
        assert timestamp_to_seconds("00:01:00,000") == 60.0
        assert timestamp_to_seconds("00:02:05,500") == 125.5

    def test_hours(self) -> None:
        """Test parsing with hours."""
        assert timestamp_to_seconds("01:00:00,000") == 3600.0
        assert timestamp_to_seconds("01:01:01,123") == 3661.123

    def test_invalid_format_raises(self) -> None:
        """Test that invalid formats raise TimestampFormatError."""
        with pytest.raises(TimestampFormatError):
            timestamp_to_seconds("00:00:00")  # Missing milliseconds

        with pytest.raises(TimestampFormatError):
            timestamp_to_seconds("00:00:00.000")  # Wrong separator

        with pytest.raises(TimestampFormatError):
            timestamp_to_seconds("0:0:0,000")  # Missing leading zeros

        with pytest.raises(TimestampFormatError):
            timestamp_to_seconds("invalid")

    def test_invalid_minutes_raises(self) -> None:
        """Test that invalid minute values raise TimestampFormatError."""
        with pytest.raises(TimestampFormatError, match="minutes"):
            timestamp_to_seconds("00:60:00,000")

    def test_invalid_seconds_raises(self) -> None:
        """Test that invalid second values raise TimestampFormatError."""
        with pytest.raises(TimestampFormatError, match="seconds"):
            timestamp_to_seconds("00:00:60,000")


class TestRoundtrip:
    """Tests for roundtrip conversion."""

    @pytest.mark.parametrize(
        "seconds",
        [0, 0.001, 0.123, 1, 1.5, 60, 90.5, 3600, 3661.123, 36000],
    )
    def test_roundtrip(self, seconds: float) -> None:
        """Test that converting to timestamp and back preserves value."""
        timestamp = seconds_to_timestamp(seconds)
        result = timestamp_to_seconds(timestamp)
        assert abs(result - seconds) < 0.001  # Within 1ms


class TestFormatDuration:
    """Tests for format_duration function."""

    def test_seconds_only(self) -> None:
        """Test formatting with only seconds."""
        assert format_duration(0) == "0s"
        assert format_duration(30) == "30s"
        assert format_duration(59) == "59s"

    def test_minutes(self) -> None:
        """Test formatting with minutes."""
        assert format_duration(60) == "1m 0s"
        assert format_duration(90) == "1m 30s"
        assert format_duration(125) == "2m 5s"

    def test_hours(self) -> None:
        """Test formatting with hours."""
        assert format_duration(3600) == "1h 0m 0s"
        assert format_duration(3725) == "1h 2m 5s"
        assert format_duration(7200) == "2h 0m 0s"

    def test_truncates_milliseconds(self) -> None:
        """Test that milliseconds are truncated."""
        assert format_duration(30.999) == "30s"

    def test_negative_raises(self) -> None:
        """Test that negative duration raises ValueError."""
        with pytest.raises(ValueError, match="cannot be negative"):
            format_duration(-1)
