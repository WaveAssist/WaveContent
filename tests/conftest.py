"""
Pytest configuration and shared fixtures for WaveContent tests.
"""
import pytest
from unittest.mock import MagicMock


@pytest.fixture
def mock_waveassist():
    """Mock waveassist so module-level code does not crash."""
    mock = MagicMock()
    mock.fetch_data.side_effect = lambda key, default=None, run_based=False, **kwargs: kwargs.get("default", default)
    mock.store_data.return_value = None
    mock.init.return_value = None
    mock.check_credits_and_notify.return_value = True
    mock.call_llm.return_value = None
    mock.send_email.return_value = True
    return mock


@pytest.fixture
def sample_website_content():
    """Sample website_content dict with pages."""
    return {
        "url": "https://example.com",
        "pages": [
            {
                "page_id": "page_0",
                "url": "https://example.com",
                "title": "Example Home",
                "meta_description": "Example site",
                "headings": [{"level": "h1", "text": "Welcome"}],
                "text_snippet": "Sample content",
            },
            {
                "page_id": "page_1",
                "url": "https://example.com/about",
                "title": "About",
                "meta_description": "About us",
                "headings": [{"level": "h1", "text": "About"}],
                "text_snippet": "About content",
            },
        ],
        "page_ids": ["page_0", "page_1"],
        "main_pages": ["https://example.com"],
    }


@pytest.fixture
def sample_executive_summary():
    """Sample executive_summary dict."""
    return {
        "summary": "Test summary",
        "key_findings": ["Finding 1", "Finding 2"],
        "recommendations": ["Rec 1"],
    }


@pytest.fixture
def sample_segregated_content():
    """Sample segregated_website_content dict."""
    return {
        "top_primary_pages": [
            {"page_id": "page_0", "url": "https://example.com"},
        ],
        "blog_article_pages": [],
        "product_pages": [],
        "documentation_pages": [],
        "legal_or_policy_pages": [],
        "other_pages": [{"page_id": "page_1", "url": "https://example.com/about"}],
    }
