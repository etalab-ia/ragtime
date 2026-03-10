"""Ingestion - Document parsing with pluggable providers.

Extract text from documents (PDF, Markdown, HTML) using local parsing (pypdf).

The provider is selected via ``ragfacile.toml``:

    [ingestion]
    provider = "local"

Example usage::

    from rag_facile.ingestion import get_provider

    provider = get_provider()
    text = provider.extract_text("document.pdf")
    context = provider.process_file("document.pdf", filename="My Doc")

.. note::

    The ``"albert"`` ingestion provider has been removed in albert-client 0.4.1.
    The ``/parse-beta`` endpoint it relied on is deprecated and will be removed
    in Albert API 0.5.0. Use the default ``"local"`` provider for text extraction,
    or rely on ``AlbertPipeline.process_file()`` which uploads documents directly
    to Albert for server-side parsing, chunking, and embedding.
"""

from __future__ import annotations

from typing import Any

from rag_facile.ingestion._base import IngestionProvider


def get_provider(config: Any | None = None) -> IngestionProvider:
    """Get the configured ingestion provider.

    Reads ``ragfacile.toml`` to determine which backend to use.

    Args:
        config: Optional RAGConfig instance. If None, loads from ragfacile.toml.

    Returns:
        An :class:`IngestionProvider` instance for the configured backend.

    Raises:
        ValueError: If the configured provider is not recognized.
    """
    if config is None:
        from rag_facile.core import get_config

        config = get_config()

    backend = config.ingestion.provider

    match backend:
        case "local":
            from rag_facile.ingestion.local import LocalProvider

            return LocalProvider()
        case "albert":
            raise ValueError(
                "The 'albert' ingestion provider has been removed in albert-client 0.4.1. "
                "The /parse-beta endpoint it used is deprecated in Albert API 0.4.1 and "
                'will be removed in 0.5.0. Use provider = "local" in ragfacile.toml, '
                "or let AlbertPipeline handle document upload directly."
            )
        case _:
            msg = f"Unknown ingestion provider: {backend!r}. Expected 'local'."
            raise ValueError(msg)


__all__ = [
    "IngestionProvider",
    "get_provider",
]
