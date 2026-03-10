"""Tests for AlbertRerankingProvider."""

import respx
from httpx import Response

from rag_facile.reranking.albert import AlbertRerankingProvider


class TestAlbertRerankingProvider:
    """Tests for AlbertRerankingProvider.rerank()."""

    def _make_provider(self, client, **kwargs) -> AlbertRerankingProvider:
        """Create a provider with an injected test client."""
        return AlbertRerankingProvider(
            model=kwargs.get("model", "openweight-rerank"),
            top_n=kwargs.get("top_n", 3),
            client=client,
        )

    @respx.mock
    def test_reranks_chunks(
        self, client, base_url, sample_chunks, mock_rerank_response
    ):
        """Should reorder chunks by relevance."""
        respx.post(f"{base_url.rstrip('/')}/rerank").mock(
            return_value=Response(200, json=mock_rerank_response)
        )

        provider = self._make_provider(client)
        result = provider.rerank("query", sample_chunks)

        # Mock returns indices [0, 2, 1] with scores [0.98, 0.85, 0.70]
        assert len(result) == 3
        assert result[0]["content"] == "First chunk"
        assert result[0]["score"] == 0.98
        assert result[1]["content"] == "Third chunk"
        assert result[2]["content"] == "Second chunk"

    def test_rerank_empty_chunks(self, client):
        """Should return empty list for empty input."""
        provider = self._make_provider(client)
        result = provider.rerank("query", [])
        assert result == []

    @respx.mock
    def test_rerank_uses_configured_model(self, client, base_url):
        """Should send the configured model name in the request."""
        # One-item response that matches the single chunk below
        single_rerank_response = {
            "object": "list",
            "id": "rerank-test",
            "data": [],
            "results": [{"relevance_score": 0.98, "index": 0}],
            "model": "custom-rerank-model",
            "usage": {"prompt_tokens": 10, "completion_tokens": 0, "total_tokens": 10},
        }
        mock_route = respx.post(f"{base_url.rstrip('/')}/rerank").mock(
            return_value=Response(200, json=single_rerank_response)
        )

        provider = self._make_provider(client, model="custom-rerank-model", top_n=1)
        from rag_facile.core import RetrievedChunk

        chunks = [
            RetrievedChunk(
                content="chunk",
                score=0.9,
                source_file=None,
                page=None,
                collection_id=1,
                document_id=1,
                chunk_id=1,
            )
        ]
        provider.rerank("query", chunks)

        request_body = mock_route.calls.last.request.content.decode()
        assert "custom-rerank-model" in request_body
