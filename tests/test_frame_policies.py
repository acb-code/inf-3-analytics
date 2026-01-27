"""Tests for frame sampling policies."""

import pytest

from inf3_analytics.frame_extraction.policies import (
    FixedFPSWithinEventPolicy,
    NFramesPerEventPolicy,
)


class TestNFramesPerEventPolicy:
    """Tests for NFramesPerEventPolicy."""

    def test_name_property(self) -> None:
        """Test that name returns 'nframes'."""
        policy = NFramesPerEventPolicy(n=5)
        assert policy.name == "nframes"

    def test_params_property(self) -> None:
        """Test that params returns the configured n value."""
        policy = NFramesPerEventPolicy(n=10)
        assert policy.params == {"n": 10}

    def test_n_must_be_positive(self) -> None:
        """Test that n must be at least 1."""
        with pytest.raises(ValueError, match="n must be at least 1"):
            NFramesPerEventPolicy(n=0)

    def test_single_frame_returns_midpoint(self) -> None:
        """Test that n=1 returns the midpoint."""
        policy = NFramesPerEventPolicy(n=1)
        timestamps = policy.compute_timestamps(10.0, 20.0, 100.0)
        assert timestamps == (15.0,)

    def test_two_frames_returns_endpoints(self) -> None:
        """Test that n=2 returns start and end."""
        policy = NFramesPerEventPolicy(n=2)
        timestamps = policy.compute_timestamps(10.0, 20.0, 100.0)
        assert timestamps == (10.0, 20.0)

    def test_five_frames_evenly_spaced(self) -> None:
        """Test that n=5 returns evenly spaced frames including endpoints."""
        policy = NFramesPerEventPolicy(n=5)
        timestamps = policy.compute_timestamps(0.0, 4.0, 100.0)
        assert len(timestamps) == 5
        assert timestamps[0] == 0.0
        assert timestamps[-1] == 4.0
        # Should be at 0, 1, 2, 3, 4
        assert timestamps == (0.0, 1.0, 2.0, 3.0, 4.0)

    def test_clamps_to_video_bounds(self) -> None:
        """Test that timestamps are clamped to video duration."""
        policy = NFramesPerEventPolicy(n=3)
        timestamps = policy.compute_timestamps(-5.0, 50.0, 30.0)
        # Should clamp to [0, 30]
        assert timestamps[0] >= 0.0
        assert timestamps[-1] <= 30.0

    def test_short_event_returns_midpoint(self) -> None:
        """Test that very short events (<0.2s) return single midpoint."""
        policy = NFramesPerEventPolicy(n=5)
        timestamps = policy.compute_timestamps(10.0, 10.1, 100.0)
        assert len(timestamps) == 1
        assert timestamps[0] == 10.05

    def test_invalid_range_returns_empty(self) -> None:
        """Test that invalid range (start >= end) returns empty tuple."""
        policy = NFramesPerEventPolicy(n=5)
        timestamps = policy.compute_timestamps(20.0, 10.0, 100.0)
        assert timestamps == ()

    def test_same_start_end_returns_empty(self) -> None:
        """Test that start == end returns empty tuple."""
        policy = NFramesPerEventPolicy(n=5)
        timestamps = policy.compute_timestamps(10.0, 10.0, 100.0)
        assert timestamps == ()


class TestFixedFPSWithinEventPolicy:
    """Tests for FixedFPSWithinEventPolicy."""

    def test_name_property(self) -> None:
        """Test that name returns 'fps'."""
        policy = FixedFPSWithinEventPolicy(fps=2.0, max_frames=10)
        assert policy.name == "fps"

    def test_params_property(self) -> None:
        """Test that params returns configured values."""
        policy = FixedFPSWithinEventPolicy(fps=2.0, max_frames=10)
        assert policy.params == {"fps": 2.0, "max_frames": 10}

    def test_fps_must_be_positive(self) -> None:
        """Test that fps must be positive."""
        with pytest.raises(ValueError, match="fps must be positive"):
            FixedFPSWithinEventPolicy(fps=0)

    def test_max_frames_must_be_positive(self) -> None:
        """Test that max_frames must be at least 1."""
        with pytest.raises(ValueError, match="max_frames must be at least 1"):
            FixedFPSWithinEventPolicy(fps=1.0, max_frames=0)

    def test_one_fps_ten_second_event(self) -> None:
        """Test 1 FPS over 10 second event."""
        policy = FixedFPSWithinEventPolicy(fps=1.0, max_frames=30)
        timestamps = policy.compute_timestamps(0.0, 10.0, 100.0)
        # Should get frames at 0, 1, 2, ..., 10
        assert len(timestamps) == 11
        assert timestamps[0] == 0.0
        assert timestamps[-1] == 10.0

    def test_respects_max_frames(self) -> None:
        """Test that max_frames limit is respected."""
        policy = FixedFPSWithinEventPolicy(fps=10.0, max_frames=5)
        timestamps = policy.compute_timestamps(0.0, 10.0, 100.0)
        assert len(timestamps) == 5

    def test_half_fps(self) -> None:
        """Test 0.5 FPS (one frame every 2 seconds)."""
        policy = FixedFPSWithinEventPolicy(fps=0.5, max_frames=30)
        timestamps = policy.compute_timestamps(0.0, 10.0, 100.0)
        # Should get frames at 0, 2, 4, 6, 8, 10
        assert len(timestamps) == 6
        assert timestamps == (0.0, 2.0, 4.0, 6.0, 8.0, 10.0)

    def test_clamps_to_video_bounds(self) -> None:
        """Test that timestamps are clamped to video duration."""
        policy = FixedFPSWithinEventPolicy(fps=1.0, max_frames=30)
        timestamps = policy.compute_timestamps(-5.0, 50.0, 30.0)
        assert timestamps[0] >= 0.0
        assert timestamps[-1] <= 30.0

    def test_short_event_returns_midpoint(self) -> None:
        """Test that very short events (<0.2s) return single midpoint."""
        policy = FixedFPSWithinEventPolicy(fps=10.0, max_frames=30)
        timestamps = policy.compute_timestamps(10.0, 10.1, 100.0)
        assert len(timestamps) == 1
        assert timestamps[0] == 10.05

    def test_invalid_range_returns_empty(self) -> None:
        """Test that invalid range (start >= end) returns empty tuple."""
        policy = FixedFPSWithinEventPolicy(fps=1.0, max_frames=30)
        timestamps = policy.compute_timestamps(20.0, 10.0, 100.0)
        assert timestamps == ()
