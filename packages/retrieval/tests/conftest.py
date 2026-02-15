"""Pytest configuration and shared fixtures for retrieval-albert tests."""

import pytest

from albert import AlbertClient
from rag_core.schema import (
    ChunkingConfig,
    CitationsConfig,
    FormattingConfig,
    RAGConfig,
    RerankingConfig,
    RetrievalConfig,
)


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
        retrieval=RetrievalConfig(strategy="hybrid", top_k=10, score_threshold=0.0),
        reranking=RerankingConfig(enabled=True, model="openweight-rerank", top_n=3),
        formatting=FormattingConfig(
            citations=CitationsConfig(enabled=True, style="inline")
        ),
    )
    monkeypatch.setattr("retrieval.ingestion.get_config", lambda: config)
    monkeypatch.setattr("retrieval.albert.get_config", lambda: config)
    monkeypatch.setattr("retrieval.formatter.get_config", lambda: config)
    return config


@pytest.fixture
def mock_search_response():
    """Realistic Albert search response with French content."""
    return {
        "object": "list",
        "data": [
            {
                "method": "hybrid",
                "score": 0.95,
                "chunk": {
                    "object": "chunk",
                    "id": 101,
                    "collection_id": 1,
                    "document_id": 10,
                    "metadata": {"source": "rapport.pdf", "page": 5},
                    "content": "La loi Energie Climat vise a accelerer la transition energetique.",
                    "created": 1700000000,
                },
            },
            {
                "method": "hybrid",
                "score": 0.87,
                "chunk": {
                    "object": "chunk",
                    "id": 102,
                    "collection_id": 1,
                    "document_id": 11,
                    "metadata": {"source": "guide.pdf", "page": 12},
                    "content": "Les energies renouvelables sont au coeur de cette transition.",
                    "created": 1700000000,
                },
            },
            {
                "method": "hybrid",
                "score": 0.72,
                "chunk": {
                    "object": "chunk",
                    "id": 103,
                    "collection_id": 1,
                    "document_id": 10,
                    "metadata": {"source": "rapport.pdf", "page": 8},
                    "content": "L'objectif est d'atteindre la neutralite carbone d'ici 2050.",
                    "created": 1700000000,
                },
            },
        ],
        "usage": {
            "prompt_tokens": 10,
            "completion_tokens": 0,
            "total_tokens": 10,
            "cost": 0.001,
            "requests": 1,
        },
    }


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
