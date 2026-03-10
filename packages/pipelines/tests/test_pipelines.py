"""Tests for the unified RAGPipeline."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from rag_facile.ingestion import IngestionProvider
from rag_facile.pipelines import get_pipeline
from rag_facile.pipelines._base import RAGPipeline
from rag_facile.reranking import RerankingProvider
from rag_facile.retrieval import RetrievalProvider
from rag_facile.storage import StorageProvider


# ── Helpers ──


def _make_mock_ingestion(
    extensions=None,
    mime_types=None,
    process_file_result="parsed content",
    process_bytes_result="parsed bytes",
) -> MagicMock:
    mock = MagicMock(spec=IngestionProvider)
    mock.supported_extensions = extensions or [".pdf"]
    mock.accepted_mime_types = mime_types or {"application/pdf": [".pdf"]}
    mock.process_file.return_value = process_file_result
    mock.process_bytes.return_value = process_bytes_result
    return mock


def _make_mock_storage(collection_id=42) -> MagicMock:
    mock = MagicMock(spec=StorageProvider)
    mock.create_collection.return_value = collection_id
    mock.ingest_documents.return_value = [1, 2]
    return mock


def _make_mock_retrieval(chunks=None) -> MagicMock:
    mock = MagicMock(spec=RetrievalProvider)
    mock.search.return_value = chunks or []
    return mock


def _make_mock_reranking(chunks=None) -> MagicMock:
    mock = MagicMock(spec=RerankingProvider)
    mock.rerank.return_value = chunks or []
    return mock


# ── Pipeline construction ──


class TestRAGPipelineConstruction:
    """Verify RAGPipeline can be built with any provider combination."""

    def test_with_all_providers(self):
        """Should accept all providers without error."""
        pipeline = RAGPipeline(
            ingestion=_make_mock_ingestion(),
            storage=_make_mock_storage(),
            retrieval=_make_mock_retrieval(),
            reranking=_make_mock_reranking(),
        )
        assert pipeline.supported_extensions == [".pdf"]

    def test_with_ingestion_only(self):
        """Should work with just an ingestion provider (context stuffing mode)."""
        pipeline = RAGPipeline(ingestion=_make_mock_ingestion())
        assert pipeline._storage is None
        assert pipeline._retrieval is None
        assert pipeline._reranking is None

    def test_capabilities_from_ingestion(self):
        """supported_extensions and accepted_mime_types come from ingestion."""
        mock_ingestion = _make_mock_ingestion(
            extensions=[".pdf", ".md"],
            mime_types={"application/pdf": [".pdf"], "text/markdown": [".md"]},
        )
        pipeline = RAGPipeline(ingestion=mock_ingestion)
        assert pipeline.supported_extensions == [".pdf", ".md"]
        assert "text/markdown" in pipeline.accepted_mime_types


# ── process_file with storage ──


class TestProcessFileWithStorage:
    """Verify process_file uploads to storage when provider is set."""

    def _make_pipeline_with_storage(self, collection_id=42) -> tuple:
        """Make a pipeline with a mock storage provider and a mocked Albert client."""
        mock_storage = _make_mock_storage(collection_id=collection_id)
        pipeline = RAGPipeline(
            ingestion=_make_mock_ingestion(),
            storage=mock_storage,
        )
        # Inject a mock client so no real AlbertClient is created
        pipeline._storage_client = MagicMock()
        return pipeline, mock_storage

    def test_creates_session_collection_on_first_file(self):
        """First file upload should create a session collection."""
        pipeline, mock_storage = self._make_pipeline_with_storage(collection_id=99)

        result = pipeline.process_file("/tmp/test.pdf", "test.pdf")

        assert result == "[Document indexed: test.pdf]"
        mock_storage.create_collection.assert_called_once()
        mock_storage.ingest_documents.assert_called_once()

    def test_reuses_collection_for_subsequent_files(self):
        """Subsequent file uploads should reuse the same collection."""
        pipeline, mock_storage = self._make_pipeline_with_storage(collection_id=77)

        pipeline.process_file("/tmp/a.pdf")
        pipeline.process_file("/tmp/b.pdf")

        # Collection created once, ingest called twice
        assert mock_storage.create_collection.call_count == 1
        assert mock_storage.ingest_documents.call_count == 2

    def test_process_bytes_ingests_into_collection(self):
        """process_bytes should upload to the session collection."""
        pipeline, mock_storage = self._make_pipeline_with_storage(collection_id=42)

        result = pipeline.process_bytes(b"fake data", "doc.pdf")

        assert result == "[Document indexed: doc.pdf]"
        mock_storage.create_collection.assert_called_once()
        mock_storage.ingest_documents.assert_called_once()


# ── process_file without storage (context stuffing) ──


class TestProcessFileWithoutStorage:
    """Verify process_file falls back to local parsing when storage=None."""

    def test_delegates_to_ingestion(self):
        """process_file should use ingestion provider when storage is None."""
        from pathlib import Path

        mock_ingestion = _make_mock_ingestion(process_file_result="full text")
        pipeline = RAGPipeline(ingestion=mock_ingestion)

        result = pipeline.process_file("/tmp/test.pdf", "test.pdf")

        assert result == "full text"
        mock_ingestion.process_file.assert_called_once_with(
            Path("/tmp/test.pdf"), "test.pdf"
        )

    def test_process_bytes_delegates_to_ingestion(self):
        """process_bytes should use ingestion provider when storage is None."""
        mock_ingestion = _make_mock_ingestion(process_bytes_result="bytes text")
        pipeline = RAGPipeline(ingestion=mock_ingestion)

        result = pipeline.process_bytes(b"raw bytes", "doc.pdf")

        assert result == "bytes text"
        mock_ingestion.process_bytes.assert_called_once_with(b"raw bytes", "doc.pdf")


# ── process_query with retrieval ──


class TestProcessQueryWithRetrieval:
    """Verify process_query orchestrates retrieval → rerank → format."""

    def test_returns_formatted_context(self):
        """process_query should search, rerank, and format context."""
        mock_chunks = [{"content": "chunk1", "score": 0.9}]
        mock_reranked = [{"content": "chunk1", "score": 0.99}]
        mock_retrieval = _make_mock_retrieval(chunks=mock_chunks)
        mock_reranking = _make_mock_reranking(chunks=mock_reranked)

        pipeline = RAGPipeline(
            ingestion=_make_mock_ingestion(),
            retrieval=mock_retrieval,
            reranking=mock_reranking,
        )
        pipeline._collection_id = 1  # Simulate an active session collection

        with (
            patch(
                "rag_facile.context.format_context", return_value="formatted context"
            ) as mock_format,
            patch("rag_facile.core.get_config") as mock_get_config,
        ):
            mock_config = MagicMock()
            mock_config.storage.collections = []
            mock_config.generation.model = "openweight-medium"
            mock_config.generation.temperature = 0.2
            mock_get_config.return_value = mock_config

            result = pipeline.process_query("what is RAG?")

        assert result == "formatted context"
        mock_retrieval.search.assert_called_once()
        mock_reranking.rerank.assert_called_once()
        mock_format.assert_called_once_with(mock_reranked)

    def test_skips_rerank_when_reranking_is_none(self):
        """process_query should skip reranking when reranking=None."""
        mock_chunks = [{"content": "chunk1", "score": 0.9}]
        mock_retrieval = _make_mock_retrieval(chunks=mock_chunks)

        pipeline = RAGPipeline(
            ingestion=_make_mock_ingestion(),
            retrieval=mock_retrieval,
            reranking=None,
        )
        pipeline._collection_id = 1

        with (
            patch(
                "rag_facile.context.format_context", return_value="formatted context"
            ) as mock_format,
            patch("rag_facile.core.get_config") as mock_get_config,
        ):
            mock_config = MagicMock()
            mock_config.storage.collections = []
            mock_config.generation.model = "openweight-medium"
            mock_config.generation.temperature = 0.2
            mock_get_config.return_value = mock_config

            result = pipeline.process_query("what is RAG?")

        assert result == "formatted context"
        mock_format.assert_called_once_with(mock_chunks)  # Unranked chunks

    def test_returns_empty_when_no_results(self):
        """process_query should return empty string when search finds nothing."""
        mock_retrieval = _make_mock_retrieval(chunks=[])

        pipeline = RAGPipeline(
            ingestion=_make_mock_ingestion(),
            retrieval=mock_retrieval,
        )
        pipeline._collection_id = 1

        with patch("rag_facile.core.get_config") as mock_get_config:
            mock_config = MagicMock()
            mock_config.storage.collections = []
            mock_get_config.return_value = mock_config

            result = pipeline.process_query("nonexistent")

        assert result == ""

    def test_uses_config_collections_when_no_session_collection(self):
        """process_query should search config collections when no session exists."""
        mock_chunks = [{"content": "chunk1", "score": 0.9}]
        mock_retrieval = _make_mock_retrieval(chunks=mock_chunks)

        pipeline = RAGPipeline(
            ingestion=_make_mock_ingestion(),
            retrieval=mock_retrieval,
        )
        # No _collection_id set (no file was uploaded this session)

        with (
            patch("rag_facile.context.format_context", return_value="context"),
            patch("rag_facile.core.get_config") as mock_get_config,
        ):
            mock_config = MagicMock()
            mock_config.storage.collections = [42, 87]
            mock_config.generation.model = "openweight-medium"
            mock_config.generation.temperature = 0.2
            mock_get_config.return_value = mock_config

            result = pipeline.process_query("test")

        assert result == "context"
        call_args = mock_retrieval.search.call_args
        assert set(call_args[0][1]) == {42, 87}

    def test_merges_config_and_session_collections(self):
        """process_query should merge config collections with session collection."""
        mock_chunks = [{"content": "chunk1", "score": 0.9}]
        mock_retrieval = _make_mock_retrieval(chunks=mock_chunks)

        pipeline = RAGPipeline(
            ingestion=_make_mock_ingestion(),
            retrieval=mock_retrieval,
        )
        pipeline._collection_id = 999  # Active session collection

        with (
            patch("rag_facile.context.format_context", return_value="context"),
            patch("rag_facile.core.get_config") as mock_get_config,
        ):
            mock_config = MagicMock()
            mock_config.storage.collections = [42, 87]
            mock_config.generation.model = "openweight-medium"
            mock_config.generation.temperature = 0.2
            mock_get_config.return_value = mock_config

            pipeline.process_query("test")

        call_args = mock_retrieval.search.call_args
        assert set(call_args[0][1]) == {42, 87, 999}

    def test_returns_empty_when_no_collections(self):
        """process_query should return empty when no collections to search."""
        mock_retrieval = _make_mock_retrieval()

        pipeline = RAGPipeline(
            ingestion=_make_mock_ingestion(),
            retrieval=mock_retrieval,
        )
        # No session collection, no config collections

        with patch("rag_facile.core.get_config") as mock_get_config:
            mock_config = MagicMock()
            mock_config.storage.collections = []
            mock_get_config.return_value = mock_config

            result = pipeline.process_query("test")

        assert result == ""
        mock_retrieval.search.assert_not_called()


# ── process_query without retrieval ──


class TestProcessQueryWithoutRetrieval:
    """Verify process_query returns empty string when retrieval=None."""

    def test_returns_empty_string(self):
        """process_query should return '' when no retrieval provider is set."""
        pipeline = RAGPipeline(ingestion=_make_mock_ingestion())
        result = pipeline.process_query("any query")
        assert result == ""

    def test_retrieve_chunks_returns_empty_list(self):
        """retrieve_chunks should return [] when no retrieval provider is set."""
        pipeline = RAGPipeline(ingestion=_make_mock_ingestion())
        result = pipeline.retrieve_chunks("any query")
        assert result == []


# ── retrieve_chunks ──


class TestRetrieveChunks:
    """Verify retrieve_chunks returns raw chunks for evaluation use."""

    def test_returns_raw_chunks(self):
        """retrieve_chunks should return raw chunks without formatting."""
        mock_chunks = [{"content": "chunk1", "score": 0.9}]
        mock_retrieval = _make_mock_retrieval(chunks=mock_chunks)

        pipeline = RAGPipeline(
            ingestion=_make_mock_ingestion(),
            retrieval=mock_retrieval,
        )
        pipeline._collection_id = 1

        with patch("rag_facile.core.get_config") as mock_get_config:
            mock_config = MagicMock()
            mock_config.storage.collections = []
            mock_get_config.return_value = mock_config

            chunks = pipeline.retrieve_chunks("test query")

        assert chunks == mock_chunks


# ── Factory ──


class TestGetPipeline:
    """Verify get_pipeline wires the correct providers from config."""

    def _make_config(
        self,
        storage_provider="albert-collections",
        retrieval_provider="albert",
        reranking_enabled=True,
        reranking_provider="albert",
        query_strategy="none",
        ingestion_provider="albert",
    ) -> MagicMock:
        config = MagicMock()
        config.storage.provider = storage_provider
        config.storage.collections = []
        config.ingestion.provider = ingestion_provider
        config.retrieval.provider = retrieval_provider
        config.retrieval.strategy = "hybrid"
        config.retrieval.top_k = 10
        config.retrieval.score_threshold = 0.0
        config.reranking.enabled = reranking_enabled
        config.reranking.provider = reranking_provider
        config.reranking.model = "openweight-rerank"
        config.reranking.top_n = 5
        config.query.strategy = query_strategy
        return config

    @patch("rag_facile.reranking.get_provider")
    @patch("rag_facile.retrieval.get_provider")
    @patch("rag_facile.storage.get_provider")
    @patch("rag_facile.ingestion.get_provider")
    def test_albert_storage_wires_all_providers(
        self,
        mock_get_ingestion,
        mock_get_storage,
        mock_get_retrieval,
        mock_get_reranking,
    ):
        """albert-collections config should wire all providers."""
        mock_get_ingestion.return_value = MagicMock(spec=IngestionProvider)
        mock_get_storage.return_value = MagicMock(spec=StorageProvider)
        mock_get_retrieval.return_value = MagicMock(spec=RetrievalProvider)
        mock_get_reranking.return_value = MagicMock(spec=RerankingProvider)

        config = self._make_config()
        pipeline = get_pipeline(config)

        assert isinstance(pipeline, RAGPipeline)
        assert pipeline._storage is not None
        assert pipeline._retrieval is not None
        assert pipeline._reranking is not None

    @patch("rag_facile.retrieval.get_provider", return_value=None)
    @patch("rag_facile.ingestion.get_provider")
    def test_local_sqlite_has_no_storage(self, mock_get_ingestion, mock_get_retrieval):
        """local-sqlite config should result in storage=None."""
        mock_get_ingestion.return_value = MagicMock(spec=IngestionProvider)

        config = self._make_config(storage_provider="local-sqlite")
        pipeline = get_pipeline(config)

        assert pipeline._storage is None

    @patch("rag_facile.reranking.get_provider")
    @patch("rag_facile.retrieval.get_provider")
    @patch("rag_facile.storage.get_provider")
    @patch("rag_facile.ingestion.get_provider")
    def test_retrieval_none_provider(
        self,
        mock_get_ingestion,
        mock_get_storage,
        mock_get_retrieval,
        mock_get_reranking,
    ):
        """retrieval.provider='none' should result in retrieval=None."""
        mock_get_ingestion.return_value = MagicMock(spec=IngestionProvider)
        mock_get_storage.return_value = MagicMock(spec=StorageProvider)
        mock_get_retrieval.return_value = None  # "none" provider
        mock_get_reranking.return_value = None

        config = self._make_config(retrieval_provider="none", reranking_enabled=False)
        pipeline = get_pipeline(config)

        assert pipeline._retrieval is None

    @patch("rag_facile.reranking.get_provider")
    @patch("rag_facile.retrieval.get_provider")
    @patch("rag_facile.storage.get_provider")
    @patch("rag_facile.ingestion.get_provider")
    def test_disabled_reranking_results_in_none(
        self,
        mock_get_ingestion,
        mock_get_storage,
        mock_get_retrieval,
        mock_get_reranking,
    ):
        """reranking.enabled=False should result in reranking=None."""
        mock_get_ingestion.return_value = MagicMock(spec=IngestionProvider)
        mock_get_storage.return_value = MagicMock(spec=StorageProvider)
        mock_get_retrieval.return_value = MagicMock(spec=RetrievalProvider)
        mock_get_reranking.return_value = None  # disabled

        config = self._make_config(reranking_enabled=False)
        pipeline = get_pipeline(config)

        assert pipeline._reranking is None
