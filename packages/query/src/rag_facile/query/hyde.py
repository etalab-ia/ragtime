"""HyDE expansion strategy — Strategy 2 (Hypothetical Document Embeddings).

Instead of reformulating the query, this strategy asks the LLM to write
a *hypothetical* ideal administrative document that would perfectly answer
the question.  The document's content is then embedded and searched,
placing the query vector in the same semantic space as real indexed documents.

Reference: Gao et al. (2022) "Precise Zero-Shot Dense Retrieval without
Relevance Labels" — https://arxiv.org/abs/2212.10496
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

import openai
from instructor.core import InstructorRetryException

from rag_facile.query._base import QueryExpander
from rag_facile.query._models import HypotheticalDocument


if TYPE_CHECKING:
    from albert import AlbertClient


logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """\
Tu es un expert en droit et administration française.
Tu rédiges des documents administratifs officiels en réponse à des questions.

Règles :
- Rédige un extrait de document officiel (circulaire, décret, notice, fiche pratique) \
  qui répondrait parfaitement à la question posée.
- Utilise le style formel de l'administration française : langage juridique précis, \
  références aux articles de loi, acronymes développés.
- Le document doit être réaliste et crédible, même s'il est hypothétique.
- Limite-toi à 200-400 mots.
- Réponds uniquement avec le JSON structuré demandé, sans texte supplémentaire.\
"""

_USER_PROMPT = """\
Question de l'utilisateur : {query}

Rédige un extrait de document administratif officiel qui répondrait à cette question.\
"""


class HyDEExpander(QueryExpander):
    """Expand a query via Hypothetical Document Embeddings (HyDE).

    Generates a plausible administrative document matching the query's
    topic, then uses its formal text as the search string.  This bridges
    the colloquial→formal vocabulary gap at embedding time rather than at
    query formulation time.

    Args:
        client: Authenticated Albert client.
        config: RAG configuration (reads ``query.*`` fields).
    """

    def __init__(self, client: AlbertClient, config: Any | None = None) -> None:
        if config is None:
            from rag_facile.core import get_config

            config = get_config()

        self._instructor = client.as_instructor()
        self._model: str = config.query.model
        self._include_original: bool = config.query.include_original

    def expand(self, query: str) -> list[str]:
        """Generate a hypothetical administrative document and return its content.

        The returned content is meant to be embedded and searched rather than
        the raw query.  When ``include_original`` is True, the original query
        is also included so retrieval has both perspectives.

        Args:
            query: Raw user query.

        Returns:
            List of search strings.  Always at least ``[query]`` on error.
        """
        prompt = _USER_PROMPT.format(query=query)

        try:
            result: HypotheticalDocument = self._instructor.chat.completions.create(
                model=self._model,
                response_model=HypotheticalDocument,
                messages=[
                    {"role": "system", "content": _SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                max_retries=2,
            )
        except (openai.APIError, InstructorRetryException) as exc:
            # Graceful degradation: fall back to the original query.
            logger.warning(
                "HyDE expansion failed, falling back to original query: %s", exc
            )
            return [query]

        logger.debug(
            "HyDE document type=%r, keywords=%s",
            result.document_type,
            result.keywords,
        )
        logger.info(
            "HyDE generated %d-char hypothetical document for %r",
            len(result.content),
            query[:50],
        )

        queries = [result.content]
        if self._include_original:
            queries = [query] + queries
        return queries
