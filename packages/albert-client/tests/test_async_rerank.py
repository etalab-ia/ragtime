"""Tests for async rerank functionality."""

import pytest
import respx
from httpx import Response

from albert_client import AsyncAlbertClient, RerankResponse, RerankResult


@pytest.fixture
def client(api_key, base_url):
    """Create test async client."""
    return AsyncAlbertClient(api_key=api_key, base_url=base_url)


@pytest.fixture
def mock_rerank_response():
    """Mock rerank response data."""
    return {
        "object": "list",
        "id": "rerank-xyz789",
        "results": [
            {"relevance_score": 0.95, "index": 2},
            {"relevance_score": 0.87, "index": 0},
            {"relevance_score": 0.73, "index": 1},
        ],
        "data": [  # Deprecated field
            {"object": "rerank", "score": 0.95, "index": 2},
            {"object": "rerank", "score": 0.87, "index": 0},
            {"object": "rerank", "score": 0.73, "index": 1},
        ],
        "model": "BAAI/bge-reranker-v2-m3",
        "usage": {
            "prompt_tokens": 50,
            "completion_tokens": 0,
            "total_tokens": 50,
            "cost": 0.005,
            "requests": 1,
        },
    }


@pytest.fixture
def sample_documents():
    """Sample documents for reranking."""
    return [
        "Le changement climatique est un défi mondial.",
        "Les énergies renouvelables sont l'avenir.",
        "La transition énergétique nécessite des investissements importants.",
    ]


class TestAsyncRerank:
    """Test async rerank method."""

    @respx.mock
    async def test_async_rerank_basic(
        self, client, base_url, mock_rerank_response, sample_documents
    ):
        """Test basic async rerank request."""
        # Mock the rerank endpoint
        respx.post(f"{base_url.rstrip('/')}/rerank").mock(
            return_value=Response(200, json=mock_rerank_response)
        )

        # Make async request
        result = await client.rerank(
            query="transition énergétique",
            documents=sample_documents,
            model="BAAI/bge-reranker-v2-m3",
        )

        # Verify result type
        assert isinstance(result, RerankResponse)
        assert result.object == "list"
        assert result.id == "rerank-xyz789"
        assert result.model == "BAAI/bge-reranker-v2-m3"
        assert len(result.results) == 3

        # Verify results are sorted by relevance (highest first)
        assert result.results[0].relevance_score == 0.95
        assert result.results[0].index == 2

        # Verify usage
        assert result.usage.total_tokens == 50
        assert result.usage.cost == 0.005

    @respx.mock
    async def test_async_rerank_with_top_n(
        self, client, base_url, mock_rerank_response, sample_documents
    ):
        """Test async rerank with top_n parameter."""
        # Return only top 2 results
        limited_response = mock_rerank_response.copy()
        limited_response["results"] = limited_response["results"][:2]
        limited_response["data"] = limited_response["data"][:2]

        respx.post(f"{base_url.rstrip('/')}/rerank").mock(
            return_value=Response(200, json=limited_response)
        )

        result = await client.rerank(
            query="transition énergétique",
            documents=sample_documents,
            model="BAAI/bge-reranker-v2-m3",
            top_n=2,
        )

        # Verify only top 2 results returned
        assert len(result.results) == 2
        assert result.results[0].relevance_score == 0.95

    @respx.mock
    async def test_async_rerank_context_manager(
        self, api_key, base_url, mock_rerank_response, sample_documents
    ):
        """Test async rerank with context manager."""
        respx.post(f"{base_url.rstrip('/')}/rerank").mock(
            return_value=Response(200, json=mock_rerank_response)
        )

        async with AsyncAlbertClient(api_key=api_key, base_url=base_url) as client:
            result = await client.rerank(
                query="test", documents=sample_documents, model="test-model"
            )
            assert isinstance(result, RerankResponse)

    @respx.mock
    async def test_async_rerank_preserves_original_index(
        self, client, base_url, mock_rerank_response, sample_documents
    ):
        """Test that async rerank preserves original document indices."""
        respx.post(f"{base_url.rstrip('/')}/rerank").mock(
            return_value=Response(200, json=mock_rerank_response)
        )

        result = await client.rerank(
            query="test",
            documents=sample_documents,
            model="BAAI/bge-reranker-v2-m3",
        )

        # Verify indices map back to original positions
        for rerank_result in result.results:
            assert isinstance(rerank_result, RerankResult)
            assert 0 <= rerank_result.index < len(sample_documents)

    @respx.mock
    async def test_async_rerank_http_error(self, client, base_url, sample_documents):
        """Test async rerank with HTTP error response."""
        respx.post(f"{base_url.rstrip('/')}/rerank").mock(
            return_value=Response(404, json={"error": {"message": "Model not found"}})
        )

        with pytest.raises(Exception):  # httpx.HTTPStatusError
            await client.rerank(query="test", documents=sample_documents, model="nonexistent-model")

    @respx.mock
    async def test_async_rerank_scores_descending(
        self, client, base_url, mock_rerank_response, sample_documents
    ):
        """Test that async rerank results are ordered by score descending."""
        respx.post(f"{base_url.rstrip('/')}/rerank").mock(
            return_value=Response(200, json=mock_rerank_response)
        )

        result = await client.rerank(query="test", documents=sample_documents, model="test-model")

        # Verify scores are in descending order
        scores = [r.relevance_score for r in result.results]
        assert scores == sorted(scores, reverse=True)
