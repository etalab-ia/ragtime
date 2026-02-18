"""Reciprocal Rank Fusion (RRF) for multi-query result aggregation.

When query expansion produces N search strings, each is searched independently.
``fuse_results`` merges those N result lists into a single de-duplicated,
re-ranked list using the RRF algorithm (Cormack et al., 2009).

Algorithm
---------
For each result list *i* and each chunk at rank *r* (0-indexed)::

    rrf_score += 1 / (k + r + 1)

where *k* = 60 is the standard constant (empirically optimal).

Chunks confirmed relevant by multiple query angles receive additive boosts —
no cross-query score normalisation is required.  After fusion, the
Albert reranker applies a precision pass using the **original** user query.
"""

from __future__ import annotations

import logging

from rag_facile.core import RetrievedChunk


logger = logging.getLogger(__name__)

_DEFAULT_K = 60  # Cormack constant — do not change without benchmarking


def fuse_results(
    results_per_query: list[list[RetrievedChunk]],
    *,
    k: int = _DEFAULT_K,
    limit: int | None = None,
) -> list[RetrievedChunk]:
    """Merge multiple ranked result lists into one via Reciprocal Rank Fusion.

    Args:
        results_per_query: One :class:`~rag_facile.core.RetrievedChunk` list
            per query variant.  Empty inner lists are ignored.
        k: Cormack constant (default 60).  Higher values reduce the impact of
            top-ranked documents; lower values increase it.
        limit: Truncate the fused list to this many results.  If ``None``,
            all unique chunks are returned.

    Returns:
        De-duplicated list of :class:`~rag_facile.core.RetrievedChunk` sorted
        by descending RRF score.  The ``score`` field of each chunk is set to
        its accumulated RRF score.
    """
    if not results_per_query:
        return []

    # Accumulate RRF scores.
    # Dedup key: (chunk_id, collection_id) — globally unique chunk identity.
    rrf_scores: dict[tuple[int, int], float] = {}
    # Keep the first-seen chunk object for each dedup key (preserves metadata).
    best_chunks: dict[tuple[int, int], RetrievedChunk] = {}

    for result_list in results_per_query:
        for rank, chunk in enumerate(result_list):
            key = (chunk["chunk_id"], chunk["collection_id"])
            score = 1.0 / (k + rank + 1)
            rrf_scores[key] = rrf_scores.get(key, 0.0) + score
            if key not in best_chunks:
                best_chunks[key] = chunk

    # Build output: copy each chunk and set its score to the RRF score.
    fused: list[RetrievedChunk] = []
    for key, rrf_score in sorted(rrf_scores.items(), key=lambda x: x[1], reverse=True):
        chunk = best_chunks[key].copy()
        chunk["score"] = rrf_score
        fused.append(chunk)

    if limit is not None:
        fused = fused[:limit]

    total_input = sum(len(r) for r in results_per_query)
    logger.info(
        "RRF fusion: %d results across %d queries → %d unique chunks (limit=%s)",
        total_input,
        len(results_per_query),
        len(fused),
        limit,
    )
    return fused
