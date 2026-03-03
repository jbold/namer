"""Tests for progress.py — shared progress tracking and ETA formatting."""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
from progress import InterruptHandler, ProgressTracker, format_eta


class TestFormatEta:
    def test_seconds(self):
        assert format_eta(45) == "45s"

    def test_minutes(self):
        assert format_eta(125) == "2m 5s"

    def test_hours(self):
        assert format_eta(3725) == "1h 2m"

    def test_zero(self):
        assert format_eta(0) == "0s"


class TestInterruptHandler:
    def test_initial_state(self):
        handler = InterruptHandler()
        assert handler.interrupted is False


class TestProgressTracker:
    def test_tick_increments(self):
        tracker = ProgressTracker(total=10)
        assert tracker.done == 0
        tracker.tick("test")
        assert tracker.done == 1

    def test_should_stop_on_errors(self):
        tracker = ProgressTracker(total=10, max_errors=3)
        assert not tracker.should_stop()
        tracker.record_error("err1")
        tracker.record_error("err2")
        assert not tracker.should_stop()
        tracker.record_error("err3")
        assert tracker.should_stop()
        assert tracker.hit_error_limit

    def test_already_done(self):
        tracker = ProgressTracker(total=100, already_done=50)
        assert tracker.done == 50
        tracker.tick("item")
        assert tracker.done == 51

    def test_record_error_returns_false_at_limit(self):
        tracker = ProgressTracker(total=10, max_errors=1)
        result = tracker.record_error("fatal")
        assert result is False
        assert tracker.hit_error_limit
