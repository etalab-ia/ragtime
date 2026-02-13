"""Tests for ingestion functions."""

import pytest
import respx
from httpx import Response

from retrieval_albert import create_collection, delete_collection, ingest_documents


class TestCreateCollection:
    """Tests for create_collection function."""

    @respx.mock
    def test_creates_collection(self, client, base_url):
        """Should create a collection and return its ID."""
        respx.post(f"{base_url.rstrip('/')}/collections").mock(
            return_value=Response(
                200,
                json={
                    "object": "collection",
                    "id": 42,
                    "name": "test-collection",
                    "description": "A test collection",
                    "visibility": "private",
                    "owner": "test-user",
                    "created": 1700000000,
                    "updated": 1700000000,
                },
            )
        )

        result = create_collection(client, "test-collection", "A test collection")

        assert result == 42

    @respx.mock
    def test_creates_collection_without_description(self, client, base_url):
        """Should create a collection with empty description."""
        respx.post(f"{base_url.rstrip('/')}/collections").mock(
            return_value=Response(
                200,
                json={
                    "object": "collection",
                    "id": 7,
                    "name": "minimal",
                    "description": "",
                    "visibility": "private",
                    "owner": "test-user",
                    "created": 1700000000,
                    "updated": 1700000000,
                },
            )
        )

        result = create_collection(client, "minimal")

        assert result == 7


class TestIngestDocuments:
    """Tests for ingest_documents function."""

    @respx.mock
    def test_uploads_documents_with_config_defaults(
        self, client, base_url, mock_config, tmp_path
    ):
        """Should upload documents using chunk size/overlap from config."""
        # Create a test file
        test_file = tmp_path / "test.txt"
        test_file.write_text("Hello world")

        mock_route = respx.post(f"{base_url.rstrip('/')}/documents").mock(
            return_value=Response(200, json={"id": 100})
        )

        result = ingest_documents(client, [test_file], collection_id=42)

        assert result == [100]
        assert mock_route.called

    @respx.mock
    def test_uploads_multiple_documents(self, client, base_url, mock_config, tmp_path):
        """Should upload multiple documents and return all IDs."""
        files = []
        for i in range(3):
            f = tmp_path / f"doc{i}.txt"
            f.write_text(f"Document {i}")
            files.append(f)

        call_count = 0

        def respond(request):
            nonlocal call_count
            call_count += 1
            return Response(200, json={"id": 200 + call_count})

        respx.post(f"{base_url.rstrip('/')}/documents").mock(side_effect=respond)

        result = ingest_documents(client, files, collection_id=1)

        assert len(result) == 3
        assert result == [201, 202, 203]

    @respx.mock
    def test_overrides_chunk_size(self, client, base_url, mock_config, tmp_path):
        """Should accept explicit chunk_size override."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("Content")

        respx.post(f"{base_url.rstrip('/')}/documents").mock(
            return_value=Response(200, json={"id": 1})
        )

        result = ingest_documents(
            client, [test_file], collection_id=1, chunk_size=1024, chunk_overlap=100
        )

        assert result == [1]

    @respx.mock
    def test_upload_failure_raises(self, client, base_url, mock_config, tmp_path):
        """Should raise on upload failure."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("Content")

        respx.post(f"{base_url.rstrip('/')}/documents").mock(
            return_value=Response(500, json={"error": "Internal server error"})
        )

        with pytest.raises(Exception):
            ingest_documents(client, [test_file], collection_id=1)


class TestDeleteCollection:
    """Tests for delete_collection function."""

    @respx.mock
    def test_deletes_collection(self, client, base_url):
        """Should delete a collection by ID."""
        mock_route = respx.delete(f"{base_url.rstrip('/')}/collections/42").mock(
            return_value=Response(204)
        )

        delete_collection(client, 42)

        assert mock_route.called

    @respx.mock
    def test_delete_nonexistent_raises(self, client, base_url):
        """Should raise on 404."""
        respx.delete(f"{base_url.rstrip('/')}/collections/999").mock(
            return_value=Response(404, json={"error": "Not found"})
        )

        with pytest.raises(Exception):
            delete_collection(client, 999)
