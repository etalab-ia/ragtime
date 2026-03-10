"""Tests for async search functionality."""

import pytest
import respx
from httpx import Response

from albert import AsyncAlbertClient, Chunk, SearchResponse, SearchResult


@pytest.fixture
def client(api_key, base_url):
    """Create test async client."""
    return AsyncAlbertClient(api_key=api_key, base_url=base_url)


@pytest.fixture
def mock_search_response():
    """Mock search response data."""
    return {
        "object": "list",
        "data": [
            {
                "method": "hybrid",
                "score": 0.95,
                "chunk": {
                    "object": "chunk",
                    "id": 123,
                    "collection_id": 1,
                    "document_id": 10,
                    "metadata": {"source": "doc1.pdf", "page": 5},
                    "content": "La loi Énergie Climat vise à accélérer la transition énergétique.",
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


class TestAsyncSearch:
    """Test async search method."""

    @respx.mock
    async def test_async_search_basic(self, client, base_url, mock_search_response):
        """Test basic async search request."""
        # Mock the search endpoint
        respx.post(f"{base_url.rstrip('/')}/search").mock(
            return_value=Response(200, json=mock_search_response)
        )

        # Make async request
        result = await client.search(query="Loi Énergie Climat", collection_ids=[1])

        # Verify result type
        assert isinstance(result, SearchResponse)
        assert result.object == "list"
        assert len(result.data) == 1

        # Verify first result
        first_result = result.data[0]
        assert isinstance(first_result, SearchResult)
        assert first_result.method == "hybrid"
        assert first_result.score == 0.95

        # Verify chunk
        chunk = first_result.chunk
        assert isinstance(chunk, Chunk)
        assert chunk.id == 123
        assert "énergie" in chunk.content.lower()

    @respx.mock
    async def test_async_search_with_parameters(
        self, client, base_url, mock_search_response
    ):
        """Test async search with optional parameters."""
        respx.post(f"{base_url.rstrip('/')}/search").mock(
            return_value=Response(200, json=mock_search_response)
        )

        result = await client.search(
            query="test query",
            collection_ids=[123],
            limit=20,
            method="semantic",
            score_threshold=0.8,
        )

        assert isinstance(result, SearchResponse)
        assert len(result.data) == 1

    @respx.mock
    async def test_async_search_context_manager(
        self, api_key, base_url, mock_search_response
    ):
        """Test async search with context manager."""
        respx.post(f"{base_url.rstrip('/')}/search").mock(
            return_value=Response(200, json=mock_search_response)
        )

        async with AsyncAlbertClient(api_key=api_key, base_url=base_url) as client:
            result = await client.search(query="test")
            assert isinstance(result, SearchResponse)

    @respx.mock
    async def test_async_search_empty_results(self, client, base_url):
        """Test async search with no results."""
        empty_response = {"object": "list", "data": []}

        respx.post(f"{base_url.rstrip('/')}/search").mock(
            return_value=Response(200, json=empty_response)
        )

        result = await client.search(query="nonexistent query")

        assert isinstance(result, SearchResponse)
        assert len(result.data) == 0

    @respx.mock
    async def test_async_search_http_error(self, client, base_url):
        """Test async search with HTTP error response."""
        respx.post(f"{base_url.rstrip('/')}/search").mock(
            return_value=Response(
                404, json={"error": {"message": "Collection not found"}}
            )
        )

        with pytest.raises(Exception):  # httpx.HTTPStatusError
            await client.search(query="test", collection_ids=[999])


class TestAsyncSearchMethods:
    """Test different async search methods."""

    @respx.mock
    @pytest.mark.parametrize("method", ["hybrid", "semantic", "lexical"])
    async def test_async_search_methods(
        self, client, base_url, method, mock_search_response
    ):
        """Test all three async search methods."""
        # Update response to match method
        mock_search_response["data"][0]["method"] = method

        respx.post(f"{base_url.rstrip('/')}/search").mock(
            return_value=Response(200, json=mock_search_response)
        )

        result = await client.search(query="test", method=method)

        assert result.data[0].method == method
