"""Retrieval - Search, reranking, and collection management.

This package provides retrieval capabilities for the RAG pipeline:

- **Search**: Find relevant document chunks via Albert API
- **Reranking**: Re-score results with a cross-encoder for higher precision
- **Formatting**: Convert retrieved chunks into LLM-ready context strings
- **Collection management**: Create, populate, and delete Albert collections

Example usage::

    from retrieval import retrieve, format_context

    chunks = retrieve(client, "What is RAG?", collection_ids=[1])
    context = format_context(chunks)

.. note::
    For file parsing and text extraction, use the ``ingestion`` package.
    For pipeline orchestration (coordinating ingestion + retrieval),
    use the ``orchestration`` package.
"""

from retrieval._types import RetrievedChunk
from retrieval.albert import rerank_chunks, retrieve, search_chunks
from retrieval.formatter import format_context, process_query
from retrieval.ingestion import (
    create_collection,
    delete_collection,
    ingest_documents,
    list_collections,
)

__all__ = [
    "RetrievedChunk",
    # Search & reranking
    "retrieve",
    "search_chunks",
    "rerank_chunks",
    # Context formatting
    "format_context",
    "process_query",
    # Collection management
    "create_collection",
    "ingest_documents",
    "delete_collection",
    "list_collections",
]
