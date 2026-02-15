"""Albert RAG pipeline — full retrieval with Albert API.

Parses documents via the Albert API (ingestion package) and supports
query-time retrieval with search, reranking, and context formatting
(retrieval package).

Selected when ``storage.provider = "albert-collections"`` in ragfacile.toml.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

from ._base import RAGPipeline


if TYPE_CHECKING:
    from albert import AlbertClient


class AlbertPipeline(RAGPipeline):
    """Full RAG pipeline using the Albert API.

    File processing is delegated to the ingestion package's
    :class:`~ingestion.AlbertProvider`.  Query-time retrieval delegates to
    the retrieval package for search, reranking, and context formatting.

    Collection management methods are exposed via composition for
    applications that need to ingest documents into Albert collections.
    """

    def __init__(self, config: Any | None = None) -> None:
        from ingestion import get_provider

        self._ingestion = get_provider(config)

    # ── Upload-time: file processing ──

    def process_file(
        self,
        path: str | Path,
        filename: str | None = None,
    ) -> str:
        """Parse a file via Albert API and return formatted context."""
        return self._ingestion.process_file(path, filename)

    def process_bytes(self, data: bytes, filename: str) -> str:
        """Parse file bytes via Albert API and return formatted context."""
        return self._ingestion.process_bytes(data, filename)

    # ── Query-time: retrieval ──

    def process_query(
        self,
        query: str,
        **kwargs: object,
    ) -> str:
        """Retrieve relevant context from Albert collections.

        Performs search → optional rerank → format.  Delegates to
        :func:`retrieval.process_query`.

        Args:
            query: User query to retrieve context for.
            **kwargs: Passed to :func:`retrieval.process_query`.
                Common keys: ``collection_ids``, ``client``.

        Returns:
            Formatted context string ready for LLM injection.
        """
        from retrieval.formatter import process_query

        return process_query(query, **kwargs)  # type: ignore[arg-type]

    # ── Collection management (delegated to retrieval) ──

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
        from retrieval.ingestion import create_collection

        return create_collection(client, name, description)

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
        from retrieval.ingestion import ingest_documents

        return ingest_documents(
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
        from retrieval.ingestion import delete_collection

        delete_collection(client, collection_id)

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
        from retrieval.ingestion import list_collections

        return list_collections(client, limit=limit, offset=offset)

    # ── Capabilities ──

    @property
    def supported_extensions(self) -> list[str]:
        """File extensions supported by the Albert ingestion provider."""
        return self._ingestion.supported_extensions

    @property
    def accepted_mime_types(self) -> dict[str, list[str]]:
        """MIME types accepted by the Albert ingestion provider."""
        return self._ingestion.accepted_mime_types
