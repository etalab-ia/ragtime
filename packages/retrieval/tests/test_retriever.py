"""Tests for search functions."""

import respx
from httpx import Response

from rag_facile.retrieval.albert import search_chunks


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
