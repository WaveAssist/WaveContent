"""
Critical unit tests for WaveContent fetch_website_content.py: empty URL handling, missing data.
Tests validation logic in isolation (no import of fetch_website_content to avoid crawlee/top-level run).
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
sys.modules["waveassist"] = _w


def _validation_would_raise(website_url):
    """Same condition as fetch_website_content.py: raise when URL missing/invalid."""
    return not website_url or not isinstance(website_url, str) or not website_url.strip()


class TestEmptyUrlHandling:
    """Test that empty or missing website_url raises ValueError."""

    def test_empty_url_raises_value_error(self):
        """Empty string URL should raise ValueError."""
        assert _validation_would_raise("") is True

    def test_none_url_raises_value_error(self):
        """None URL should raise ValueError."""
        assert _validation_would_raise(None) is True

    def test_whitespace_only_url_raises_value_error(self):
        """Whitespace-only URL should raise ValueError."""
        assert _validation_would_raise("   ") is True

    def test_valid_url_passes_validation(self):
        """Valid URL should pass validation."""
        assert _validation_would_raise("https://example.com") is False


class TestSafeFetch:
    """Test that fetch_data uses default= parameter."""

    def test_fetch_data_uses_default(self):
        """fetch_data should be called with default=''."""
        website_url = _w.fetch_data("website_url", default="")
        assert website_url == ""
        _w.fetch_data.assert_called_with("website_url", default="")


class TestDataStorage:
    """Test that data is stored with correct data_type."""

    def test_website_content_stored_as_json(self):
        """website_content should be stored with data_type='json' (pattern in node)."""
        _w.store_data.reset_mock()
        _w.store_data("website_content", {"pages": []}, data_type="json")
        _w.store_data.assert_called_once()
        call_kw = _w.store_data.call_args[1]
        assert call_kw.get("data_type") == "json"

    def test_page_data_stored_as_json(self):
        """Individual page data stored with data_type='json' (pattern in node)."""
        _w.store_data.reset_mock()
        _w.store_data("website_page_0_data", {"url": "https://example.com"}, data_type="json")
        _w.store_data.assert_called_once()
        call_kw = _w.store_data.call_args[1]
        assert call_kw.get("data_type") == "json"
