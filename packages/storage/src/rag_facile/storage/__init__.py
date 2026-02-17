"""Storage - Vector storage and collection management.

This package provides collection lifecycle operations for the RAG pipeline:

- **Create**: Initialize new document collections
- **Ingest**: Upload and index documents into collections
- **Delete**: Remove collections and their contents
- **List**: Browse accessible collections

Example usage::

    from rag_facile.storage import get_provider

    provider = get_provider()
    collection_id = provider.create_collection(client, "my-docs")
    provider.ingest_documents(client, ["report.pdf"], collection_id)

.. note::
    For document text extraction, use the ``ingestion`` package.
    For search, reranking, and context formatting, use the ``retrieval`` package.
"""

from __future__ import annotations

from typing import Any

from rag_facile.storage._base import StorageProvider


def get_provider(config: Any | None = None) -> StorageProvider:
    """Get the configured storage provider.

    Reads ``storage.provider`` from ragfacile.toml (or the given config)
    to select the appropriate backend.

    Args:
        config: Optional RAGConfig instance. If None, loads from ragfacile.toml.

    Returns:
        A configured :class:`StorageProvider` instance.

    Raises:
        ValueError: If the configured provider is unknown.
    """
    if config is None:
        from rag_facile.core import get_config

        config = get_config()

    backend = config.storage.provider

    match backend:
        case "albert-collections":
            from rag_facile.storage.albert import AlbertProvider

            return AlbertProvider()
        case _:
            msg = (
                f"Unknown storage provider: {backend!r}. "
                f"Valid options: 'albert-collections', 'local-sqlite'"
            )
            raise ValueError(msg)


__all__ = [
    "StorageProvider",
    "get_provider",
]
