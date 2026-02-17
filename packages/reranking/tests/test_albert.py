"""Tests for Albert reranking."""

import respx
from httpx import Response

from rag_facile.reranking import rerank_chunks


class TestRerankChunks:
    """Tests for rerank_chunks function."""

    @respx.mock
    def test_reranks_chunks(
        self, client, base_url, sample_chunks, mock_rerank_response
    ):
        """Should reorder chunks by relevance."""
        respx.post(f"{base_url.rstrip('/')}/rerank").mock(
            return_value=Response(200, json=mock_rerank_response)
        )

        result = rerank_chunks(
            client, "query", sample_chunks, model="openweight-rerank"
        )

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
