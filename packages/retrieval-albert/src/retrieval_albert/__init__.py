"""Retrieval Albert - RAG retrieval via Albert API.

Provides document ingestion, semantic search, reranking, and context
formatting powered by Albert's sovereign AI platform.

All functions follow a functional style -- explicit AlbertClient injection,
no classes, config-driven defaults from ragfacile.toml.

Example:
    from albert import AlbertClient
    from retrieval_albert import process_query, retrieve

    # One-shot: retrieve + format
    context = process_query("Qu'est-ce que le Code civil?", collection_ids=[123])

    # Granular control
    client = AlbertClient()
    chunks = retrieve(client, "Code civil", collection_ids=[123])
"""

from ._types import RetrievedChunk
from .formatter import format_context, process_query
from .ingestion import (
    create_collection,
    delete_collection,
    ingest_documents,
    list_collections,
)
from .parser import (
    extract_text_from_bytes,
    extract_text_from_pdf,
    format_as_context,
    process_multiple_files,
    process_pdf_file,
)
from .retriever import rerank_chunks, retrieve, search_chunks


__all__ = [
    # Types
    "RetrievedChunk",
    # Parser (context_loader-compatible, same interface as retrieval-basic)
    "extract_text_from_bytes",
    "extract_text_from_pdf",
    "format_as_context",
    "process_multiple_files",
    "process_pdf_file",
    # Ingestion
    "create_collection",
    "delete_collection",
    "ingest_documents",
    "list_collections",
    # Retrieval
    "rerank_chunks",
    "retrieve",
    "search_chunks",
    # Formatting
    "format_context",
    "process_query",
]
