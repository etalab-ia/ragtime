"""Tests for documents functionality."""

import tempfile
from pathlib import Path

import pytest
import respx
from httpx import Response

from albert_client import AlbertClient, Document, DocumentList


@pytest.fixture
def client(api_key, base_url):
    """Create test client."""
    return AlbertClient(api_key=api_key, base_url=base_url)


@pytest.fixture
def mock_document():
    """Mock document data."""
    return {
        "object": "document",
        "id": 456,
        "name": "test_doc.pdf",
        "collection_id": 123,
        "created": 1234567890,
        "chunks": 10,
    }


@pytest.fixture
def mock_document_list(mock_document):
    """Mock document list data."""
    return {
        "object": "list",
        "data": [
            mock_document,
            {**mock_document, "id": 789, "name": "another_doc.pdf", "chunks": 5},
        ],
    }


@pytest.fixture
def temp_file():
    """Create a temporary test file."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        f.write("Test document content\nSecond line of content.")
        temp_path = Path(f.name)

    yield temp_path

    # Cleanup
    temp_path.unlink()


class TestUploadDocument:
    """Test upload_document method."""

    @respx.mock
    def test_upload_document_basic(self, client, base_url, mock_document, temp_file):
        """Test uploading a document with default parameters."""
        respx.post(f"{base_url.rstrip('/')}/documents").mock(
            return_value=Response(200, json=mock_document)
        )

        result = client.upload_document(file_path=temp_file, collection_id=123)

        assert isinstance(result, Document)
        assert result.id == 456
        assert result.name == "test_doc.pdf"
        assert result.collection_id == 123
        assert result.chunks == 10

    @respx.mock
    def test_upload_document_with_parameters(
        self, client, base_url, mock_document, temp_file
    ):
        """Test uploading document with custom parameters."""
        respx.post(f"{base_url.rstrip('/')}/documents").mock(
            return_value=Response(200, json=mock_document)
        )

        result = client.upload_document(
            file_path=temp_file,
            collection_id=123,
            chunk_size=1024,
            chunk_overlap=100,
            page_range="1-10",
        )

        assert isinstance(result, Document)
        assert result.id == 456

    @respx.mock
    def test_upload_document_http_error(self, client, base_url, temp_file):
        """Test upload document with HTTP error."""
        respx.post(f"{base_url.rstrip('/')}/documents").mock(
            return_value=Response(
                400, json={"error": {"message": "Invalid collection"}}
            )
        )

        with pytest.raises(Exception):  # httpx.HTTPStatusError
            client.upload_document(file_path=temp_file, collection_id=999)


class TestListDocuments:
    """Test list_documents method."""

    @respx.mock
    def test_list_all_documents(self, client, base_url, mock_document_list):
        """Test listing all accessible documents."""
        respx.get(f"{base_url.rstrip('/')}/documents").mock(
            return_value=Response(200, json=mock_document_list)
        )

        result = client.list_documents()

        assert isinstance(result, DocumentList)
        assert result.object == "list"
        assert len(result.data) == 2
        assert result.data[0].id == 456
        assert result.data[1].id == 789

    @respx.mock
    def test_list_documents_by_collection(self, client, base_url, mock_document_list):
        """Test listing documents for a specific collection."""
        mock_route = respx.get(f"{base_url.rstrip('/')}/documents").mock(
            return_value=Response(200, json=mock_document_list)
        )

        result = client.list_documents(collection_id=123)

        # Verify collection filter was sent
        assert mock_route.calls.last.request.url.params.get("collection") == "123"

        assert isinstance(result, DocumentList)
        assert len(result.data) == 2

    @respx.mock
    def test_list_documents_empty(self, client, base_url):
        """Test listing documents when none exist."""
        respx.get(f"{base_url.rstrip('/')}/documents").mock(
            return_value=Response(200, json={"object": "list", "data": []})
        )

        result = client.list_documents()

        assert isinstance(result, DocumentList)
        assert len(result.data) == 0


class TestGetDocument:
    """Test get_document method."""

    @respx.mock
    def test_get_document(self, client, base_url, mock_document):
        """Test getting a specific document."""
        respx.get(f"{base_url.rstrip('/')}/documents/456").mock(
            return_value=Response(200, json=mock_document)
        )

        result = client.get_document(456)

        assert isinstance(result, Document)
        assert result.id == 456
        assert result.name == "test_doc.pdf"
        assert result.chunks == 10

    @respx.mock
    def test_get_document_not_found(self, client, base_url):
        """Test getting non-existent document."""
        respx.get(f"{base_url.rstrip('/')}/documents/999").mock(
            return_value=Response(404, json={"error": {"message": "Not found"}})
        )

        with pytest.raises(Exception):  # httpx.HTTPStatusError
            client.get_document(999)


class TestDeleteDocument:
    """Test delete_document method."""

    @respx.mock
    def test_delete_document(self, client, base_url):
        """Test deleting a document."""
        respx.delete(f"{base_url.rstrip('/')}/documents/456").mock(
            return_value=Response(204)
        )

        # Should not raise
        client.delete_document(456)

    @respx.mock
    def test_delete_document_not_found(self, client, base_url):
        """Test deleting non-existent document."""
        respx.delete(f"{base_url.rstrip('/')}/documents/999").mock(
            return_value=Response(404, json={"error": {"message": "Not found"}})
        )

        with pytest.raises(Exception):  # httpx.HTTPStatusError
            client.delete_document(999)
