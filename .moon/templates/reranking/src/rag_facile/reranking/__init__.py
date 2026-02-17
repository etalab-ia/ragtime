"""Reranking - re-score retrieved chunks with a cross-encoder.

This package provides reranking capabilities for the RAG pipeline.
Given a query and a list of retrieved chunks, it re-scores them using
a cross-encoder model for higher precision.

Example usage::

    from rag_facile.reranking import rerank_chunks

    reranked = rerank_chunks(client, "What is RAG?", chunks)

.. note::
    For vector search, use the ``retrieval`` package.
    For context formatting, use the ``context`` package.
"""

from rag_facile.reranking.albert import rerank_chunks

__all__ = [
    "rerank_chunks",
]
