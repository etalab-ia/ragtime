"""Albert-powered vector search.

Provides config-driven search functions that wrap the Albert client SDK.
All parameters default to ragfacile.toml values.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from rag_facile.core import RetrievedChunk


if TYPE_CHECKING:
    from albert import AlbertClient


logger = logging.getLogger(__name__)


def _search_result_to_chunk(result) -> RetrievedChunk:
    """Convert an Albert SearchResult to a RetrievedChunk."""
    chunk = result.chunk
    metadata = chunk.metadata or {}
    return RetrievedChunk(
        content=chunk.content,
        score=result.score,
        source_file=metadata.get("source"),
        page=metadata.get("page"),
        collection_id=chunk.collection_id,
        document_id=chunk.document_id,
        chunk_id=chunk.id,
    )


def search_chunks(
    client: AlbertClient,
    query: str,
    collection_ids: list[int | str],
    *,
    limit: int = 10,
    method: str = "hybrid",
    score_threshold: float | None = None,
) -> list[RetrievedChunk]:
    """Search for relevant chunks across collections.

    Args:
        client: Authenticated Albert client.
        query: Search query text.
        collection_ids: Collections to search in.
        limit: Maximum results to return.
        method: Search method ("hybrid", "semantic", or "lexical").
        score_threshold: Minimum relevance score (0.0-1.0).

    Returns:
        List of retrieved chunks sorted by score (descending).
    """
    # score_threshold is only supported for semantic search; the Albert API
    # rejects it for hybrid/lexical methods with a 400 Bad Request.
    effective_threshold = score_threshold if method == "semantic" else None

    response = client.search(
        prompt=query,
        collections=collection_ids,
        limit=limit,
        method=method,
        score_threshold=effective_threshold,
    )

    chunks = [_search_result_to_chunk(r) for r in response.data]
    logger.info(
        "Search returned %d chunks (method=%s, query=%r)",
        len(chunks),
        method,
        query[:50],
    )
    return chunks
