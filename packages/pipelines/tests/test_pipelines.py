"""Tests for the pipelines package."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from pipelines import get_pipeline
from pipelines._base import RAGPipeline as RAGPipelineABC
from pipelines.albert import AlbertPipeline
from pipelines.basic import BasicPipeline


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

    @patch("storage.get_provider")
    @patch("ingestion.get_provider")
    def test_albert_collections_returns_albert_pipeline(
        self, mock_get_ingestion, mock_get_storage
    ):
        """albert-collections config should return AlbertPipeline."""
        mock_get_ingestion.return_value = MagicMock()
        mock_get_storage.return_value = MagicMock()
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
    """Verify AlbertPipeline delegates to ingestion, retrieval, and storage."""

    @patch("storage.get_provider")
    @patch("ingestion.get_provider")
    def test_process_file_ingests_into_collection(
        self, mock_get_ingestion, mock_get_storage
    ):
        """process_file should upload to a session collection."""
        mock_storage = MagicMock()
        mock_storage.create_collection.return_value = 42
        mock_get_storage.return_value = mock_storage
        mock_get_ingestion.return_value = MagicMock()

        pipeline = AlbertPipeline()
        result = pipeline.process_file("/tmp/test.pdf", "test.pdf")

        assert result == "[Document indexed: test.pdf]"
        mock_storage.create_collection.assert_called_once()
        mock_storage.ingest_documents.assert_called_once()

    @patch("storage.get_provider")
    @patch("ingestion.get_provider")
    def test_process_bytes_ingests_into_collection(
        self, mock_get_ingestion, mock_get_storage
    ):
        """process_bytes should upload to a session collection."""
        mock_storage = MagicMock()
        mock_storage.create_collection.return_value = 42
        mock_get_storage.return_value = mock_storage
        mock_get_ingestion.return_value = MagicMock()

        pipeline = AlbertPipeline()
        result = pipeline.process_bytes(b"fake data", "doc.pdf")

        assert result == "[Document indexed: doc.pdf]"
        mock_storage.create_collection.assert_called_once()
        mock_storage.ingest_documents.assert_called_once()

    @patch("storage.get_provider")
    @patch("ingestion.get_provider")
    def test_process_query_orchestrates_search_rerank_format(
        self, mock_get_ingestion, mock_get_storage
    ):
        """process_query should orchestrate search → rerank → format."""
        mock_get_ingestion.return_value = MagicMock()
        mock_get_storage.return_value = MagicMock()
        pipeline = AlbertPipeline()

        mock_chunks = [{"content": "chunk1", "score": 0.9}]
        mock_reranked = [{"content": "chunk1", "score": 0.99}]

        with (
            patch("retrieval.search_chunks", return_value=mock_chunks) as mock_search,
            patch("reranking.rerank_chunks", return_value=mock_reranked) as mock_rerank,
            patch(
                "context.format_context", return_value="formatted context"
            ) as mock_format,
            patch("rag_core.get_config") as mock_get_config,
        ):
            mock_config = MagicMock()
            mock_config.retrieval.top_k = 10
            mock_config.retrieval.strategy = "hybrid"
            mock_config.retrieval.score_threshold = 0.0
            mock_config.reranking.enabled = True
            mock_config.reranking.model = "openweight-rerank"
            mock_config.reranking.top_n = 3
            mock_get_config.return_value = mock_config

            mock_client = MagicMock()
            result = pipeline.process_query(
                "what is RAG?", collection_ids=[1], client=mock_client
            )

        assert result == "formatted context"
        mock_search.assert_called_once()
        mock_rerank.assert_called_once()
        mock_format.assert_called_once_with(mock_reranked)

    @patch("storage.get_provider")
    @patch("ingestion.get_provider")
    def test_process_query_skips_rerank_when_disabled(
        self, mock_get_ingestion, mock_get_storage
    ):
        """process_query should skip reranking when config disables it."""
        mock_get_ingestion.return_value = MagicMock()
        mock_get_storage.return_value = MagicMock()
        pipeline = AlbertPipeline()

        mock_chunks = [{"content": "chunk1", "score": 0.9}]

        with (
            patch("retrieval.search_chunks", return_value=mock_chunks),
            patch("reranking.rerank_chunks") as mock_rerank,
            patch(
                "context.format_context", return_value="formatted context"
            ) as mock_format,
            patch("rag_core.get_config") as mock_get_config,
        ):
            mock_config = MagicMock()
            mock_config.retrieval.top_k = 10
            mock_config.retrieval.strategy = "hybrid"
            mock_config.retrieval.score_threshold = 0.0
            mock_config.reranking.enabled = False
            mock_get_config.return_value = mock_config

            mock_client = MagicMock()
            pipeline.process_query(
                "what is RAG?", collection_ids=[1], client=mock_client
            )

        mock_rerank.assert_not_called()
        mock_format.assert_called_once_with(mock_chunks)

    @patch("storage.get_provider")
    @patch("ingestion.get_provider")
    def test_process_query_returns_empty_when_no_results(
        self, mock_get_ingestion, mock_get_storage
    ):
        """process_query should return empty string when search finds nothing."""
        mock_get_ingestion.return_value = MagicMock()
        mock_get_storage.return_value = MagicMock()
        pipeline = AlbertPipeline()

        with (
            patch("retrieval.search_chunks", return_value=[]),
            patch("rag_core.get_config") as mock_get_config,
        ):
            mock_config = MagicMock()
            mock_config.retrieval.top_k = 10
            mock_config.retrieval.strategy = "hybrid"
            mock_config.retrieval.score_threshold = 0.0
            mock_get_config.return_value = mock_config

            mock_client = MagicMock()
            result = pipeline.process_query(
                "nonexistent", collection_ids=[1], client=mock_client
            )

        assert result == ""

    @patch("storage.get_provider")
    @patch("ingestion.get_provider")
    def test_supported_extensions_from_ingestion(
        self, mock_get_ingestion, mock_get_storage
    ):
        """supported_extensions should come from the Albert ingestion provider."""
        expected_extensions = [".pdf", ".md", ".html"]
        mock_provider = MagicMock()
        mock_provider.supported_extensions = expected_extensions
        mock_get_ingestion.return_value = mock_provider
        mock_get_storage.return_value = MagicMock()

        pipeline = AlbertPipeline()
        assert pipeline.supported_extensions == expected_extensions

    @patch("storage.get_provider")
    @patch("ingestion.get_provider")
    def test_accepted_mime_types_from_ingestion(
        self, mock_get_ingestion, mock_get_storage
    ):
        """accepted_mime_types should come from the Albert ingestion provider."""
        mock_provider = MagicMock()
        mock_provider.accepted_mime_types = {
            "application/pdf": [".pdf"],
            "text/markdown": [".md"],
        }
        mock_get_ingestion.return_value = mock_provider
        mock_get_storage.return_value = MagicMock()

        pipeline = AlbertPipeline()
        assert pipeline.accepted_mime_types == {
            "application/pdf": [".pdf"],
            "text/markdown": [".md"],
        }

    @patch("storage.get_provider")
    @patch("ingestion.get_provider")
    def test_process_query_uses_config_collections(
        self, mock_get_ingestion, mock_get_storage
    ):
        """process_query should search config collections when no session collection exists."""
        mock_get_ingestion.return_value = MagicMock()
        mock_get_storage.return_value = MagicMock()
        pipeline = AlbertPipeline()

        mock_chunks = [{"content": "chunk1", "score": 0.9}]

        with (
            patch("retrieval.search_chunks", return_value=mock_chunks) as mock_search,
            patch("context.format_context", return_value="context"),
            patch("rag_core.get_config") as mock_get_config,
        ):
            mock_config = MagicMock()
            mock_config.storage.collections = [42, 87]
            mock_config.retrieval.top_k = 10
            mock_config.retrieval.strategy = "hybrid"
            mock_config.retrieval.score_threshold = 0.0
            mock_config.reranking.enabled = False
            mock_get_config.return_value = mock_config

            mock_client = MagicMock()
            pipeline._client = mock_client
            result = pipeline.process_query("what is RAG?")

        assert result == "context"
        # Should search the configured collections
        call_args = mock_search.call_args
        assert call_args[0][2] == [42, 87]  # collection_ids

    @patch("storage.get_provider")
    @patch("ingestion.get_provider")
    def test_process_query_merges_config_and_session_collections(
        self, mock_get_ingestion, mock_get_storage
    ):
        """process_query should merge config collections with session collection."""
        mock_get_ingestion.return_value = MagicMock()
        mock_get_storage.return_value = MagicMock()
        pipeline = AlbertPipeline()
        pipeline._collection_id = 999  # Simulate a session collection

        mock_chunks = [{"content": "chunk1", "score": 0.9}]

        with (
            patch("retrieval.search_chunks", return_value=mock_chunks) as mock_search,
            patch("context.format_context", return_value="context"),
            patch("rag_core.get_config") as mock_get_config,
        ):
            mock_config = MagicMock()
            mock_config.storage.collections = [42, 87]
            mock_config.retrieval.top_k = 10
            mock_config.retrieval.strategy = "hybrid"
            mock_config.retrieval.score_threshold = 0.0
            mock_config.reranking.enabled = False
            mock_get_config.return_value = mock_config

            mock_client = MagicMock()
            pipeline._client = mock_client
            pipeline.process_query("test query")

        # Should include both config collections AND session collection
        call_args = mock_search.call_args
        assert set(call_args[0][2]) == {42, 87, 999}

    @patch("storage.get_provider")
    @patch("ingestion.get_provider")
    def test_process_query_returns_empty_when_no_collections(
        self, mock_get_ingestion, mock_get_storage
    ):
        """process_query should return empty when no config or session collections."""
        mock_get_ingestion.return_value = MagicMock()
        mock_get_storage.return_value = MagicMock()
        pipeline = AlbertPipeline()

        with patch("rag_core.get_config") as mock_get_config:
            mock_config = MagicMock()
            mock_config.storage.collections = []
            mock_get_config.return_value = mock_config

            mock_client = MagicMock()
            pipeline._client = mock_client
            result = pipeline.process_query("test query")

        assert result == ""

    @patch("storage.get_provider")
    @patch("ingestion.get_provider")
    def test_process_query_session_only_when_no_config_collections(
        self, mock_get_ingestion, mock_get_storage
    ):
        """process_query should use only session collection when config has no collections."""
        mock_get_ingestion.return_value = MagicMock()
        mock_get_storage.return_value = MagicMock()
        pipeline = AlbertPipeline()
        pipeline._collection_id = 555

        mock_chunks = [{"content": "chunk1", "score": 0.9}]

        with (
            patch("retrieval.search_chunks", return_value=mock_chunks) as mock_search,
            patch("context.format_context", return_value="context"),
            patch("rag_core.get_config") as mock_get_config,
        ):
            mock_config = MagicMock()
            mock_config.storage.collections = []
            mock_config.retrieval.top_k = 10
            mock_config.retrieval.strategy = "hybrid"
            mock_config.retrieval.score_threshold = 0.0
            mock_config.reranking.enabled = False
            mock_get_config.return_value = mock_config

            mock_client = MagicMock()
            pipeline._client = mock_client
            pipeline.process_query("test query")

        # Should use only the session collection
        call_args = mock_search.call_args
        assert call_args[0][2] == [555]

    @patch("storage.get_provider")
    @patch("ingestion.get_provider")
    def test_create_collection_delegates_to_storage(
        self, mock_get_ingestion, mock_get_storage
    ):
        """create_collection should delegate to storage provider."""
        mock_get_ingestion.return_value = MagicMock()
        mock_storage = MagicMock()
        mock_storage.create_collection.return_value = 42
        mock_get_storage.return_value = mock_storage

        pipeline = AlbertPipeline()
        mock_client = MagicMock()
        result = pipeline.create_collection(mock_client, "test", "description")

        assert result == 42
        mock_storage.create_collection.assert_called_once_with(
            mock_client, "test", "description"
        )

    @patch("storage.get_provider")
    @patch("ingestion.get_provider")
    def test_ingest_documents_delegates_to_storage(
        self, mock_get_ingestion, mock_get_storage
    ):
        """ingest_documents should delegate to storage provider."""
        mock_get_ingestion.return_value = MagicMock()
        mock_storage = MagicMock()
        mock_storage.ingest_documents.return_value = [1, 2, 3]
        mock_get_storage.return_value = mock_storage

        pipeline = AlbertPipeline()
        mock_client = MagicMock()
        result = pipeline.ingest_documents(
            mock_client, ["/tmp/a.pdf"], 42, chunk_size=256
        )

        assert result == [1, 2, 3]
        mock_storage.ingest_documents.assert_called_once_with(
            mock_client, ["/tmp/a.pdf"], 42, chunk_size=256, chunk_overlap=None
        )
