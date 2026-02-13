"""Albert-powered RAG retrieval pipeline.

Provides config-driven search and reranking functions that wrap the
Albert client SDK. All parameters default to ragfacile.toml values.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from rag_core import get_config

from ._types import RetrievedChunk


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

    This is the low-level search function (no reranking).

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
    response = client.search(
        prompt=query,
        collections=collection_ids,
        limit=limit,
        method=method,
        score_threshold=score_threshold,
    )

    chunks = [_search_result_to_chunk(r) for r in response.data]
    logger.info(
        "Search returned %d chunks (method=%s, query=%r)",
        len(chunks),
        method,
        query[:50],
    )
    return chunks


def rerank_chunks(
    client: AlbertClient,
    query: str,
    chunks: list[RetrievedChunk],
    *,
    model: str = "bge-reranker-large",
    top_n: int | None = None,
) -> list[RetrievedChunk]:
    """Rerank chunks by relevance to a query.

    Args:
        client: Authenticated Albert client.
        query: The query to rank chunks against.
        chunks: Chunks to rerank.
        model: Reranker model name.
        top_n: Return only top N results. If None, returns all.

    Returns:
        Reranked list of chunks (highest relevance first).
    """
    if not chunks:
        return []

    documents = [c["content"] for c in chunks]
    response = client.rerank(
        query=query,
        documents=documents,
        model=model,
        top_n=top_n,
    )

    # Build reranked list using the results index mapping
    reranked: list[RetrievedChunk] = []
    for result in response.results:
        original = chunks[result.index]
        reranked.append(
            RetrievedChunk(
                content=original["content"],
                score=result.relevance_score,
                source_file=original["source_file"],
                page=original["page"],
                collection_id=original["collection_id"],
                document_id=original["document_id"],
                chunk_id=original["chunk_id"],
            )
        )

    logger.info("Reranked %d chunks → %d results", len(chunks), len(reranked))
    return reranked


def retrieve(
    client: AlbertClient,
    query: str,
    collection_ids: list[int | str],
    *,
    top_k: int | None = None,
    method: str | None = None,
    score_threshold: float | None = None,
    rerank: bool | None = None,
    rerank_model: str | None = None,
    rerank_top_n: int | None = None,
) -> list[RetrievedChunk]:
    """Full retrieval pipeline: search then optionally rerank.

    All parameters default to ragfacile.toml config values via rag_core.

    Args:
        client: Authenticated Albert client.
        query: Search query text.
        collection_ids: Collections to search in.
        top_k: Number of search results (defaults to config.retrieval.top_k).
        method: Search method (defaults to config.retrieval.method).
        score_threshold: Min score (defaults to config.retrieval.score_threshold).
        rerank: Whether to rerank (defaults to config.reranking.enabled).
        rerank_model: Reranker model (defaults to config.reranking.model).
        rerank_top_n: Final count after reranking (defaults to config.reranking.top_n).

    Returns:
        List of retrieved chunks, ordered by relevance.
    """
    config = get_config()

    # Apply config defaults
    top_k = top_k if top_k is not None else config.retrieval.top_k
    method = method if method is not None else config.retrieval.method
    score_threshold = (
        score_threshold
        if score_threshold is not None
        else config.retrieval.score_threshold
    )
    rerank = rerank if rerank is not None else config.reranking.enabled
    rerank_model = rerank_model if rerank_model is not None else config.reranking.model
    rerank_top_n = rerank_top_n if rerank_top_n is not None else config.reranking.top_n

    # Step 1: Search
    chunks = search_chunks(
        client,
        query,
        collection_ids,
        limit=top_k,
        method=method,
        score_threshold=score_threshold,
    )

    if not chunks:
        return []

    # Step 2: Rerank (optional)
    if rerank:
        chunks = rerank_chunks(
            client,
            query,
            chunks,
            model=rerank_model,
            top_n=rerank_top_n,
        )

    return chunks
