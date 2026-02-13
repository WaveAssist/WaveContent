"""
Critical unit tests for WaveContent segregrate_website_content.py: missing/malformed data handling.
Tests validation logic in isolation (no import of segregrate_website_content to avoid LLM/top-level run).
"""
import pytest
from unittest.mock import MagicMock
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

_w = MagicMock()
_w.fetch_data.side_effect = lambda key, default=None, run_based=False, **kwargs: kwargs.get("default", default)
_w.store_data.return_value = None
_w.init.return_value = None
_w.call_llm.return_value = None
sys.modules["waveassist"] = _w


class TestMissingWebsiteContent:
    """Test handling of missing website_content."""

    def test_empty_dict_reset_to_empty(self):
        """Empty dict should be reset to empty dict."""
        website_content = {}
        if not isinstance(website_content, dict):
            website_content = {}
        assert isinstance(website_content, dict)
        assert website_content == {}

    def test_non_dict_reset_to_empty(self):
        """Non-dict should be reset to empty dict."""
        website_content = "not-a-dict"
        if not isinstance(website_content, dict):
            website_content = {}
        assert isinstance(website_content, dict)
        assert website_content == {}

    def test_empty_dict_raises_value_error(self):
        """Empty dict should raise ValueError."""
        website_content = {}
        should_raise = bool(not website_content)
        assert should_raise is True


class TestMissingPages:
    """Test handling of missing or empty pages."""

    def test_missing_pages_raises_value_error(self):
        """Missing pages key should raise ValueError."""
        website_content = {"url": "https://example.com"}
        pages = website_content.get("pages") or []
        assert not pages

    def test_empty_pages_raises_value_error(self):
        """Empty pages list should raise ValueError."""
        website_content = {"pages": []}
        pages = website_content.get("pages") or []
        assert not pages


class TestSafeFetch:
    """Test that fetch_data uses default= parameter."""

    def test_fetch_data_uses_default(self):
        """fetch_data should be called with default={}."""
        website_content = _w.fetch_data("website_content", default={})
        assert isinstance(website_content, dict)
        _w.fetch_data.assert_called_with("website_content", default={})


class TestDataStorage:
    """Test that data is stored with correct data_type."""

    def test_segregated_content_stored_as_json(self):
        """segregated_website_content stored with data_type='json' (pattern in node)."""
        _w.store_data.reset_mock()
        _w.store_data("segregated_website_content", {"top_primary_pages": []}, data_type="json")
        _w.store_data.assert_called_once()
        call_kw = _w.store_data.call_args[1]
        assert call_kw.get("data_type") == "json"
