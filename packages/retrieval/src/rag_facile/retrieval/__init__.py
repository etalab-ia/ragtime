"""Retrieval - vector search for the RAG pipeline.

This package provides search capabilities via the Albert API:
semantic, lexical, and hybrid search across document collections.
It also provides :func:`fuse_results` to merge multi-query results
via Reciprocal Rank Fusion (RRF).

Example usage::

    from rag_facile.retrieval import search_chunks, fuse_results

    # Single query
    chunks = search_chunks(client, "What is RAG?", collection_ids=[1])

    # Multi-query with RRF fusion
    all_results = [
        search_chunks(client, q, collection_ids=[1])
        for q in expanded_queries
    ]
    chunks = fuse_results(all_results, limit=10)

.. note::
    For reranking results, use the ``reranking`` package.
    For formatting chunks as LLM context, use the ``context`` package.
    For collection management (create, delete, list), use the ``storage`` package.
    For pipeline orchestration, use the ``pipelines`` package.
    For query expansion before retrieval, use the ``query`` package.
"""

from rag_facile.retrieval.albert import search_chunks
from rag_facile.retrieval.fusion import fuse_results

__all__ = [
    "fuse_results",
    "search_chunks",
]
