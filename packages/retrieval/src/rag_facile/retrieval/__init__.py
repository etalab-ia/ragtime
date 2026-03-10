"""Retrieval - vector search for the RAG pipeline.

This package provides pluggable search capabilities for the RAG pipeline.
The provider is selected via ``ragfacile.toml``::

    [retrieval]
    provider = "albert"    # "albert" or "none"
    strategy = "hybrid"    # "hybrid", "semantic", or "lexical"
    top_k = 10

Example usage::

    from rag_facile.retrieval import get_provider

    retrieval = get_provider()
    chunks = retrieval.search("What is RAG?", collection_ids=[1])

Also provides :func:`fuse_results` to merge multi-query results
via Reciprocal Rank Fusion (RRF)::

    from rag_facile.retrieval import get_provider, fuse_results

    retrieval = get_provider()
    all_results = [retrieval.search(q, collection_ids=[1]) for q in queries]
    chunks = fuse_results(all_results, limit=10)

.. note::
    For reranking results, use the ``reranking`` package.
    For formatting chunks as LLM context, use the ``context`` package.
    For collection management (create, delete, list), use the ``storage`` package.
    For pipeline orchestration, use the ``pipelines`` package.
    For query expansion before retrieval, use the ``query`` package.
"""

from __future__ import annotations

from typing import Any

from rag_facile.retrieval._base import RetrievalProvider
from rag_facile.retrieval.albert import AlbertRetrievalProvider
from rag_facile.retrieval.fusion import fuse_results


def get_provider(config: Any | None = None) -> RetrievalProvider | None:
    """Get the configured retrieval provider.

    Reads ``retrieval.provider`` from ``ragfacile.toml`` (or the supplied
    *config*) to select the appropriate backend.  Returns ``None`` when
    ``retrieval.provider = "none"`` — the pipeline will skip retrieval and
    return an empty context.

    Args:
        config: Optional :class:`~rag_facile.core.RAGConfig` instance.
            If ``None``, loads configuration from ``ragfacile.toml``.

    Returns:
        A :class:`RetrievalProvider` instance, or ``None`` when
        ``retrieval.provider = "none"``.

    Raises:
        ValueError: If the configured provider is not recognised.
    """
    if config is None:
        from rag_facile.core import get_config

        config = get_config()

    provider = config.retrieval.provider

    match provider:
        case "albert":
            return AlbertRetrievalProvider(
                method=config.retrieval.strategy,
                top_k=config.retrieval.top_k,
                score_threshold=config.retrieval.score_threshold,
            )
        case "none":
            return None
        case _:
            msg = (
                f"Unknown retrieval provider: {provider!r}. "
                "Expected 'albert' or 'none'."
            )
            raise ValueError(msg)


__all__ = [
    "AlbertRetrievalProvider",
    "RetrievalProvider",
    "fuse_results",
    "get_provider",
]
