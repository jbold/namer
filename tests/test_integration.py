"""Integration tests — hit real APIs with small inputs.

Run with: pytest tests/test_integration.py -m integration
Skip with: pytest -m 'not integration'
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
from generate import filter_basic, generate_compounds, generate_morpheme_blends, generate_semantic


@pytest.mark.integration
class TestDatamuseIntegration:
    """Hit real Datamuse API with minimal seeds."""

    def test_semantic_returns_results(self):
        """Datamuse should return results for common words."""
        results = generate_semantic(["light"])
        assert len(results) > 10, f"Expected >10 results, got {len(results)}"

    def test_full_pipeline_small(self):
        """Run generate → filter_basic with 3 seeds."""
        seeds = ["spark", "drift", "pulse"]
        semantic = generate_semantic(seeds)
        compounds = generate_compounds(list(semantic) + seeds)
        blends = generate_morpheme_blends(seeds + list(semantic)[:20])

        all_candidates = semantic | compounds | blends | set(seeds)
        filtered = filter_basic(all_candidates, min_len=4, max_len=12)

        assert len(filtered) > 50, f"Expected >50 filtered candidates, got {len(filtered)}"
        # All should be lowercase alpha, 4-12 chars
        for c in filtered:
            assert c.isalpha(), f"'{c}' is not alpha"
            assert 4 <= len(c) <= 12, f"'{c}' outside length bounds"


@pytest.mark.integration
class TestRegistryIntegration:
    """Hit real package registries with known names."""

    def test_npm_detects_react(self):
        from filter import check_registry

        result = check_registry("react", "https://registry.npmjs.org/{name}")
        assert result is True, "react should be taken on npm"

    def test_npm_clear_for_nonsense(self):
        from filter import check_registry

        result = check_registry("xzqwvbnt", "https://registry.npmjs.org/{name}")
        assert result is False, "Nonsense name should be clear on npm"
