"""Unified RAG pipeline — composition-based, provider-per-phase.

:class:`RAGPipeline` is a concrete class that wires together independent
phase providers (ingestion, storage, retrieval, reranking, query expansion).
Behavior is determined entirely by which providers are injected — there are
no subclasses.  Use :func:`rag_facile.pipelines.get_pipeline` to instantiate
a correctly configured pipeline from ``ragfacile.toml``.

Provider wiring:

- ``storage=None``    → context-stuffing fallback (full document in prompt)
- ``retrieval=None``  → ``process_query()`` returns ``""`` (no retrieval)
- ``reranking=None``  → retrieval results are used directly (no re-scoring)
- ``query=None``      → single-query search (no expansion)
"""

from __future__ import annotations

import logging
import time
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import TYPE_CHECKING, Any


if TYPE_CHECKING:
    from albert import AlbertClient
    from rag_facile.core import RetrievedChunk
    from rag_facile.ingestion import IngestionProvider
    from rag_facile.query import QueryExpander
    from rag_facile.reranking import RerankingProvider
    from rag_facile.retrieval import RetrievalProvider
    from rag_facile.storage import StorageProvider


logger = logging.getLogger(__name__)


class RAGPipeline:
    """Unified RAG pipeline coordinating all phase providers.

    Provides a unified interface for both upload-time (file processing)
    and query-time (retrieval + generation context) operations.

    Args:
        ingestion: Provider for document text extraction.
        storage: Provider for collection/index management.
            When ``None``, :meth:`process_file` falls back to local text
            extraction (context stuffing).
        retrieval: Provider for vector search.
            When ``None``, :meth:`process_query` returns an empty string.
        reranking: Provider for cross-encoder re-scoring.
            When ``None``, retrieval results are used without re-scoring.
        query: Query expansion strategy.
            When ``None``, a single-query search is performed.
    """

    def __init__(
        self,
        *,
        ingestion: IngestionProvider,
        storage: StorageProvider | None = None,
        retrieval: RetrievalProvider | None = None,
        reranking: RerankingProvider | None = None,
        query: QueryExpander | None = None,
    ) -> None:
        self._ingestion = ingestion
        self._storage = storage
        self._retrieval = retrieval
        self._reranking = reranking
        self._query = query
        self._collection_id: int | None = None
        self._storage_client: AlbertClient | None = None

    # ── Internal helpers ──

    @property
    def _albert_client(self) -> AlbertClient:
        """Lazily create the Albert client used for storage operations."""
        if self._storage_client is None:
            from albert import AlbertClient as _AlbertClient

            self._storage_client = _AlbertClient()
        return self._storage_client

    def _ensure_collection(self) -> int:
        """Create a session collection if one doesn't exist yet.

        Returns:
            The collection ID for this session.
        """
        if self._collection_id is None:
            if self._storage is None:
                msg = "_ensure_collection called but storage provider is None"
                raise RuntimeError(msg)
            name = f"rag-facile-session-{time.time_ns()}"
            self._collection_id = self._storage.create_collection(
                self._albert_client, name, description="Auto-managed session collection"
            )
            logger.info(
                "Created session collection %s (id=%s)", name, self._collection_id
            )
        return self._collection_id

    # ── Upload-time: file processing ──

    def process_file(
        self,
        path: str | Path,
        filename: str | None = None,
    ) -> str:
        """Process a file for the RAG pipeline.

        When a storage provider is configured, the file is uploaded to an
        auto-managed Albert collection for RAG retrieval (chunking and
        embedding handled server-side).

        When no storage provider is configured, the file is parsed locally
        and its full text is returned for context stuffing.

        Args:
            path: Path to the document.
            filename: Optional display name.  Defaults to the file's basename.

        Returns:
            Confirmation message (storage mode) or formatted full-text context
            (context-stuffing mode).
        """
        path = Path(path)
        display_name = filename or path.name

        if self._storage is not None:
            collection_id = self._ensure_collection()
            self._storage.ingest_documents(self._albert_client, [path], collection_id)
            logger.info("Ingested '%s' into collection %s", display_name, collection_id)
            return f"[Document indexed: {display_name}]"

        # Fallback: local text extraction (context stuffing)
        return self._ingestion.process_file(path, filename)

    def process_bytes(self, data: bytes, filename: str) -> str:
        """Process file bytes for the RAG pipeline.

        When a storage provider is configured, bytes are written to a
        temporary file and uploaded to the session collection.

        When no storage provider is configured, bytes are parsed locally
        and the full text is returned for context stuffing.

        Args:
            data: Raw file content.
            filename: Display name (also used to infer file type).

        Returns:
            Confirmation message (storage mode) or formatted full-text context
            (context-stuffing mode).
        """
        if self._storage is not None:
            suffix = Path(filename).suffix or ".txt"
            collection_id = self._ensure_collection()

            # Storage upload requires a file path — write bytes to a temp file.
            with NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
                tmp_path = Path(tmp.name)
                tmp.write(data)

            try:
                self._storage.ingest_documents(
                    self._albert_client, [tmp_path], collection_id
                )
            finally:
                tmp_path.unlink(missing_ok=True)

            logger.info("Ingested '%s' into collection %s", filename, collection_id)
            return f"[Document indexed: {filename}]"

        # Fallback: local text extraction (context stuffing)
        return self._ingestion.process_bytes(data, filename)

    # ── Query-time: retrieval ──

    def _get_chunks(
        self,
        query: str,
        **kwargs: object,
    ) -> tuple[
        list[RetrievedChunk], list[int | str], list[str], list[dict], list[dict]
    ]:
        """Run expand → search → fuse → rerank; return results for both
        :meth:`process_query` and :meth:`retrieve_chunks`.

        Returns:
            ``(chunks, collection_ids, expanded_queries, pre_rerank, reranked)``

            - *chunks*: final chunk list after optional reranking
            - *collection_ids*: resolved IDs that were searched
            - *expanded_queries*: query variants generated by expansion (for tracing)
            - *pre_rerank*: raw search results before reranking (for tracing)
            - *reranked*: reranked list, empty when reranking is off (for tracing)
        """
        from rag_facile.core import get_config
        from rag_facile.retrieval import fuse_results

        config = get_config()

        # Resolve collection IDs — explicit kwarg, config, or auto-managed session.
        # When collection_ids is explicitly passed (even empty), honour the
        # caller's intent (e.g. user disabled all public collections in the UI).
        # When not passed (None), fall back to config defaults.
        col_ids: list[int | str] | None = kwargs.get("collection_ids")  # type: ignore[assignment]
        initial = config.storage.collections if col_ids is None else col_ids
        ids: set[int | str] = set(initial)

        # Always include the auto-managed session collection if one exists
        if self._collection_id is not None:
            ids.add(self._collection_id)

        if not ids:
            logger.info("No collection IDs to search — skipping retrieval")
            return [], [], [], [], []
        collection_ids: list[int | str] = list(ids)
        logger.info("Searching collections: %s", collection_ids)

        # Step 0: Query expansion (optional)
        expanded_queries: list[str] = []
        if self._query is not None:
            queries = self._query.expand(query)
            expanded_queries = queries
            logger.info(
                "Query expansion: %d → %d queries",
                1,
                len(queries),
            )

            def _search(q: str) -> list:
                return self._retrieval.search(q, collection_ids)  # type: ignore[union-attr]

            from concurrent.futures import ThreadPoolExecutor

            with ThreadPoolExecutor() as executor:
                all_results = list(executor.map(_search, queries))
            chunks = fuse_results(all_results, limit=config.retrieval.top_k)
        else:
            # Step 1: Single search (default path — no expansion overhead)
            chunks = self._retrieval.search(query, collection_ids)  # type: ignore[union-attr]

        if not chunks:
            return [], collection_ids, expanded_queries, [], []

        pre_rerank = [dict(c) for c in chunks]

        # Step 2: Rerank — always uses the ORIGINAL query for precision
        reranked: list[dict] = []
        if self._reranking is not None:
            chunks = self._reranking.rerank(query, chunks)
            reranked = [dict(c) for c in chunks]

        return chunks, collection_ids, expanded_queries, pre_rerank, reranked

    def retrieve_chunks(self, query: str, **kwargs: object) -> list[Any]:
        """Return the individual chunks retrieved for *query*.

        Unlike :meth:`process_query`, which returns a formatted string ready for
        LLM injection, this method returns the raw chunks so callers can inspect
        retrieval quality (e.g. for evaluation metrics like context recall and
        context precision).

        When no retrieval provider is configured, returns an empty list.

        Args:
            query: User query to retrieve chunks for.
            **kwargs: Pipeline-specific options (same as :meth:`process_query`).

        Returns:
            List of retrieved :class:`~rag_facile.core.RetrievedChunk` dicts.
            Empty list when retrieval is not configured or no results found.
        """
        if self._retrieval is None:
            return []
        chunks, _, _, _, _ = self._get_chunks(query, **kwargs)
        return chunks

    def process_query(
        self,
        query: str,
        **kwargs: object,
    ) -> str:
        """Retrieve relevant context for a user query.

        When no retrieval provider is configured (``retrieval=None``), returns
        an empty string — suitable for pipelines using context stuffing where
        the full document is already in the prompt.

        When a retrieval provider is configured, orchestrates:

        0. Query expansion (optional — only when a query expander is set)
        1. Search for relevant chunks (retrieval provider)
        2. Fuse multi-query results via RRF (retrieval) — only when expanded
        3. Rerank results using the original query (reranking provider, optional)
        4. Format chunks as LLM context (context package)

        Args:
            query: User query to retrieve context for.
            **kwargs: Pipeline options.
                ``collection_ids``: Albert collection IDs to search.
                    Falls back to the auto-managed session collection.

        Returns:
            Formatted context string ready for LLM injection.
            Empty string if retrieval is not configured, no collection exists,
            or no results found.
        """
        if self._retrieval is None:
            return ""

        from rag_facile.context import format_context
        from rag_facile.core import get_config

        chunks, collection_ids, expanded_queries, pre_rerank, reranked = (
            self._get_chunks(query, **kwargs)
        )

        if not chunks:
            return ""

        # Format as LLM context
        context = format_context(chunks)

        # Log trace (best-effort — never block the pipeline)
        try:
            from rag_facile.tracing import (
                TraceRecord,
                _notify_hook,
                get_tracer,
                set_current_trace_id,
            )

            config = get_config()
            trace = TraceRecord(
                query=query,
                expanded_queries=expanded_queries,
                retrieved_chunks=pre_rerank,
                reranked_chunks=reranked,
                formatted_context=context,
                collection_ids=[int(i) for i in collection_ids],
                model=config.generation.model,
                temperature=config.generation.temperature,
                config_snapshot=config.model_dump(),
            )
            tracer = get_tracer(config)
            tracer.log_trace(trace)
            set_current_trace_id(trace.id)
            _notify_hook(trace)
            logger.info("Logged trace %s", trace.id)
        except Exception:  # noqa: BLE001
            # Tracing must never break the pipeline — log and continue
            logger.warning("Tracing failed (non-critical)", exc_info=True)

        return context

    # ── Capabilities (for UI file dialogs) ──

    @property
    def supported_extensions(self) -> list[str]:
        """File extensions this pipeline can process."""
        return self._ingestion.supported_extensions

    @property
    def accepted_mime_types(self) -> dict[str, list[str]]:
        """MIME types for file picker dialogs."""
        return self._ingestion.accepted_mime_types
