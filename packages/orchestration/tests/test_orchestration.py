"""Tests for the orchestration package."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from orchestration import get_pipeline
from orchestration._base import RAGPipeline as RAGPipelineABC
from orchestration.albert import AlbertPipeline
from orchestration.basic import BasicPipeline


# ── ABC tests ──


class TestRAGPipelineABC:
    """Verify the abstract base class contract."""

    def test_cannot_instantiate_abc(self):
        """RAGPipeline is abstract and cannot be instantiated."""
        with pytest.raises(TypeError):
            RAGPipelineABC()

    def test_process_query_default_returns_empty(self):
        """Default process_query should return empty string."""

        class MinimalPipeline(RAGPipelineABC):
            def process_file(self, path, filename=None):
                return ""

            def process_bytes(self, data, filename):
                return ""

            @property
            def supported_extensions(self):
                return []

            @property
            def accepted_mime_types(self):
                return {}

        pipeline = MinimalPipeline()
        assert pipeline.process_query("test query") == ""


# ── Factory tests ──


class TestGetPipeline:
    """Verify pipeline factory selects the correct implementation."""

    def _make_config(self, storage_provider: str) -> MagicMock:
        config = MagicMock()
        config.storage.provider = storage_provider
        config.ingestion.provider = "local"
        return config

    @patch("ingestion.get_provider")
    def test_local_sqlite_returns_basic_pipeline(self, mock_get_provider):
        """local-sqlite config should return BasicPipeline."""
        mock_get_provider.return_value = MagicMock()
        config = self._make_config("local-sqlite")
        pipeline = get_pipeline(config)
        assert isinstance(pipeline, BasicPipeline)

    @patch("ingestion.get_provider")
    def test_albert_collections_returns_albert_pipeline(self, mock_get_provider):
        """albert-collections config should return AlbertPipeline."""
        mock_get_provider.return_value = MagicMock()
        config = self._make_config("albert-collections")
        pipeline = get_pipeline(config)
        assert isinstance(pipeline, AlbertPipeline)

    def test_unknown_backend_raises_value_error(self):
        """Unknown storage provider should raise ValueError."""
        config = self._make_config("unknown-backend")
        with pytest.raises(ValueError, match="Unknown storage backend"):
            get_pipeline(config)


# ── BasicPipeline tests ──


class TestBasicPipeline:
    """Verify BasicPipeline delegates to the ingestion provider."""

    @patch("ingestion.get_provider")
    def test_process_file_delegates_to_ingestion(self, mock_get_provider):
        """process_file should delegate to ingestion provider."""
        mock_provider = MagicMock()
        mock_provider.process_file.return_value = "parsed content"
        mock_get_provider.return_value = mock_provider

        pipeline = BasicPipeline()
        result = pipeline.process_file("/tmp/test.pdf", "test.pdf")

        assert result == "parsed content"
        mock_provider.process_file.assert_called_once_with("/tmp/test.pdf", "test.pdf")

    @patch("ingestion.get_provider")
    def test_process_bytes_delegates_to_ingestion(self, mock_get_provider):
        """process_bytes should delegate to ingestion provider."""
        mock_provider = MagicMock()
        mock_provider.process_bytes.return_value = "parsed bytes"
        mock_get_provider.return_value = mock_provider

        pipeline = BasicPipeline()
        result = pipeline.process_bytes(b"fake pdf data", "test.pdf")

        assert result == "parsed bytes"
        mock_provider.process_bytes.assert_called_once_with(
            b"fake pdf data", "test.pdf"
        )

    @patch("ingestion.get_provider")
    def test_process_query_returns_empty(self, mock_get_provider):
        """BasicPipeline should return empty string for queries (context stuffing)."""
        mock_get_provider.return_value = MagicMock()
        pipeline = BasicPipeline()
        assert pipeline.process_query("what is RAG?") == ""

    @patch("ingestion.get_provider")
    def test_supported_extensions_from_ingestion(self, mock_get_provider):
        """supported_extensions should come from the ingestion provider."""
        mock_provider = MagicMock()
        mock_provider.supported_extensions = [".pdf"]
        mock_get_provider.return_value = mock_provider

        pipeline = BasicPipeline()
        assert pipeline.supported_extensions == [".pdf"]

    @patch("ingestion.get_provider")
    def test_accepted_mime_types_from_ingestion(self, mock_get_provider):
        """accepted_mime_types should come from the ingestion provider."""
        mock_provider = MagicMock()
        mock_provider.accepted_mime_types = {"application/pdf": [".pdf"]}
        mock_get_provider.return_value = mock_provider

        pipeline = BasicPipeline()
        assert pipeline.accepted_mime_types == {"application/pdf": [".pdf"]}


# ── AlbertPipeline tests ──


class TestAlbertPipeline:
    """Verify AlbertPipeline delegates to ingestion and retrieval."""

    @patch("ingestion.get_provider")
    def test_process_file_delegates_to_ingestion(self, mock_get_provider):
        """process_file should delegate to Albert ingestion provider."""
        mock_provider = MagicMock()
        mock_provider.process_file.return_value = "albert parsed content"
        mock_get_provider.return_value = mock_provider

        pipeline = AlbertPipeline()
        result = pipeline.process_file("/tmp/test.pdf", "test.pdf")

        assert result == "albert parsed content"
        mock_provider.process_file.assert_called_once_with("/tmp/test.pdf", "test.pdf")

    @patch("ingestion.get_provider")
    def test_process_bytes_delegates_to_ingestion(self, mock_get_provider):
        """process_bytes should delegate to Albert ingestion provider."""
        mock_provider = MagicMock()
        mock_provider.process_bytes.return_value = "albert parsed bytes"
        mock_get_provider.return_value = mock_provider

        pipeline = AlbertPipeline()
        result = pipeline.process_bytes(b"fake data", "doc.pdf")

        assert result == "albert parsed bytes"
        mock_provider.process_bytes.assert_called_once_with(b"fake data", "doc.pdf")

    @patch("ingestion.get_provider")
    def test_process_query_delegates_to_retrieval(self, mock_get_provider):
        """process_query should delegate to retrieval.process_query."""
        mock_get_provider.return_value = MagicMock()
        pipeline = AlbertPipeline()

        with patch("retrieval.formatter.process_query") as mock_pq:
            mock_pq.return_value = "retrieved context"
            result = pipeline.process_query("what is RAG?", collection_ids=[1])

        assert result == "retrieved context"
        mock_pq.assert_called_once_with("what is RAG?", collection_ids=[1])

    @patch("ingestion.get_provider")
    def test_supported_extensions_from_ingestion(self, mock_get_provider):
        """supported_extensions should come from the Albert ingestion provider."""
        mock_provider = MagicMock()
        mock_provider.supported_extensions = [".pdf", ".json", ".md", ".html"]
        mock_get_provider.return_value = mock_provider

        pipeline = AlbertPipeline()
        assert pipeline.supported_extensions == [".pdf", ".json", ".md", ".html"]

    @patch("ingestion.get_provider")
    def test_accepted_mime_types_from_ingestion(self, mock_get_provider):
        """accepted_mime_types should come from the Albert ingestion provider."""
        mock_provider = MagicMock()
        mock_provider.accepted_mime_types = {
            "application/pdf": [".pdf"],
            "text/markdown": [".md"],
        }
        mock_get_provider.return_value = mock_provider

        pipeline = AlbertPipeline()
        assert pipeline.accepted_mime_types == {
            "application/pdf": [".pdf"],
            "text/markdown": [".md"],
        }

    @patch("ingestion.get_provider")
    def test_create_collection_delegates_to_retrieval(self, mock_get_provider):
        """create_collection should delegate to retrieval."""
        mock_get_provider.return_value = MagicMock()
        pipeline = AlbertPipeline()
        mock_client = MagicMock()

        with patch("retrieval.ingestion.create_collection") as mock_cc:
            mock_cc.return_value = 42
            result = pipeline.create_collection(mock_client, "test", "description")

        assert result == 42
        mock_cc.assert_called_once_with(mock_client, "test", "description")

    @patch("ingestion.get_provider")
    def test_ingest_documents_delegates_to_retrieval(self, mock_get_provider):
        """ingest_documents should delegate to retrieval."""
        mock_get_provider.return_value = MagicMock()
        pipeline = AlbertPipeline()
        mock_client = MagicMock()

        with patch("retrieval.ingestion.ingest_documents") as mock_id:
            mock_id.return_value = [1, 2, 3]
            result = pipeline.ingest_documents(
                mock_client, ["/tmp/a.pdf"], 42, chunk_size=256
            )

        assert result == [1, 2, 3]
        mock_id.assert_called_once_with(
            mock_client, ["/tmp/a.pdf"], 42, chunk_size=256, chunk_overlap=None
        )
