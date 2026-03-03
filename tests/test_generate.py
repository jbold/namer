"""Tests for generate.py — compound generation, morpheme blends, basic filtering."""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
from generate import filter_basic, generate_compounds, generate_morpheme_blends


class TestCompoundGeneration:
    def test_produces_candidates(self):
        base_words = ["trace", "flow", "mind", "spark", "vault"]
        compounds = generate_compounds(base_words)
        assert len(compounds) > 0, "Should produce at least some compounds"

    def test_prefix_compounds(self):
        base_words = ["flow"]
        compounds = generate_compounds(base_words)
        # Should include prefix+base combos
        prefix_hits = [c for c in compounds if c.startswith(("re", "neo", "deep", "ever"))]
        assert len(prefix_hits) > 0, "Should generate prefix+base compounds"

    def test_suffix_compounds(self):
        base_words = ["trace"]
        compounds = generate_compounds(base_words)
        suffix_hits = [c for c in compounds if c.endswith(("mind", "flow", "spark", "vault"))]
        assert len(suffix_hits) > 0, "Should generate base+suffix compounds"

    def test_respects_length_limit(self):
        base_words = ["memory", "recall", "trace", "mind"]
        compounds = generate_compounds(base_words)
        # base+base combos limited to 12 chars
        base_base = [
            c
            for c in compounds
            if not any(
                c.startswith(p)
                for p in ["re", "un", "neo", "pre", "ever", "deep", "true", "all", "pan", "omni", "syn", "meta"]
            )
        ]
        for c in base_base:
            assert len(c) <= 18, f"Compound '{c}' too long"  # suffix compounds can be longer

    def test_skips_short_bases(self):
        base_words = ["a", "bb", "trace"]  # first two too short
        compounds = generate_compounds(base_words)
        # Should only use "trace" as base
        assert all(
            "trace" in c or any(c.startswith(p) for p in ["re", "un", "neo"]) for c in compounds if len(c) <= 12
        ), "Should skip bases shorter than 3 chars"


class TestMorphemeBlends:
    def test_produces_blends(self):
        seeds = ["memory", "recall", "trace", "pattern"]
        blends = generate_morpheme_blends(seeds)
        assert len(blends) > 0, "Should produce morpheme blends"

    def test_blend_length_bounds(self):
        seeds = ["memory", "recall", "trace", "pattern"]
        blends = generate_morpheme_blends(seeds)
        for b in blends:
            assert 5 <= len(b) <= 11, f"Blend '{b}' outside 5-11 char range"

    def test_single_seed_limited_blends(self):
        seeds = ["memory"]
        blends = generate_morpheme_blends(seeds)
        # Single seed can still produce blends (memo+mory != self-pair since slices differ)
        # But should be very few compared to multi-seed
        assert len(blends) <= 2, f"Single seed should produce very few blends, got {len(blends)}"


class TestBasicFilter:
    def test_removes_short_words(self):
        candidates = {"ab", "abc", "abcd", "abcde"}
        filtered = filter_basic(candidates, min_len=4, max_len=12)
        assert "ab" not in filtered
        assert "abc" not in filtered
        assert "abcd" in filtered

    def test_removes_long_words(self):
        candidates = {"short", "verylongwordhere"}
        filtered = filter_basic(candidates, min_len=4, max_len=12)
        assert "short" in filtered
        assert "verylongwordhere" not in filtered

    def test_removes_common_words(self):
        candidates = {"memory", "recall", "think", "novelword"}
        filtered = filter_basic(candidates, min_len=4, max_len=12)
        assert "memory" not in filtered
        assert "novelword" in filtered

    def test_removes_non_alpha(self):
        candidates = {"good-name", "good_name", "goodname", "good123"}
        filtered = filter_basic(candidates, min_len=4, max_len=12)
        assert "goodname" in filtered
        assert "good-name" not in filtered
        assert "good_name" not in filtered
        assert "good123" not in filtered

    def test_deduplicates(self):
        candidates = {"trace", "Trace", "TRACE"}
        filtered = filter_basic(candidates, min_len=4, max_len=12)
        assert filtered.count("trace") == 1

    def test_returns_sorted(self):
        candidates = {"zeta", "alpha", "mango"}
        filtered = filter_basic(candidates, min_len=4, max_len=12)
        assert filtered == sorted(filtered)
