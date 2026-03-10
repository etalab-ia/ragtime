"""Pipelines - RAG pipeline coordination for chat applications.

Provides a unified :class:`RAGPipeline` that coordinates all pipeline phases
via injected providers.  Each phase (ingestion, storage, retrieval, reranking,
query expansion) is independently configurable via ``ragfacile.toml``.

Pipeline construction is driven by per-phase provider settings::

    [ingestion]
    provider = "albert"        # or "local"

    [storage]
    provider = "albert-collections"

    [retrieval]
    provider = "albert"        # or "none" to skip retrieval

    [reranking]
    provider = "albert"
    enabled = true

    [query]
    strategy = "none"          # or "multi_query" / "hyde"

Example usage::

    from rag_facile.pipelines import get_pipeline

    pipeline = get_pipeline()
    context = pipeline.process_file("document.pdf")

Convenience functions are also available for simpler call-sites::

    from rag_facile.pipelines import process_file, process_bytes, get_accepted_mime_types
"""

from __future__ import annotations

import threading
from pathlib import Path
from typing import Any

from rag_facile.pipelines._base import RAGPipeline


# ── Singleton pipeline cache ──

_pipeline: RAGPipeline | None = None
_lock = threading.Lock()


def _get_or_create_pipeline() -> RAGPipeline:
    """Return the cached pipeline, creating it on first call."""
    global _pipeline  # noqa: PLW0603
    if _pipeline is None:
        with _lock:
            if _pipeline is None:
                _pipeline = get_pipeline()
    assert _pipeline is not None  # Narrowing for type checker
    return _pipeline


# ── Factory ──


def get_pipeline(config: Any | None = None) -> RAGPipeline:
    """Get a configured RAG pipeline.

    Reads ``ragfacile.toml`` to instantiate and wire the phase providers.
    Each phase independently selects its backend via its own ``provider``
    (or ``enabled``) config field.

    Args:
        config: Optional RAGConfig instance.  If *None*, loads from
            ragfacile.toml.

    Returns:
        A :class:`RAGPipeline` instance wired with the configured providers.
    """
    if config is None:
        from rag_facile.core import get_config

        config = get_config()

    # Ingestion — always required
    from rag_facile.ingestion import get_provider as get_ingestion_provider

    ingestion = get_ingestion_provider(config)

    # Storage — None for local-sqlite (being retired in favour of Supabase)
    storage = None
    if config.storage.provider != "local-sqlite":
        from rag_facile.storage import get_provider as get_storage_provider

        storage = get_storage_provider(config)

    # Retrieval — None when provider = "none"
    from rag_facile.retrieval import get_provider as get_retrieval_provider

    retrieval = get_retrieval_provider(config)

    # Reranking — None when disabled
    from rag_facile.reranking import get_provider as get_reranking_provider

    reranking = get_reranking_provider(config)

    # Query expansion — None when strategy = "none"
    query_expander = None
    if config.query.strategy != "none":
        from rag_facile.query import get_expander

        query_expander = get_expander(config)

    return RAGPipeline(
        ingestion=ingestion,
        storage=storage,
        retrieval=retrieval,
        reranking=reranking,
        query=query_expander,
    )


# ── Convenience functions ──
#
# These allow simple call-sites like:
#   from rag_facile.pipelines import process_file
#   context = process_file("doc.pdf")


def process_file(path: str | Path, filename: str | None = None) -> str:
    """Parse a file and return formatted context.

    Uses the singleton pipeline (created on first call from config).

    Args:
        path: Path to the document.
        filename: Optional display name.

    Returns:
        Formatted context string.
    """
    return _get_or_create_pipeline().process_file(path, filename)


def process_bytes(data: bytes, filename: str) -> str:
    """Parse file bytes and return formatted context.

    Uses the singleton pipeline (created on first call from config).

    Args:
        data: Raw file content.
        filename: Display name (also used to infer file type).

    Returns:
        Formatted context string.
    """
    return _get_or_create_pipeline().process_bytes(data, filename)


def process_query(query: str, **kwargs: object) -> str:
    """Retrieve relevant context for a user query.

    Uses the singleton pipeline (created on first call from config).
    When a retrieval provider is configured, performs
    expand (optional) → search → rerank (optional) → format.

    Args:
        query: User query to retrieve context for.
        **kwargs: Pipeline-specific options (e.g., ``collection_ids``).

    Returns:
        Formatted context string. Empty string when retrieval is not
        configured or no results found.
    """
    return _get_or_create_pipeline().process_query(query, **kwargs)


def get_accepted_mime_types() -> dict[str, list[str]]:
    """Get accepted MIME types for file upload dialogs.

    Returns:
        Dict mapping MIME types to file extensions.
    """
    return _get_or_create_pipeline().accepted_mime_types


__all__ = [
    "RAGPipeline",
    "get_accepted_mime_types",
    "get_pipeline",
    "process_bytes",
    "process_file",
    "process_query",
]
