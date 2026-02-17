"""Retrieval - vector search for the RAG pipeline.

This package provides search capabilities via the Albert API:
semantic, lexical, and hybrid search across document collections.

Example usage::

    from rag_facile.retrieval import search_chunks

    chunks = search_chunks(client, "What is RAG?", collection_ids=[1])

.. note::
    For reranking results, use the ``reranking`` package.
    For formatting chunks as LLM context, use the ``context`` package.
    For collection management (create, delete, list), use the ``storage`` package.
    For pipeline orchestration, use the ``pipelines`` package.
"""

from rag_facile.retrieval.albert import search_chunks

__all__ = [
    "search_chunks",
]
