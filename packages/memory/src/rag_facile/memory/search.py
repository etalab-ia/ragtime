"""Hybrid search combining FTS5 keyword and optional semantic (embedding) search.

Uses Reciprocal Rank Fusion (RRF) to merge results from both backends,
with graceful degradation to keyword-only when embeddings are unavailable.
"""

from __future__ import annotations

import logging

from rag_facile.memory.index import MemoryIndex, SearchResult

logger = logging.getLogger(__name__)

# RRF constant (standard value from the original RRF paper).
_RRF_K = 60


def hybrid_search(
    index: MemoryIndex,
    query: str,
    *,
    query_embedding: list[float] | None = None,
    limit: int = 5,
) -> list[SearchResult]:
    """Run a hybrid keyword + semantic search and return fused results.

    Parameters
    ----------
    index:
        The memory index to search.
    query:
        Natural language query string (used for FTS5 keyword search).
    query_embedding:
        Optional embedding vector for the query (used for semantic search).
        If ``None``, only keyword search is performed.
    limit:
        Maximum number of results to return.

    Returns
    -------
    list[SearchResult]
        Results ranked by fused RRF score.
    """
    keyword_results = index.search_keyword(query, limit=limit * 2)

    semantic_results: list[SearchResult] = []
    if query_embedding is not None:
        semantic_results = index.search_semantic(query_embedding, limit=limit * 2)

    if not keyword_results and not semantic_results:
        return []

    if not semantic_results:
        return keyword_results[:limit]

    if not keyword_results:
        return semantic_results[:limit]

    # Fuse with RRF
    return _fuse_rrf(keyword_results, semantic_results, limit=limit)


def _fuse_rrf(
    *result_lists: list[SearchResult],
    limit: int = 5,
) -> list[SearchResult]:
    """Merge multiple ranked result lists using Reciprocal Rank Fusion.

    RRF score = sum(1 / (k + rank_i)) across all lists.
    """
    # Key: (source_file, line_start) to identify unique chunks
    scores: dict[tuple[str, int], float] = {}
    best_result: dict[tuple[str, int], SearchResult] = {}

    for results in result_lists:
        for rank, result in enumerate(results):
            key = (result.source_file, result.line_start)
            rrf_score = 1.0 / (_RRF_K + rank)
            scores[key] = scores.get(key, 0.0) + rrf_score

            # Track whether this result appeared in multiple lists
            if key in best_result:
                best_result[key].match_type = "both"
            else:
                best_result[key] = result

    # Sort by fused score (descending)
    ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)

    output: list[SearchResult] = []
    for key, score in ranked[:limit]:
        result = best_result[key]
        result.score = score
        output.append(result)

    return output


def format_search_results(results: list[SearchResult]) -> str:
    """Format search results as a readable string for the agent.

    Includes source citations so the agent can use ``get_memory`` for details.
    """
    if not results:
        return "No results found."

    parts: list[str] = []
    for i, r in enumerate(results, 1):
        match_label = {"keyword": "KW", "semantic": "SEM", "both": "KW+SEM"}.get(
            r.match_type, "?"
        )
        parts.append(
            f"**{i}. [{r.source_file}:{r.line_start}-{r.line_end}]** "
            f"(§ {r.section}) [{match_label}]\n"
            f"{r.content[:300]}{'…' if len(r.content) > 300 else ''}"
        )

    return "\n\n".join(parts)
