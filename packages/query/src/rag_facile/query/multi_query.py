"""Multi-query expansion strategy — Strategy 1 (primary).

Generates N reformulations of the user's query in formal French
administrative language, bridging the vocabulary gap between colloquial
queries and indexed official documents.

Example translations performed by the LLM:
- "APL"        → "Aide Personnalisée au Logement"
- "CNI"        → "Carte Nationale d'Identité"
- "fonc' pub'" → "fonctionnaire de la fonction publique d'État"
- "je me suis fait virer" → "licenciement, rupture du contrat de travail"
"""

from __future__ import annotations

import logging
from typing import Any

import openai
from instructor.core import InstructorRetryException

from rag_facile.query._base import QueryExpander
from rag_facile.query._models import ExpandedQueries


logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """\
Tu es un expert en droit et administration française.
Tu aides à améliorer la recherche documentaire dans les textes officiels \
(codes, circulaires, décrets, fiches pratiques) en reformulant les questions \
des utilisateurs dans le vocabulaire formel de l'administration française.

Règles :
- Développe les sigles et acronymes (APL → Aide Personnalisée au Logement).
- Remplace le langage familier par les termes juridiques ou administratifs exacts.
- Propose des formulations qui correspondent au style des textes officiels.
- Chaque variation doit cibler un angle de recherche distinct : \
développement de sigle, synonyme formel, référence légale associée.
- Réponds uniquement avec le JSON structuré demandé, sans texte supplémentaire.\
"""

_USER_PROMPT = """\
Question originale : {query}

Génère {num_variations} reformulations de cette question en vocabulaire \
administratif français officiel.\
"""


class MultiQueryExpander(QueryExpander):
    """Expand a query into N formal French administrative variations.

    Uses ``client.as_instructor()`` to call the LLM with a structured
    Pydantic output schema, ensuring parseable results every time.
    The Albert client is created lazily on first use.

    Args:
        config: RAG configuration (reads ``query.*`` fields).
            If ``None``, loads from ``ragfacile.toml``.
    """

    def __init__(self, config: Any | None = None) -> None:
        if config is None:
            from rag_facile.core import get_config

            config = get_config()

        self._model: str = config.query.model
        self._num_variations: int = config.query.num_variations
        self._include_original: bool = config.query.include_original
        self._instructor_client: object | None = None

    @property
    def _instructor(self) -> object:
        """Lazily create the instructor-wrapped Albert client on first use."""
        if self._instructor_client is None:
            from albert import AlbertClient

            self._instructor_client = AlbertClient().as_instructor()
        return self._instructor_client

    def expand(self, query: str) -> list[str]:
        """Expand query into formal French administrative variations.

        Calls the Albert LLM via ``instructor`` to generate structured
        reformulations, then prepends the original query when
        ``include_original`` is True (the default).

        Args:
            query: Raw user query (colloquial French, may contain acronyms).

        Returns:
            List of search strings.  Always at least ``[query]`` on error.
        """
        prompt = _USER_PROMPT.format(
            query=query,
            num_variations=self._num_variations,
        )

        try:
            result: ExpandedQueries = self._instructor.chat.completions.create(  # type: ignore[attr-defined]
                model=self._model,
                response_model=ExpandedQueries,
                messages=[
                    {"role": "system", "content": _SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                max_retries=2,
            )
        except (openai.APIError, InstructorRetryException) as exc:
            # Graceful degradation: fall back to the original query
            # so retrieval still works even if expansion fails.
            logger.warning(
                "Multi-query expansion failed, falling back to original query: %s",
                exc,
            )
            return [query]

        logger.debug("Multi-query expansion reasoning: %s", result.reasoning)
        logger.info(
            "Expanded %r into %d variations", query[:50], len(result.variations)
        )

        queries = result.variations
        if self._include_original:
            queries = [query] + queries
        return queries
