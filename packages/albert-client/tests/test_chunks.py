"""Tests for chunks functionality."""

import pytest
import respx
from httpx import Response

from albert_client import AlbertClient, Chunk, ChunkList


@pytest.fixture
def client(api_key, base_url):
    """Create test client."""
    return AlbertClient(api_key=api_key, base_url=base_url)


@pytest.fixture
def mock_chunk():
    """Mock chunk data."""
    return {
        "object": "chunk",
        "id": 789,
        "metadata": {"page": 1, "source": "test_doc.pdf"},
        "content": "This is the content of the chunk from the document.",
    }


@pytest.fixture
def mock_chunk_list(mock_chunk):
    """Mock chunk list data."""
    return {
        "object": "list",
        "data": [
            mock_chunk,
            {
                **mock_chunk,
                "id": 790,
                "metadata": {"page": 2, "source": "test_doc.pdf"},
                "content": "This is the second chunk.",
            },
        ],
    }


class TestListChunks:
    """Test list_chunks method."""

    @respx.mock
    def test_list_chunks(self, client, base_url, mock_chunk_list):
        """Test listing all chunks for a document."""
        respx.get(f"{base_url.rstrip('/')}/chunks/456").mock(
            return_value=Response(200, json=mock_chunk_list)
        )

        result = client.list_chunks(document_id=456)

        assert isinstance(result, ChunkList)
        assert result.object == "list"
        assert len(result.data) == 2
        assert result.data[0].id == 789
        assert result.data[1].id == 790
        assert "content of the chunk" in result.data[0].content

    @respx.mock
    def test_list_chunks_empty(self, client, base_url):
        """Test listing chunks when none exist."""
        respx.get(f"{base_url.rstrip('/')}/chunks/456").mock(
            return_value=Response(200, json={"object": "list", "data": []})
        )

        result = client.list_chunks(document_id=456)

        assert isinstance(result, ChunkList)
        assert len(result.data) == 0

    @respx.mock
    def test_list_chunks_http_error(self, client, base_url):
        """Test list chunks with HTTP error."""
        respx.get(f"{base_url.rstrip('/')}/chunks/999").mock(
            return_value=Response(
                404, json={"error": {"message": "Document not found"}}
            )
        )

        with pytest.raises(Exception):  # httpx.HTTPStatusError
            client.list_chunks(document_id=999)


class TestGetChunk:
    """Test get_chunk method."""

    @respx.mock
    def test_get_chunk(self, client, base_url, mock_chunk):
        """Test getting a specific chunk."""
        respx.get(f"{base_url.rstrip('/')}/chunks/456/789").mock(
            return_value=Response(200, json=mock_chunk)
        )

        result = client.get_chunk(document_id=456, chunk_id=789)

        assert isinstance(result, Chunk)
        assert result.id == 789
        assert result.metadata["page"] == 1
        assert "content of the chunk" in result.content

    @respx.mock
    def test_get_chunk_with_metadata(self, client, base_url):
        """Test getting chunk with complex metadata."""
        chunk_with_metadata = {
            "object": "chunk",
            "id": 789,
            "metadata": {
                "page": 1,
                "source": "test_doc.pdf",
                "section": "Introduction",
                "author": "John Doe",
            },
            "content": "Sample content.",
        }

        respx.get(f"{base_url.rstrip('/')}/chunks/456/789").mock(
            return_value=Response(200, json=chunk_with_metadata)
        )

        result = client.get_chunk(document_id=456, chunk_id=789)

        assert result.metadata["section"] == "Introduction"
        assert result.metadata["author"] == "John Doe"

    @respx.mock
    def test_get_chunk_not_found(self, client, base_url):
        """Test getting non-existent chunk."""
        respx.get(f"{base_url.rstrip('/')}/chunks/456/999").mock(
            return_value=Response(404, json={"error": {"message": "Chunk not found"}})
        )

        with pytest.raises(Exception):  # httpx.HTTPStatusError
            client.get_chunk(document_id=456, chunk_id=999)

    @respx.mock
    def test_get_chunk_pydantic_helpers(self, client, base_url, mock_chunk):
        """Test chunk Pydantic model helper methods."""
        respx.get(f"{base_url.rstrip('/')}/chunks/456/789").mock(
            return_value=Response(200, json=mock_chunk)
        )

        result = client.get_chunk(document_id=456, chunk_id=789)

        # Test to_dict()
        chunk_dict = result.to_dict()
        assert isinstance(chunk_dict, dict)
        assert chunk_dict["id"] == 789
        assert chunk_dict["object"] == "chunk"

        # Test to_json()
        chunk_json = result.to_json()
        assert isinstance(chunk_json, str)
        assert "789" in chunk_json
        assert "chunk" in chunk_json
