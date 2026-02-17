"""Albert RAG pipeline — true retrieval-augmented generation with Albert API.

Ingests documents into Albert collections (chunking + embedding handled
server-side), then retrieves relevant chunks at query time via
search -> rerank -> format.  Orchestrates the individual phase packages.

Selected when ``storage.provider = "albert-collections"`` in ragfacile.toml.
"""

from __future__ import annotations

import logging
import time
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import TYPE_CHECKING, Any

from ._base import RAGPipeline


if TYPE_CHECKING:
    from albert import AlbertClient


logger = logging.getLogger(__name__)


class AlbertPipeline(RAGPipeline):
    """Full RAG pipeline using the Albert API.

    Documents are uploaded to an auto-managed Albert collection on first
    file upload.  At query time, relevant chunks are retrieved via
    search -> optional rerank -> context formatting.

    Collection management is delegated to the storage package.
    Query-time retrieval orchestrates: search -> rerank -> format
    using the retrieval, reranking, and context packages.
    """

    def __init__(self, config: Any | None = None) -> None:
        from rag_facile.ingestion import get_provider
        from rag_facile.storage import get_provider as get_storage_provider

        self._ingestion = get_provider(config)
        self._storage = get_storage_provider(config)
        self._client: AlbertClient | None = None
        self._collection_id: int | None = None

    # ── Internal helpers ──

    @property
    def client(self) -> AlbertClient:
        """Lazily create the Albert client on first use."""
        if self._client is None:
            from albert import AlbertClient as _AlbertClient

            self._client = _AlbertClient()
        return self._client

    def _ensure_collection(self) -> int:
        """Create a session collection if one doesn't exist yet.

        Returns:
            The collection ID for this session.
        """
        if self._collection_id is None:
            name = f"rag-facile-session-{time.time_ns()}"
            self._collection_id = self._storage.create_collection(
                self.client, name, description="Auto-managed session collection"
            )
            logger.info(
                "Created session collection %s (id=%s)", name, self._collection_id
            )
        return self._collection_id

    # ── Upload-time: ingest into collection ──

    def process_file(
        self,
        path: str | Path,
        filename: str | None = None,
    ) -> str:
        """Ingest a file into the session collection for RAG retrieval.

        The document is uploaded to Albert, which handles chunking and
        embedding server-side.

        Args:
            path: Path to the document.
            filename: Optional display name.

        Returns:
            Confirmation message with the uploaded filename.
        """
        path = Path(path)
        display_name = filename or path.name
        collection_id = self._ensure_collection()

        self._storage.ingest_documents(
            self.client,
            [path],
            collection_id,
        )
        logger.info("Ingested '%s' into collection %s", display_name, collection_id)
        return f"[Document indexed: {display_name}]"

    def process_bytes(self, data: bytes, filename: str) -> str:
        """Ingest file bytes into the session collection for RAG retrieval.

        Writes bytes to a temporary file, then uploads to Albert for
        chunking and embedding.

        Args:
            data: Raw file content.
            filename: Display name (also used to infer file type).

        Returns:
            Confirmation message with the uploaded filename.
        """
        suffix = Path(filename).suffix or ".txt"
        collection_id = self._ensure_collection()

        # Albert upload API requires a file path — write to temp file.
        with NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp_path = Path(tmp.name)
            tmp.write(data)

        try:
            self._storage.ingest_documents(
                self.client,
                [tmp_path],
                collection_id,
            )
        finally:
            tmp_path.unlink(missing_ok=True)

        logger.info("Ingested '%s' into collection %s", filename, collection_id)
        return f"[Document indexed: {filename}]"

    # ── Query-time: search -> rerank -> format ──

    def process_query(
        self,
        query: str,
        **kwargs: object,
    ) -> str:
        """Retrieve relevant context from Albert collections.

        Orchestrates the full retrieval pipeline:
        1. Search for relevant chunks (retrieval package)
        2. Optionally rerank results (reranking package)
        3. Format chunks as LLM context (context package)

        All parameters default to ragfacile.toml config values.

        Args:
            query: User query to retrieve context for.
            **kwargs: Pipeline options.
                ``collection_ids``: Albert collection IDs to search.
                    Falls back to the auto-managed session collection.
                ``client``: Optional pre-configured Albert client.

        Returns:
            Formatted context string ready for LLM injection.
            Empty string if no collection exists or no results found.
        """
        from rag_facile.context import format_context
        from rag_facile.core import get_config
        from rag_facile.reranking import rerank_chunks
        from rag_facile.retrieval import search_chunks

        config = get_config()

        # Resolve client
        client: AlbertClient | None = kwargs.get("client")  # type: ignore[assignment]
        if client is None:
            client = self.client

        # Resolve collection IDs — explicit kwarg, config, or auto-managed session.
        # When collection_ids is explicitly passed (even empty), honour the
        # caller's intent (e.g. user disabled all public collections in the UI).
        # When not passed (None), fall back to config defaults.
        collection_ids: list[int | str] | None = kwargs.get("collection_ids")  # type: ignore[assignment]
        initial = (
            config.storage.collections if collection_ids is None else collection_ids
        )
        ids: set[int | str] = set(initial)

        # Always include the auto-managed session collection if one exists
        if self._collection_id is not None:
            ids.add(self._collection_id)

        if not ids:
            logger.info("No collection IDs to search — skipping retrieval")
            return ""
        collection_ids = list(ids)
        logger.info("Searching collections: %s", collection_ids)

        # Step 1: Search
        chunks = search_chunks(
            client,
            query,
            collection_ids,
            limit=config.retrieval.top_k,
            method=config.retrieval.strategy,
            score_threshold=config.retrieval.score_threshold,
        )

        if not chunks:
            return ""

        # Step 2: Rerank (optional)
        if config.reranking.enabled:
            chunks = rerank_chunks(
                client,
                query,
                chunks,
                model=config.reranking.model,
                top_n=config.reranking.top_n,
            )

        # Step 3: Format as LLM context
        return format_context(chunks)

    # ── Collection management (delegated to storage) ──

    def create_collection(
        self,
        client: AlbertClient,
        name: str,
        description: str = "",
    ) -> int:
        """Create a new collection in Albert.

        Args:
            client: Configured Albert client.
            name: Collection name.
            description: Optional description.

        Returns:
            The new collection ID.
        """
        return self._storage.create_collection(client, name, description)

    def ingest_documents(
        self,
        client: AlbertClient,
        paths: list[str | Path],
        collection_id: int,
        *,
        chunk_size: int | None = None,
        chunk_overlap: int | None = None,
    ) -> list[int]:
        """Upload documents to an Albert collection for indexing.

        Args:
            client: Configured Albert client.
            paths: Document file paths to upload.
            collection_id: Target collection ID.
            chunk_size: Override chunk size (defaults to config).
            chunk_overlap: Override chunk overlap (defaults to config).

        Returns:
            List of document IDs created.
        """
        return self._storage.ingest_documents(
            client,
            paths,
            collection_id,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
        )

    def delete_collection(self, client: AlbertClient, collection_id: int) -> None:
        """Delete a collection and all its documents.

        Args:
            client: Configured Albert client.
            collection_id: Collection to delete.
        """
        self._storage.delete_collection(client, collection_id)

    def list_collections(
        self,
        client: AlbertClient,
        *,
        limit: int = 10,
        offset: int = 0,
    ) -> Any:
        """List accessible collections.

        Args:
            client: Configured Albert client.
            limit: Maximum number of results.
            offset: Pagination offset.

        Returns:
            CollectionList from Albert API.
        """
        return self._storage.list_collections(client, limit=limit, offset=offset)

    # ── Capabilities ──

    @property
    def supported_extensions(self) -> list[str]:
        """File extensions supported by the Albert ingestion provider."""
        return self._ingestion.supported_extensions

    @property
    def accepted_mime_types(self) -> dict[str, list[str]]:
        """MIME types accepted by the Albert ingestion provider."""
        return self._ingestion.accepted_mime_types
