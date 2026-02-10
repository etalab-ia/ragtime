"""Tests for collections functionality."""

import pytest
import respx
from httpx import Response

from albert import AlbertClient, Collection, CollectionList


@pytest.fixture
def client(api_key, base_url):
    """Create test client."""
    return AlbertClient(api_key=api_key, base_url=base_url)


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
def mock_collection_list(mock_collection):
    """Mock collection list data."""
    return {
        "object": "list",
        "data": [
            mock_collection,
            {
                **mock_collection,
                "id": 456,
                "name": "Another Collection",
                "visibility": "public",
            },
        ],
    }


class TestCreateCollection:
    """Test create_collection method."""

    @respx.mock
    def test_create_collection_minimal(self, client, base_url, mock_collection):
        """Test creating collection with minimal parameters."""
        respx.post(f"{base_url.rstrip('/')}/collections").mock(
            return_value=Response(200, json=mock_collection)
        )

        result = client.create_collection(name="Test Collection")

        assert isinstance(result, Collection)
        assert result.id == 123
        assert result.name == "Test Collection"
        assert result.visibility == "private"

    @respx.mock
    def test_create_collection_with_all_parameters(
        self, client, base_url, mock_collection
    ):
        """Test creating collection with all parameters."""
        mock_route = respx.post(f"{base_url.rstrip('/')}/collections").mock(
            return_value=Response(200, json=mock_collection)
        )

        result = client.create_collection(
            name="Test Collection",
            description="A test collection",
            visibility="public",
        )

        # Verify request body
        request_body = mock_route.calls.last.request.content.decode()
        assert "Test Collection" in request_body
        assert "A test collection" in request_body
        assert "public" in request_body

        assert isinstance(result, Collection)
        assert result.description == "A test collection"

    @respx.mock
    def test_create_collection_http_error(self, client, base_url):
        """Test create collection with HTTP error."""
        respx.post(f"{base_url.rstrip('/')}/collections").mock(
            return_value=Response(
                400, json={"error": {"message": "Invalid collection name"}}
            )
        )

        with pytest.raises(Exception):  # httpx.HTTPStatusError
            client.create_collection(name="")


class TestListCollections:
    """Test list_collections method."""

    @respx.mock
    def test_list_collections(self, client, base_url, mock_collection_list):
        """Test listing all collections."""
        respx.get(f"{base_url.rstrip('/')}/collections").mock(
            return_value=Response(200, json=mock_collection_list)
        )

        result = client.list_collections()

        assert isinstance(result, CollectionList)
        assert result.object == "list"
        assert len(result.data) == 2
        assert result.data[0].id == 123
        assert result.data[1].id == 456

    @respx.mock
    def test_list_collections_empty(self, client, base_url):
        """Test listing collections when none exist."""
        respx.get(f"{base_url.rstrip('/')}/collections").mock(
            return_value=Response(200, json={"object": "list", "data": []})
        )

        result = client.list_collections()

        assert isinstance(result, CollectionList)
        assert len(result.data) == 0


class TestGetCollection:
    """Test get_collection method."""

    @respx.mock
    def test_get_collection(self, client, base_url, mock_collection):
        """Test getting a specific collection."""
        respx.get(f"{base_url.rstrip('/')}/collections/123").mock(
            return_value=Response(200, json=mock_collection)
        )

        result = client.get_collection(123)

        assert isinstance(result, Collection)
        assert result.id == 123
        assert result.name == "Test Collection"
        assert result.documents == 5

    @respx.mock
    def test_get_collection_not_found(self, client, base_url):
        """Test getting non-existent collection."""
        respx.get(f"{base_url.rstrip('/')}/collections/999").mock(
            return_value=Response(404, json={"error": {"message": "Not found"}})
        )

        with pytest.raises(Exception):  # httpx.HTTPStatusError
            client.get_collection(999)


class TestUpdateCollection:
    """Test update_collection method."""

    @respx.mock
    def test_update_collection_name(self, client, base_url, mock_collection):
        """Test updating collection name."""
        updated_collection = {**mock_collection, "name": "Updated Name"}

        mock_route = respx.patch(f"{base_url.rstrip('/')}/collections/123").mock(
            return_value=Response(200, json=updated_collection)
        )

        result = client.update_collection(123, name="Updated Name")

        # Verify request body only contains name
        request_body = mock_route.calls.last.request.content.decode()
        assert "Updated Name" in request_body

        assert isinstance(result, Collection)
        assert result.name == "Updated Name"

    @respx.mock
    def test_update_collection_multiple_fields(self, client, base_url, mock_collection):
        """Test updating multiple collection fields."""
        updated = {
            **mock_collection,
            "name": "New Name",
            "description": "New Description",
            "visibility": "public",
        }

        respx.patch(f"{base_url.rstrip('/')}/collections/123").mock(
            return_value=Response(200, json=updated)
        )

        result = client.update_collection(
            123, name="New Name", description="New Description", visibility="public"
        )

        assert result.name == "New Name"
        assert result.description == "New Description"
        assert result.visibility == "public"

    @respx.mock
    def test_update_collection_http_error(self, client, base_url):
        """Test update collection with permission error."""
        respx.patch(f"{base_url.rstrip('/')}/collections/123").mock(
            return_value=Response(403, json={"error": {"message": "Forbidden"}})
        )

        with pytest.raises(Exception):  # httpx.HTTPStatusError
            client.update_collection(123, name="New Name")


class TestDeleteCollection:
    """Test delete_collection method."""

    @respx.mock
    def test_delete_collection(self, client, base_url):
        """Test deleting a collection."""
        respx.delete(f"{base_url.rstrip('/')}/collections/123").mock(
            return_value=Response(204)
        )

        # Should not raise
        client.delete_collection(123)

    @respx.mock
    def test_delete_collection_not_found(self, client, base_url):
        """Test deleting non-existent collection."""
        respx.delete(f"{base_url.rstrip('/')}/collections/999").mock(
            return_value=Response(404, json={"error": {"message": "Not found"}})
        )

        with pytest.raises(Exception):  # httpx.HTTPStatusError
            client.delete_collection(999)
