"""Albert-powered vector search provider.

Implements :class:`RetrievalProvider` using the Albert API.
Configuration parameters (method, top_k, score_threshold) are injected at
construction time by :func:`rag_facile.retrieval.get_provider`.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from rag_facile.core import RetrievedChunk

from ._base import RetrievalProvider


if TYPE_CHECKING:
    from albert import AlbertClient  # Only needed for type annotations


logger = logging.getLogger(__name__)


def _search_result_to_chunk(result: object) -> RetrievedChunk:
    """Convert an Albert SearchResult to a RetrievedChunk."""
    chunk = result.chunk  # type: ignore[attr-defined]
    metadata = chunk.metadata or {}
    return RetrievedChunk(
        content=chunk.content,
        score=result.score,  # type: ignore[attr-defined]
        source_file=metadata.get("source"),
        page=metadata.get("page"),
        collection_id=chunk.collection_id,
        document_id=chunk.document_id,
        chunk_id=chunk.id,
    )


class AlbertRetrievalProvider(RetrievalProvider):
    """Retrieval provider backed by the Albert API.

    Wraps Albert's ``/search`` endpoint.  All search parameters are fixed at
    construction time (loaded from ``ragfacile.toml`` by the factory) so
    call-sites only supply the runtime inputs: query and collection IDs.

    Args:
        method: Search method (``"hybrid"``, ``"semantic"``, or ``"lexical"``).
        top_k: Maximum number of chunks to retrieve.
        score_threshold: Minimum relevance score filter (0.0–1.0).
            Only applied for semantic search; ignored otherwise (Albert API
            constraint).
    """

    def __init__(
        self,
        *,
        method: str = "hybrid",
        top_k: int = 10,
        score_threshold: float = 0.0,
        client: AlbertClient | None = None,
    ) -> None:
        self._method = method
        self._top_k = top_k
        self._score_threshold = score_threshold
        self._client: AlbertClient | None = client

    @property
    def _albert_client(self) -> AlbertClient:
        """Lazily create the Albert client on first use."""
        if self._client is None:
            from albert import AlbertClient as _AlbertClient

            self._client = _AlbertClient()
        return self._client

    def search(
        self,
        query: str,
        collection_ids: list[int | str],
    ) -> list[RetrievedChunk]:
        """Search for relevant chunks across Albert collections.

        Args:
            query: Search query text.
            collection_ids: Albert collection IDs to search.

        Returns:
            List of retrieved chunks sorted by relevance score (descending).
        """
        # score_threshold is only supported for semantic search; the Albert API
        # rejects it for hybrid/lexical methods with a 400 Bad Request.
        effective_threshold = (
            self._score_threshold if self._method == "semantic" else None
        )

        # Albert API requires integer collection IDs; coerce from str if needed
        # (e.g. when IDs are read from env vars or mixed-type config sources).
        collection_ids_int: list[int] = [int(c) for c in collection_ids]

        response = self._albert_client.search(
            query=query,
            collection_ids=collection_ids_int,
            limit=self._top_k,
            method=self._method,
            score_threshold=effective_threshold,
        )

        chunks = [_search_result_to_chunk(r) for r in response.data]
        logger.info(
            "Search returned %d chunks (method=%s, query=%r)",
            len(chunks),
            self._method,
            query[:50],
        )
        return chunks
