"""Tests for websearch_gate.py — product signal detection and provider discovery."""

import os
import sys
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
from websearch_gate import check_product_presence, discover_provider


class TestProductSignalDetection:
    """Test product presence detection with mocked search results."""

    @patch("websearch_gate.do_search")
    def test_clear_no_product_signals(self, mock_search):
        """No product signals in results = CLEAR."""
        mock_search.return_value = [
            {
                "title": "Xyloquent - a rare English word",
                "url": "https://dictionary.com/xyloquent",
                "description": "Meaning: speaking of wood",
            },
            {
                "title": "Xyloquent on Reddit",
                "url": "https://reddit.com/r/words/xyloquent",
                "description": "TIL about this word",
            },
        ]
        result = check_product_presence("brave", {"BRAVE_API_KEY": "test"}, "xyloquent")
        assert result["verdict"] == "CLEAR"
        assert result["has_product"] is False

    @patch("websearch_gate.do_search")
    def test_bumped_strong_product_signals(self, mock_search):
        """Multiple product signals = BUMPED."""
        mock_search.return_value = [
            {
                "title": "Acme App - Project Management Platform",
                "url": "https://acme.io",
                "description": "Sign up for free trial. Enterprise pricing available.",
            },
            {
                "title": "Acme API Documentation",
                "url": "https://docs.acme.io/api",
                "description": "SDK and API reference for developers",
            },
        ]
        result = check_product_presence("brave", {"BRAVE_API_KEY": "test"}, "acme")
        assert result["verdict"] == "BUMPED"
        assert result["has_product"] is True
        assert len(set(result["signals"])) >= 2

    @patch("websearch_gate.do_search")
    def test_caution_weak_signal(self, mock_search):
        """Single product signal = CAUTION."""
        mock_search.return_value = [
            {
                "title": "Zephyr - Wikipedia",
                "url": "https://en.wikipedia.org/wiki/Zephyr",
                "description": "Greek god of the west wind",
            },
            {
                "title": "Zephyr Linux Foundation",
                "url": "https://zephyrproject.org",
                "description": "Open source RTOS platform",
            },
        ]
        result = check_product_presence("brave", {"BRAVE_API_KEY": "test"}, "zephyr")
        # "platform" is one signal
        assert result["verdict"] in ("CAUTION", "BUMPED")

    @patch("websearch_gate.do_search")
    def test_empty_results(self, mock_search):
        """No search results = CLEAR."""
        mock_search.return_value = []
        result = check_product_presence("brave", {"BRAVE_API_KEY": "test"}, "zzzznotreal")
        assert result["verdict"] == "CLEAR"

    @patch("websearch_gate.do_search")
    def test_top_results_truncated(self, mock_search):
        """Top results are truncated to 80 chars."""
        mock_search.return_value = [
            {"title": "A" * 200, "url": "https://example.com/" + "x" * 200, "description": "test"},
        ]
        result = check_product_presence("brave", {"BRAVE_API_KEY": "test"}, "test")
        assert len(result["top_results"][0]["title"]) <= 80
        assert len(result["top_results"][0]["url"]) <= 80


class TestProviderDiscovery:
    """Test auto-discovery of search providers from environment."""

    def test_discovers_brave(self):
        with patch.dict(os.environ, {"BRAVE_API_KEY": "test-key"}, clear=False):
            provider, env_vals = discover_provider()
            assert provider == "brave"
            assert env_vals["BRAVE_API_KEY"] == "test-key"

    def test_discovers_serper(self):
        env = {"SERPER_API_KEY": "test-key"}
        with patch.dict(os.environ, env, clear=True):
            provider, env_vals = discover_provider()
            assert provider == "serper"

    def test_discovers_google_needs_both_vars(self):
        # Only one of two required vars
        with patch.dict(os.environ, {"GOOGLE_API_KEY": "key"}, clear=True), raises_system_exit():
            discover_provider()

        # Both vars present
        env = {"GOOGLE_API_KEY": "key", "GOOGLE_CSE_ID": "cse"}
        with patch.dict(os.environ, env, clear=True):
            provider, env_vals = discover_provider()
            assert provider == "google"

    def test_discovers_searxng(self):
        env = {"SEARXNG_URL": "http://localhost:8080"}
        with patch.dict(os.environ, env, clear=True):
            provider, env_vals = discover_provider()
            assert provider == "searxng"
            assert env_vals["SEARXNG_URL"] == "http://localhost:8080"

    def test_priority_order_brave_first(self):
        env = {"BRAVE_API_KEY": "brave-key", "SERPER_API_KEY": "serper-key"}
        with patch.dict(os.environ, env, clear=True):
            provider, _ = discover_provider()
            assert provider == "brave", "Brave should take priority over Serper"

    def test_exits_when_no_provider(self):
        with patch.dict(os.environ, {}, clear=True), raises_system_exit():
            discover_provider()


class _SystemExitCatcher:
    """Context manager to catch SystemExit."""

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is SystemExit:
            self.code = exc_val.code
            return True
        return False


def raises_system_exit():
    return _SystemExitCatcher()
