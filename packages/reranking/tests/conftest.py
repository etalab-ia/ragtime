"""Pytest configuration and shared fixtures for reranking tests."""

import pytest

from albert import AlbertClient
from rag_facile.core import RetrievedChunk


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
def sample_chunks():
    """Sample retrieved chunks for reranking tests."""
    return [
        RetrievedChunk(
            content="First chunk",
            score=0.95,
            source_file="a.pdf",
            page=1,
            collection_id=1,
            document_id=1,
            chunk_id=1,
        ),
        RetrievedChunk(
            content="Second chunk",
            score=0.87,
            source_file="b.pdf",
            page=2,
            collection_id=1,
            document_id=2,
            chunk_id=2,
        ),
        RetrievedChunk(
            content="Third chunk",
            score=0.72,
            source_file="c.pdf",
            page=3,
            collection_id=1,
            document_id=3,
            chunk_id=3,
        ),
    ]


@pytest.fixture
def mock_rerank_response():
    """Mock rerank response."""
    return {
        "object": "list",
        "id": "rerank-test-123",
        "data": [],
        "results": [
            {"relevance_score": 0.98, "index": 0},
            {"relevance_score": 0.85, "index": 2},
            {"relevance_score": 0.70, "index": 1},
        ],
        "model": "openweight-rerank",
        "usage": {
            "prompt_tokens": 50,
            "completion_tokens": 0,
            "total_tokens": 50,
            "cost": 0.002,
            "requests": 1,
        },
    }
