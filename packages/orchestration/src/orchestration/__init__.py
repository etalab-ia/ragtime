"""Orchestration - RAG pipeline coordination for chat applications.

Provides a unified :class:`RAGPipeline` interface that coordinates
document ingestion and retrieval.  Chat apps depend on this package
instead of importing from ingestion or retrieval directly.

Pipeline selection is driven by ``ragfacile.toml``::

    [storage]
    provider = "local-sqlite"          # → BasicPipeline
    provider = "albert-collections"    # → AlbertPipeline

Example usage::

    from orchestration import get_pipeline

    pipeline = get_pipeline()
    context = pipeline.process_file("document.pdf")

Convenience functions are also available for simpler call sites::

    from orchestration import process_file, process_bytes, get_accepted_mime_types
"""

from __future__ import annotations

import threading
from pathlib import Path
from typing import Any

from orchestration._base import RAGPipeline


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

    Reads ``ragfacile.toml`` to determine which pipeline to instantiate.

    Args:
        config: Optional RAGConfig instance.  If *None*, loads from
            ragfacile.toml.

    Returns:
        A :class:`RAGPipeline` instance for the configured backend.

    Raises:
        ValueError: If the configured storage provider is not recognized.
    """
    if config is None:
        from rag_core import get_config

        config = get_config()

    backend = config.storage.provider

    match backend:
        case "local-sqlite":
            from orchestration.basic import BasicPipeline

            return BasicPipeline(config)
        case "albert-collections":
            from orchestration.albert import AlbertPipeline

            return AlbertPipeline(config)
        case _:
            msg = (
                f"Unknown storage backend: {backend!r}. "
                "Expected 'local-sqlite' or 'albert-collections'."
            )
            raise ValueError(msg)


# ── Convenience functions ──
#
# These allow simple call-sites like:
#   from orchestration import process_file
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
]
