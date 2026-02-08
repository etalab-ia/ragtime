"""Pytest configuration and shared fixtures."""

import pytest


@pytest.fixture(autouse=True)
def mock_env_vars(monkeypatch):
    """Mock environment variables for all tests."""
    # Prevent tests from accidentally using real API keys
    monkeypatch.delenv("ALBERT_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)


@pytest.fixture
def api_key():
    """Test API key."""
    return "albert_test_key_123"


@pytest.fixture
def base_url():
    """Test base URL (OpenAI client adds trailing slash)."""
    return "https://test.albert.api/v1/"
