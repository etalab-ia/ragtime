"""Base interface for query expansion strategies.

Defines the :class:`QueryExpander` ABC that all backends must implement.
"""

from __future__ import annotations

from abc import ABC, abstractmethod


class QueryExpander(ABC):
    """Abstract base class for query expansion strategies.

    A query expander takes a raw user query and returns a list of
    search strings for the vector store.  All returned strings should
    be searched and the results aggregated via :func:`fuse_results`.

    Example::

        expander = MultiQueryExpander(client, config)
        queries = expander.expand("comment toucher les APL ?")
        # → ["comment toucher les APL ?",
        #    "conditions d'attribution de l'Aide Personnalisée au Logement",
        #    "démarches pour bénéficier des APL logement social",
        #    "demande d'aide personnalisée au logement CAF"]

    Subclasses must implement:
      - :meth:`expand` — expand a raw query into a list of search strings
    """

    @abstractmethod
    def expand(self, query: str) -> list[str]:
        """Expand a user query into one or more search strings.

        Args:
            query: Raw user query (may be colloquial, contain acronyms, etc.).

        Returns:
            List of query strings to send to the vector store.
            Callers should search with ALL returned strings and merge
            results using :func:`rag_facile.retrieval.fuse_results`.
        """
