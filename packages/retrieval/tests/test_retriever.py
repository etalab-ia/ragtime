"""Tests for AlbertRetrievalProvider."""

import respx
from httpx import Response

from rag_facile.retrieval.albert import AlbertRetrievalProvider


class TestAlbertRetrievalProvider:
    """Tests for AlbertRetrievalProvider.search()."""

    def _make_provider(self, client, **kwargs) -> AlbertRetrievalProvider:
        """Create a provider with an injected test client."""
        return AlbertRetrievalProvider(
            method=kwargs.get("method", "hybrid"),
            top_k=kwargs.get("top_k", 10),
            score_threshold=kwargs.get("score_threshold", 0.0),
            client=client,
        )

    @respx.mock
    def test_basic_search(self, client, base_url, mock_search_response):
        """Should return RetrievedChunk list from search results."""
        respx.post(f"{base_url.rstrip('/')}/search").mock(
            return_value=Response(200, json=mock_search_response)
        )

        provider = self._make_provider(client)
        result = provider.search("transition energetique", collection_ids=[1])

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

        provider = self._make_provider(client)
        result = provider.search("nonexistent", collection_ids=[1])

        assert result == []

    @respx.mock
    def test_search_passes_parameters(self, client, base_url, mock_search_response):
        """Should forward method and score_threshold to the API."""
        mock_route = respx.post(f"{base_url.rstrip('/')}/search").mock(
            return_value=Response(200, json=mock_search_response)
        )

        provider = self._make_provider(
            client, method="semantic", score_threshold=0.5, top_k=20
        )
        provider.search("query", collection_ids=[1, 2])

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

        provider = self._make_provider(client)
        result = provider.search("query", collection_ids=[1])

        assert len(result) == 1
        assert result[0]["source_file"] is None
        assert result[0]["page"] is None

    def test_lazy_client_not_created_at_init(self):
        """Should not create AlbertClient until first search call."""
        provider = AlbertRetrievalProvider()
        assert provider._client is None  # Not yet created
