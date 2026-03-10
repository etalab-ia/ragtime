"""Tests for async collections, documents, and chunks functionality."""

import pytest
import respx
from httpx import Response

from albert import (
    AsyncAlbertClient,
    Chunk,
    ChunkList,
    Collection,
    CollectionList,
    Document,
    DocumentList,
    DocumentResponse,
)


@pytest.fixture
def client(api_key, base_url):
    """Create test async client."""
    return AsyncAlbertClient(api_key=api_key, base_url=base_url)


@pytest.fixture
def mock_collection():
    """Mock collection data."""
    return {
        "object": "collection",
        "id": 123,
        "name": "Test Collection",
        "owner": "user@example.com",
        "description": "A test collection",
        "visibility": "private",
        "created": 1234567890,
        "updated": 1234567890,
        "documents": 5,
    }


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
def mock_chunk():
    """Mock chunk data."""
    return {
        "object": "chunk",
        "id": 789,
        "collection_id": 123,
        "document_id": 456,
        "metadata": {"page": 1, "source": "test_doc.pdf"},
        "content": "This is the content of the chunk from the document.",
        "created": 1700000000,
    }


@pytest.fixture
def temp_file(tmp_path):
    """Create a temporary test file."""
    f = tmp_path / "test.txt"
    f.write_text("Test document content\nSecond line of content.")
    return f


class TestAsyncCollections:
    """Test async collections methods."""

    @respx.mock
    async def test_create_collection(self, client, base_url, mock_collection):
        """Test async create collection."""
        respx.post(f"{base_url.rstrip('/')}/collections").mock(
            return_value=Response(200, json=mock_collection)
        )

        result = await client.create_collection(
            name="Test Collection", description="A test collection"
        )

        assert isinstance(result, Collection)
        assert result.id == 123
        assert result.name == "Test Collection"

    @respx.mock
    async def test_list_collections(self, client, base_url, mock_collection):
        """Test async list collections."""
        respx.get(f"{base_url.rstrip('/')}/collections").mock(
            return_value=Response(
                200, json={"object": "list", "data": [mock_collection]}
            )
        )

        result = await client.list_collections()

        assert isinstance(result, CollectionList)
        assert len(result.data) == 1
        assert result.data[0].id == 123

    @respx.mock
    async def test_get_collection(self, client, base_url, mock_collection):
        """Test async get collection."""
        respx.get(f"{base_url.rstrip('/')}/collections/123").mock(
            return_value=Response(200, json=mock_collection)
        )

        result = await client.get_collection(123)

        assert isinstance(result, Collection)
        assert result.id == 123

    @respx.mock
    async def test_update_collection(self, client, base_url):
        """Test async update collection."""
        respx.patch(f"{base_url.rstrip('/')}/collections/123").mock(
            return_value=Response(204)
        )

        result = await client.update_collection(123, name="Updated Name")

        assert result is None

    @respx.mock
    async def test_delete_collection(self, client, base_url):
        """Test async delete collection."""
        respx.delete(f"{base_url.rstrip('/')}/collections/123").mock(
            return_value=Response(204)
        )

        await client.delete_collection(123)

    @respx.mock
    async def test_collections_context_manager(
        self, api_key, base_url, mock_collection
    ):
        """Test async collections with context manager."""
        respx.post(f"{base_url.rstrip('/')}/collections").mock(
            return_value=Response(200, json=mock_collection)
        )

        async with AsyncAlbertClient(api_key=api_key, base_url=base_url) as client:
            result = await client.create_collection(name="Test")
            assert isinstance(result, Collection)


class TestAsyncDocuments:
    """Test async documents methods."""

    @respx.mock
    async def test_upload_document(self, client, base_url, temp_file):
        """Test async upload document."""
        respx.post(f"{base_url.rstrip('/')}/documents").mock(
            return_value=Response(200, json={"id": 456})
        )

        result = await client.upload_document(file_path=temp_file, collection_id=123)

        assert isinstance(result, DocumentResponse)
        assert result.id == 456

    @respx.mock
    async def test_list_documents(self, client, base_url, mock_document):
        """Test async list documents."""
        respx.get(f"{base_url.rstrip('/')}/documents").mock(
            return_value=Response(200, json={"object": "list", "data": [mock_document]})
        )

        result = await client.list_documents()

        assert isinstance(result, DocumentList)
        assert len(result.data) == 1
        assert result.data[0].id == 456

    @respx.mock
    async def test_list_documents_by_collection(self, client, base_url, mock_document):
        """Test async list documents for specific collection."""
        mock_route = respx.get(f"{base_url.rstrip('/')}/documents").mock(
            return_value=Response(200, json={"object": "list", "data": [mock_document]})
        )

        result = await client.list_documents(collection_id=123)

        assert mock_route.calls.last.request.url.params.get("collection_id") == "123"
        assert isinstance(result, DocumentList)

    @respx.mock
    async def test_get_document(self, client, base_url, mock_document):
        """Test async get document."""
        respx.get(f"{base_url.rstrip('/')}/documents/456").mock(
            return_value=Response(200, json=mock_document)
        )

        result = await client.get_document(456)

        assert isinstance(result, Document)
        assert result.id == 456

    @respx.mock
    async def test_delete_document(self, client, base_url):
        """Test async delete document."""
        respx.delete(f"{base_url.rstrip('/')}/documents/456").mock(
            return_value=Response(204)
        )

        await client.delete_document(456)

    @respx.mock
    async def test_documents_context_manager(self, api_key, base_url, temp_file):
        """Test async documents with context manager."""
        respx.post(f"{base_url.rstrip('/')}/documents").mock(
            return_value=Response(200, json={"id": 456})
        )

        async with AsyncAlbertClient(api_key=api_key, base_url=base_url) as client:
            result = await client.upload_document(
                file_path=temp_file, collection_id=123
            )
            assert isinstance(result, DocumentResponse)


class TestAsyncChunks:
    """Test async chunks methods."""

    @respx.mock
    async def test_list_chunks(self, client, base_url, mock_chunk):
        """Test async list chunks."""
        respx.get(f"{base_url.rstrip('/')}/documents/456/chunks").mock(
            return_value=Response(200, json={"object": "list", "data": [mock_chunk]})
        )

        result = await client.list_chunks(document_id=456)

        assert isinstance(result, ChunkList)
        assert len(result.data) == 1
        assert result.data[0].id == 789

    @respx.mock
    async def test_get_chunk(self, client, base_url, mock_chunk):
        """Test async get chunk."""
        respx.get(f"{base_url.rstrip('/')}/documents/456/chunks/789").mock(
            return_value=Response(200, json=mock_chunk)
        )

        result = await client.get_chunk(document_id=456, chunk_id=789)

        assert isinstance(result, Chunk)
        assert result.id == 789
        assert "content of the chunk" in result.content

    @respx.mock
    async def test_chunks_context_manager(self, api_key, base_url, mock_chunk):
        """Test async chunks with context manager."""
        respx.get(f"{base_url.rstrip('/')}/documents/456/chunks/789").mock(
            return_value=Response(200, json=mock_chunk)
        )

        async with AsyncAlbertClient(api_key=api_key, base_url=base_url) as client:
            result = await client.get_chunk(document_id=456, chunk_id=789)
            assert isinstance(result, Chunk)
