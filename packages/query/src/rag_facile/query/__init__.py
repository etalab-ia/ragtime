"""Query Expansion - broaden RAG retrieval with formal French administrative vocabulary.

Sits between the user query and the vector store, generating one or more
optimised search strings that bridge colloquial input and formal document language.

Selected strategy is configured via ``ragfacile.toml``::

    [query]
    strategy = "multi_query"   # "multi_query" | "hyde" | "none"
    num_variations = 3
    include_original = true
    model = "openweight-medium"

Example usage::

    from rag_facile.query import get_expander

    expander = get_expander()
    queries = expander.expand("comment toucher les APL ?")
    # → ["comment toucher les APL ?",
    #    "conditions d'attribution de l'Aide Personnalisée au Logement",
    #    ...]

.. note::
    Pair with :func:`rag_facile.retrieval.fuse_results` to merge the results
    from multiple queries before reranking.
"""

from __future__ import annotations

from typing import Any

from rag_facile.query._base import QueryExpander


def get_expander(config: Any | None = None) -> QueryExpander:
    """Return the configured query expander.

    Reads ``ragfacile.toml`` (or the supplied *config*) to determine which
    expansion strategy to instantiate.  The Albert client is created lazily
    by the expander on first :meth:`~QueryExpander.expand` call.

    Args:
        config: Optional :class:`~rag_facile.core.RAGConfig` instance.
            If ``None``, loads configuration from ``ragfacile.toml``.

    Returns:
        A :class:`QueryExpander` instance for the configured strategy.

    Raises:
        ValueError: If the configured strategy is not recognised.
    """
    if config is None:
        from rag_facile.core import get_config

        config = get_config()

    strategy = config.query.strategy

    match strategy:
        case "multi_query":
            from rag_facile.query.multi_query import MultiQueryExpander

            return MultiQueryExpander(config)
        case "hyde":
            from rag_facile.query.hyde import HyDEExpander

            return HyDEExpander(config)
        case _:
            msg = (
                f"Unknown query expansion strategy: {strategy!r}. "
                "Expected 'multi_query', 'hyde', or 'none'."
            )
            raise ValueError(msg)


__all__ = [
    "QueryExpander",
    "get_expander",
]
