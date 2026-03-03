"""Tests for filter.py — verdict logic and thresholds."""

import os
import sys
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
from filter import check_candidate


class TestVerdictLogic:
    """Test verdict classification without hitting real APIs."""

    @patch("filter.check_registry")
    @patch("filter.check_github_count")
    def test_clean_verdict(self, mock_gh, mock_reg):
        """No registry hits + low GitHub = CLEAN."""
        mock_reg.return_value = False  # not taken
        mock_gh.return_value = 2
        result = check_candidate("xyloquent", delay=0)
        assert result["verdict"] == "CLEAN"
        assert result["npm"] is False
        assert result["pypi"] is False
        assert result["crates"] is False

    @patch("filter.check_registry")
    @patch("filter.check_github_count")
    def test_likely_ok_verdict(self, mock_gh, mock_reg):
        """No registry hits + moderate GitHub = LIKELY_OK."""
        mock_reg.return_value = False
        mock_gh.return_value = 12
        result = check_candidate("xyloquent", delay=0)
        assert result["verdict"] == "LIKELY_OK"

    @patch("filter.check_registry")
    @patch("filter.check_github_count")
    def test_check_verdict(self, mock_gh, mock_reg):
        """One registry hit + moderate GitHub = CHECK."""
        # npm taken, pypi/crates not
        mock_reg.side_effect = [True, False, False]
        mock_gh.return_value = 30
        result = check_candidate("xyloquent", delay=0)
        assert result["verdict"] == "CHECK"

    @patch("filter.check_registry")
    @patch("filter.check_github_count")
    def test_taken_verdict_multiple_registries(self, mock_gh, mock_reg):
        """Multiple registry hits = TAKEN."""
        mock_reg.return_value = True  # all taken
        mock_gh.return_value = 100
        result = check_candidate("react", delay=0)
        assert result["verdict"] == "TAKEN"

    @patch("filter.check_registry")
    @patch("filter.check_github_count")
    def test_taken_verdict_high_github(self, mock_gh, mock_reg):
        """No registries but very high GitHub = TAKEN (2+ registries needed)."""
        mock_reg.return_value = False
        mock_gh.return_value = 200
        result = check_candidate("popular", delay=0)
        # 0 registry hits, gh=200 → CHECK (not TAKEN, needs registry hits too)
        # Actually looking at the logic: registry_hits=0, gh=200 → falls through to TAKEN
        # because none of the earlier conditions match (gh >= 50)
        assert result["verdict"] == "TAKEN"

    @patch("filter.check_registry")
    @patch("filter.check_github_count")
    def test_handles_none_github(self, mock_gh, mock_reg):
        """GitHub API failure (None) treated as 0."""
        mock_reg.return_value = False
        mock_gh.return_value = None
        result = check_candidate("xyloquent", delay=0)
        assert result["verdict"] == "CLEAN"
        assert result["github"] is None
