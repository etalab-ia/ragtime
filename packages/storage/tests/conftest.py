"""Pytest configuration and shared fixtures for storage tests."""

import pytest

from albert import AlbertClient
from rag_facile.core.schema import ChunkingConfig, RAGConfig


@pytest.fixture(autouse=True)
def mock_env_vars(monkeypatch):
    """Prevent tests from accidentally using real API keys."""
    monkeypatch.delenv("ALBERT_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)


@pytest.fixture
def api_key():
    """Test API key."""
    return "albert_test_key_123"


@pytest.fixture
def base_url():
    """Test base URL."""
    return "https://test.albert.api/v1/"


@pytest.fixture
def client(api_key, base_url):
    """Create test Albert client."""
    return AlbertClient(api_key=api_key, base_url=base_url)


@pytest.fixture
def mock_config(monkeypatch):
    """Patch rag_core.get_config() with test values."""
    config = RAGConfig(
        chunking=ChunkingConfig(chunk_size=512, chunk_overlap=50),
    )
    monkeypatch.setattr("rag_facile.storage.albert.get_config", lambda: config)
    return config
