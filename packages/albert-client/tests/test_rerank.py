"""Tests for rerank functionality."""

import pytest
import respx
from httpx import Response

from albert_client import AlbertClient, RerankResponse, RerankResult


@pytest.fixture
def client(api_key, base_url):
    """Create test client."""
    return AlbertClient(api_key=api_key, base_url=base_url)


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
        "data": [  # Deprecated field, but may be present
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


class TestRerank:
    """Test rerank method."""

    @respx.mock
    def test_rerank_basic(
        self, client, base_url, mock_rerank_response, sample_documents
    ):
        """Test basic rerank request."""
        # Mock the rerank endpoint
        respx.post(f"{base_url.rstrip('/')}/rerank").mock(
            return_value=Response(200, json=mock_rerank_response)
        )

        # Make request
        result = client.rerank(
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
        assert result.results[1].relevance_score == 0.87
        assert result.results[1].index == 0

        # Verify usage
        assert result.usage.total_tokens == 50
        assert result.usage.cost == 0.005

    @respx.mock
    def test_rerank_with_top_n(
        self, client, base_url, mock_rerank_response, sample_documents
    ):
        """Test rerank with top_n parameter."""
        # Return only top 2 results
        limited_response = mock_rerank_response.copy()
        limited_response["results"] = limited_response["results"][:2]
        limited_response["data"] = limited_response["data"][:2]

        mock_route = respx.post(f"{base_url.rstrip('/')}/rerank").mock(
            return_value=Response(200, json=limited_response)
        )

        result = client.rerank(
            query="transition énergétique",
            documents=sample_documents,
            model="BAAI/bge-reranker-v2-m3",
            top_n=2,
        )

        # Verify top_n was sent in request
        request_body = mock_route.calls.last.request.content.decode()
        assert '"top_n":2' in request_body or '"top_n": 2' in request_body

        # Verify only top 2 results returned
        assert len(result.results) == 2
        assert result.results[0].relevance_score == 0.95

    @respx.mock
    def test_rerank_preserves_original_index(
        self, client, base_url, mock_rerank_response, sample_documents
    ):
        """Test that rerank preserves original document indices."""
        respx.post(f"{base_url.rstrip('/')}/rerank").mock(
            return_value=Response(200, json=mock_rerank_response)
        )

        result = client.rerank(
            query="test",
            documents=sample_documents,
            model="BAAI/bge-reranker-v2-m3",
        )

        # Verify indices map back to original positions
        for rerank_result in result.results:
            assert isinstance(rerank_result, RerankResult)
            assert 0 <= rerank_result.index < len(sample_documents)

    @respx.mock
    def test_rerank_without_usage(self, client, base_url, sample_documents):
        """Test rerank response without usage field."""
        response_no_usage = {
            "object": "list",
            "id": "rerank-123",
            "results": [{"relevance_score": 0.9, "index": 0}],
            "data": [{"object": "rerank", "score": 0.9, "index": 0}],
            "model": "test-model",
        }

        respx.post(f"{base_url.rstrip('/')}/rerank").mock(
            return_value=Response(200, json=response_no_usage)
        )

        result = client.rerank(
            query="test", documents=sample_documents, model="test-model"
        )

        assert isinstance(result, RerankResponse)
        assert result.usage is None

    @respx.mock
    def test_rerank_http_error(self, client, base_url, sample_documents):
        """Test rerank with HTTP error response."""
        respx.post(f"{base_url.rstrip('/')}/rerank").mock(
            return_value=Response(404, json={"error": {"message": "Model not found"}})
        )

        with pytest.raises(Exception):  # httpx.HTTPStatusError
            client.rerank(
                query="test", documents=sample_documents, model="nonexistent-model"
            )

    @respx.mock
    def test_rerank_pydantic_helpers(
        self, client, base_url, mock_rerank_response, sample_documents
    ):
        """Test Pydantic helper methods on rerank response."""
        respx.post(f"{base_url.rstrip('/')}/rerank").mock(
            return_value=Response(200, json=mock_rerank_response)
        )

        result = client.rerank(
            query="test", documents=sample_documents, model="BAAI/bge-reranker-v2-m3"
        )

        # Test .to_dict()
        result_dict = result.to_dict()
        assert isinstance(result_dict, dict)
        assert result_dict["object"] == "list"
        assert result_dict["model"] == "BAAI/bge-reranker-v2-m3"
        assert len(result_dict["results"]) == 3

        # Test .to_json()
        result_json = result.to_json()
        assert isinstance(result_json, str)
        assert "BAAI/bge-reranker-v2-m3" in result_json

        # Test on nested models
        first_result = result.results[0]
        result_dict = first_result.to_dict()
        assert result_dict["relevance_score"] == 0.95


class TestRerankRequestValidation:
    """Test rerank request parameter validation."""

    @respx.mock
    def test_rerank_with_empty_documents(self, client, base_url):
        """Test rerank with empty document list."""
        respx.post(f"{base_url.rstrip('/')}/rerank").mock(
            return_value=Response(
                200,
                json={
                    "object": "list",
                    "id": "rerank-empty",
                    "results": [],
                    "data": [],
                    "model": "test-model",
                },
            )
        )

        result = client.rerank(query="test", documents=[], model="test-model")

        assert isinstance(result, RerankResponse)
        assert len(result.results) == 0

    @respx.mock
    def test_rerank_request_body_structure(
        self, client, base_url, mock_rerank_response, sample_documents
    ):
        """Test that request body has correct structure."""
        mock_route = respx.post(f"{base_url.rstrip('/')}/rerank").mock(
            return_value=Response(200, json=mock_rerank_response)
        )

        client.rerank(
            query="transition énergétique",
            documents=sample_documents,
            model="BAAI/bge-reranker-v2-m3",
            top_n=2,
        )

        # Verify request body structure
        request_body = mock_route.calls.last.request.content.decode()
        assert "query" in request_body
        assert "documents" in request_body
        assert "model" in request_body
        assert "top_n" in request_body
        assert "transition énergétique" in request_body


class TestRerankScores:
    """Test rerank score ordering and values."""

    @respx.mock
    def test_rerank_scores_descending(
        self, client, base_url, mock_rerank_response, sample_documents
    ):
        """Test that rerank results are ordered by score descending."""
        respx.post(f"{base_url.rstrip('/')}/rerank").mock(
            return_value=Response(200, json=mock_rerank_response)
        )

        result = client.rerank(
            query="test", documents=sample_documents, model="test-model"
        )

        # Verify scores are in descending order
        scores = [r.relevance_score for r in result.results]
        assert scores == sorted(scores, reverse=True)

    @respx.mock
    def test_rerank_score_range(
        self, client, base_url, mock_rerank_response, sample_documents
    ):
        """Test that rerank scores are valid floats."""
        respx.post(f"{base_url.rstrip('/')}/rerank").mock(
            return_value=Response(200, json=mock_rerank_response)
        )

        result = client.rerank(
            query="test", documents=sample_documents, model="test-model"
        )

        # Verify all scores are valid floats
        for rerank_result in result.results:
            assert isinstance(rerank_result.relevance_score, float)
            assert isinstance(rerank_result.index, int)
