"""Tests for search functionality."""

import pytest
import respx
from httpx import Response

from albert import AlbertClient, Chunk, SearchResponse, SearchResult


@pytest.fixture
def client(api_key, base_url):
    """Create test client."""
    return AlbertClient(api_key=api_key, base_url=base_url)


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
                    "metadata": {"source": "doc1.pdf", "page": 5},
                    "content": "La loi Énergie Climat vise à accélérer la transition énergétique.",
                },
            },
            {
                "method": "hybrid",
                "score": 0.87,
                "chunk": {
                    "object": "chunk",
                    "id": 456,
                    "metadata": {"source": "doc2.pdf", "page": 12},
                    "content": "Les énergies renouvelables sont au cœur de cette transition.",
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


class TestSearch:
    """Test search method."""

    @respx.mock
    def test_search_basic(self, client, base_url, mock_search_response):
        """Test basic search request."""
        # Mock the search endpoint
        respx.post(f"{base_url.rstrip('/')}/search").mock(
            return_value=Response(200, json=mock_search_response)
        )

        # Make request
        result = client.search(prompt="Loi Énergie Climat", collections=["col_123"])

        # Verify result type
        assert isinstance(result, SearchResponse)
        assert result.object == "list"
        assert len(result.data) == 2

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
        assert chunk.metadata["source"] == "doc1.pdf"

        # Verify usage
        assert result.usage.total_tokens == 10
        assert result.usage.cost == 0.001

    @respx.mock
    def test_search_with_all_parameters(self, client, base_url, mock_search_response):
        """Test search with all optional parameters."""
        mock_route = respx.post(f"{base_url.rstrip('/')}/search").mock(
            return_value=Response(200, json=mock_search_response)
        )

        # Make request with all parameters
        result = client.search(
            prompt="transition énergétique",
            collections=[123, 456],
            limit=20,
            offset=10,
            method="semantic",
            score_threshold=0.8,
            rff_k=30,
        )

        # Verify request was made
        assert mock_route.called
        request_body = mock_route.calls.last.request.content.decode()
        assert "transition énergétique" in request_body
        assert "semantic" in request_body
        assert "0.8" in request_body

        # Verify response
        assert isinstance(result, SearchResponse)
        assert len(result.data) == 2

    @respx.mock
    def test_search_empty_results(self, client, base_url):
        """Test search with no results."""
        empty_response = {"object": "list", "data": []}

        respx.post(f"{base_url.rstrip('/')}/search").mock(
            return_value=Response(200, json=empty_response)
        )

        result = client.search(prompt="nonexistent query")

        assert isinstance(result, SearchResponse)
        assert len(result.data) == 0

    @respx.mock
    def test_search_default_collections(self, client, base_url, mock_search_response):
        """Test search with default (empty) collections."""
        mock_route = respx.post(f"{base_url.rstrip('/')}/search").mock(
            return_value=Response(200, json=mock_search_response)
        )

        result = client.search(prompt="test query")

        # Verify collections defaults to empty list
        request_body = mock_route.calls.last.request.content.decode()
        assert '"collections":[]' in request_body or '"collections": []' in request_body

        assert isinstance(result, SearchResponse)

    @respx.mock
    def test_search_without_usage(self, client, base_url):
        """Test search response without usage field."""
        response_no_usage = {
            "object": "list",
            "data": [
                {
                    "method": "semantic",
                    "score": 0.9,
                    "chunk": {
                        "object": "chunk",
                        "id": 1,
                        "metadata": {},
                        "content": "Test content",
                    },
                }
            ],
        }

        respx.post(f"{base_url.rstrip('/')}/search").mock(
            return_value=Response(200, json=response_no_usage)
        )

        result = client.search(prompt="test")

        assert isinstance(result, SearchResponse)
        assert result.usage is None

    @respx.mock
    def test_search_http_error(self, client, base_url):
        """Test search with HTTP error response."""
        respx.post(f"{base_url.rstrip('/')}/search").mock(
            return_value=Response(
                404, json={"error": {"message": "Collection not found"}}
            )
        )

        with pytest.raises(Exception):  # httpx.HTTPStatusError
            client.search(prompt="test", collections=["nonexistent"])

    @respx.mock
    def test_search_pydantic_helpers(self, client, base_url, mock_search_response):
        """Test Pydantic helper methods on response."""
        respx.post(f"{base_url.rstrip('/')}/search").mock(
            return_value=Response(200, json=mock_search_response)
        )

        result = client.search(prompt="test")

        # Test .to_dict()
        result_dict = result.to_dict()
        assert isinstance(result_dict, dict)
        assert result_dict["object"] == "list"
        assert len(result_dict["data"]) == 2

        # Test .to_json()
        result_json = result.to_json()
        assert isinstance(result_json, str)
        assert "énergie" in result_json.lower()
        assert "climat" in result_json.lower()

        # Test on nested models
        chunk_dict = result.data[0].chunk.to_dict()
        assert chunk_dict["id"] == 123


class TestSearchMethods:
    """Test different search methods."""

    @respx.mock
    @pytest.mark.parametrize("method", ["hybrid", "semantic", "lexical"])
    def test_search_methods(self, client, base_url, method, mock_search_response):
        """Test all three search methods."""
        # Update response to match method
        mock_search_response["data"][0]["method"] = method

        mock_route = respx.post(f"{base_url.rstrip('/')}/search").mock(
            return_value=Response(200, json=mock_search_response)
        )

        result = client.search(prompt="test", method=method)

        # Verify method was sent in request
        request_body = mock_route.calls.last.request.content.decode()
        assert f'"{method}"' in request_body

        assert result.data[0].method == method


class TestSearchPagination:
    """Test search pagination."""

    @respx.mock
    def test_search_with_limit_and_offset(self, client, base_url, mock_search_response):
        """Test pagination parameters."""
        mock_route = respx.post(f"{base_url.rstrip('/')}/search").mock(
            return_value=Response(200, json=mock_search_response)
        )

        result = client.search(prompt="test", limit=50, offset=100)

        # Verify pagination params in request
        request_body = mock_route.calls.last.request.content.decode()
        assert '"limit":50' in request_body or '"limit": 50' in request_body
        assert '"offset":100' in request_body or '"offset": 100' in request_body

        assert isinstance(result, SearchResponse)
