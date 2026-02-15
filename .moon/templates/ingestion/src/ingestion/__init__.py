"""Ingestion - Document parsing with pluggable providers.

Extract text from documents (PDF, Markdown, HTML) using either local
parsing (pypdf) or server-side parsing (Albert API).

The provider is selected via ``ragfacile.toml``:

    [ingestion]
    provider = "local"   # or "albert"

Example usage::

    from ingestion import get_provider

    provider = get_provider()
    text = provider.extract_text("document.pdf")
    context = provider.process_file("document.pdf", filename="My Doc")
"""

from __future__ import annotations

from typing import Any

from ingestion._base import IngestionProvider


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
        from rag_core import get_config

        config = get_config()

    backend = config.ingestion.provider

    match backend:
        case "local":
            from ingestion.local import LocalProvider

            return LocalProvider()
        case "albert":
            from ingestion.albert import AlbertProvider

            return AlbertProvider()
        case _:
            msg = f"Unknown ingestion provider: {backend!r}. Expected 'local' or 'albert'."
            raise ValueError(msg)


__all__ = [
    "IngestionProvider",
    "get_provider",
]
