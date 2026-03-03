"""Tests for io.py — shared I/O helpers."""

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
from fileio import apply_pre_filter, load_candidates


class TestLoadCandidates:
    def test_loads_simple_file(self, tmp_path):
        f = tmp_path / "names.txt"
        f.write_text("alpha\nbeta\ngamma\n")
        result = load_candidates(str(f))
        assert result == ["alpha", "beta", "gamma"]

    def test_loads_tsv_first_column(self, tmp_path):
        f = tmp_path / "names.tsv"
        f.write_text("alpha\t0.95\nbeta\t0.88\n")
        result = load_candidates(str(f))
        assert result == ["alpha", "beta"]

    def test_skips_blank_lines(self, tmp_path):
        f = tmp_path / "names.txt"
        f.write_text("alpha\n\nbeta\n  \ngamma\n")
        result = load_candidates(str(f))
        assert result == ["alpha", "beta", "gamma"]

    def test_exits_on_missing_file(self):
        with pytest.raises(SystemExit):
            load_candidates("/nonexistent/file.txt")

    def test_exits_on_empty_file(self, tmp_path):
        f = tmp_path / "empty.txt"
        f.write_text("")
        with pytest.raises(SystemExit):
            load_candidates(str(f))


class TestApplyPreFilter:
    def test_filters_by_substring(self):
        candidates = ["sparkflow", "deepmind", "neotrace", "random"]
        result = apply_pre_filter(candidates, "spark,neo")
        assert result == ["sparkflow", "neotrace"]

    def test_none_returns_all(self):
        candidates = ["alpha", "beta"]
        result = apply_pre_filter(candidates, None)
        assert result == ["alpha", "beta"]

    def test_case_insensitive(self):
        candidates = ["SparkFlow", "DeepMind"]
        result = apply_pre_filter(candidates, "spark")
        assert result == ["SparkFlow"]
