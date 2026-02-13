"""Tests for retriever functions."""

import respx
from httpx import Response

from retrieval_albert import rerank_chunks, retrieve, search_chunks
from retrieval_albert._types import RetrievedChunk


class TestSearchChunks:
    """Tests for search_chunks function."""

    @respx.mock
    def test_basic_search(self, client, base_url, mock_search_response):
        """Should return RetrievedChunk list from search results."""
        respx.post(f"{base_url.rstrip('/')}/search").mock(
            return_value=Response(200, json=mock_search_response)
        )

        result = search_chunks(client, "transition energetique", collection_ids=[1])

        assert len(result) == 3
        assert result[0]["score"] == 0.95
        assert result[0]["source_file"] == "rapport.pdf"
        assert result[0]["page"] == 5
        assert "Energie Climat" in result[0]["content"]

    @respx.mock
    def test_empty_search_results(self, client, base_url):
        """Should return empty list when no results."""
        respx.post(f"{base_url.rstrip('/')}/search").mock(
            return_value=Response(200, json={"object": "list", "data": []})
        )

        result = search_chunks(client, "nonexistent", collection_ids=[1])

        assert result == []

    @respx.mock
    def test_search_passes_parameters(self, client, base_url, mock_search_response):
        """Should forward all parameters to the API."""
        mock_route = respx.post(f"{base_url.rstrip('/')}/search").mock(
            return_value=Response(200, json=mock_search_response)
        )

        search_chunks(
            client,
            "query",
            collection_ids=[1, 2],
            limit=20,
            method="semantic",
            score_threshold=0.5,
        )

        request_body = mock_route.calls.last.request.content.decode()
        assert '"semantic"' in request_body
        assert "0.5" in request_body

    @respx.mock
    def test_handles_missing_metadata(self, client, base_url):
        """Should handle chunks without metadata gracefully."""
        response = {
            "object": "list",
            "data": [
                {
                    "method": "semantic",
                    "score": 0.9,
                    "chunk": {
                        "object": "chunk",
                        "id": 1,
                        "collection_id": 1,
                        "document_id": 1,
                        "content": "Some content",
                        "metadata": None,
                        "created": 1700000000,
                    },
                }
            ],
        }

        respx.post(f"{base_url.rstrip('/')}/search").mock(
            return_value=Response(200, json=response)
        )

        result = search_chunks(client, "query", collection_ids=[1])

        assert len(result) == 1
        assert result[0]["source_file"] is None
        assert result[0]["page"] is None


class TestRerankChunks:
    """Tests for rerank_chunks function."""

    @respx.mock
    def test_reranks_chunks(self, client, base_url, mock_rerank_response):
        """Should reorder chunks by relevance."""
        respx.post(f"{base_url.rstrip('/')}/rerank").mock(
            return_value=Response(200, json=mock_rerank_response)
        )

        chunks: list[RetrievedChunk] = [
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

        result = rerank_chunks(client, "query", chunks, model="bge-reranker-large")

        # Mock returns indices [0, 2, 1] with scores [0.98, 0.85, 0.70]
        assert len(result) == 3
        assert result[0]["content"] == "First chunk"
        assert result[0]["score"] == 0.98
        assert result[1]["content"] == "Third chunk"
        assert result[2]["content"] == "Second chunk"

    def test_rerank_empty_chunks(self, client):
        """Should return empty list for empty input."""
        result = rerank_chunks(client, "query", [])

        assert result == []


class TestRetrieve:
    """Tests for retrieve function (full pipeline)."""

    @respx.mock
    def test_retrieve_with_reranking(
        self, client, base_url, mock_config, mock_search_response, mock_rerank_response
    ):
        """Should search then rerank when reranking is enabled."""
        respx.post(f"{base_url.rstrip('/')}/search").mock(
            return_value=Response(200, json=mock_search_response)
        )
        respx.post(f"{base_url.rstrip('/')}/rerank").mock(
            return_value=Response(200, json=mock_rerank_response)
        )

        result = retrieve(client, "transition energetique", collection_ids=[1])

        # Should have reranked results (3 from mock_rerank_response.results)
        assert len(result) == 3
        # First result should be the highest relevance after reranking
        assert result[0]["score"] == 0.98

    @respx.mock
    def test_retrieve_without_reranking(
        self, client, base_url, mock_config, mock_search_response
    ):
        """Should return search results directly when reranking disabled."""
        respx.post(f"{base_url.rstrip('/')}/search").mock(
            return_value=Response(200, json=mock_search_response)
        )

        result = retrieve(
            client, "transition energetique", collection_ids=[1], rerank=False
        )

        # Should return raw search results (3 from mock_search_response)
        assert len(result) == 3
        assert result[0]["score"] == 0.95

    @respx.mock
    def test_retrieve_empty_results(self, client, base_url, mock_config):
        """Should return empty list when search finds nothing."""
        respx.post(f"{base_url.rstrip('/')}/search").mock(
            return_value=Response(200, json={"object": "list", "data": []})
        )

        result = retrieve(client, "nonexistent", collection_ids=[1])

        assert result == []

    @respx.mock
    def test_retrieve_uses_config_defaults(
        self, client, base_url, mock_config, mock_search_response
    ):
        """Should use ragfacile.toml values as defaults."""
        mock_route = respx.post(f"{base_url.rstrip('/')}/search").mock(
            return_value=Response(200, json=mock_search_response)
        )
        respx.post(f"{base_url.rstrip('/')}/rerank").mock(
            return_value=Response(
                200,
                json={
                    "object": "list",
                    "id": "r1",
                    "data": [],
                    "results": [{"relevance_score": 0.9, "index": 0}],
                    "model": "bge-reranker-large",
                },
            )
        )

        retrieve(client, "query", collection_ids=[1])

        # Verify search was called with config defaults
        request_body = mock_route.calls.last.request.content.decode()
        assert '"hybrid"' in request_body  # config.retrieval.method
        assert '"limit":10' in request_body or '"limit": 10' in request_body

    @respx.mock
    def test_retrieve_overrides_config(
        self, client, base_url, mock_config, mock_search_response
    ):
        """Should allow overriding config values."""
        mock_route = respx.post(f"{base_url.rstrip('/')}/search").mock(
            return_value=Response(200, json=mock_search_response)
        )

        retrieve(
            client,
            "query",
            collection_ids=[1],
            top_k=5,
            method="semantic",
            rerank=False,
        )

        request_body = mock_route.calls.last.request.content.decode()
        assert '"semantic"' in request_body
        assert '"limit":5' in request_body or '"limit": 5' in request_body
