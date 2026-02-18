"""Pydantic output models for instructor-structured LLM responses.

These models define the exact JSON schema the LLM must produce when
called via ``instructor``.  The ``reasoning`` / ``keywords`` fields are
intentionally included for observability — they appear in debug logs
but are never passed downstream to the vector store.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class ExpandedQueries(BaseModel):
    """Structured output for multi-query expansion.

    The LLM is asked to produce ``variations`` — reformulations of the
    original query that use official French administrative vocabulary —
    plus a brief ``reasoning`` explaining the expansion strategy chosen.

    Example::

        ExpandedQueries(
            variations=[
                "conditions d'attribution de l'Aide Personnalisée au Logement",
                "demande APL logement social CAF",
                "bénéficier de l'aide au logement selon le code de la construction",
            ],
            reasoning="APL expanded to full name, formal code references added",
        )
    """

    variations: list[str] = Field(
        ...,
        min_length=1,
        max_length=5,
        description=(
            "Query variations using official French administrative vocabulary. "
            "Each variation should target a distinct retrieval angle: acronym "
            "expansion, formal synonym, or related legal concept."
        ),
    )
    reasoning: str = Field(
        ...,
        description=(
            "Brief explanation of the expansion strategy applied "
            "(used for observability and logging only)."
        ),
    )


class HypotheticalDocument(BaseModel):
    """Structured output for HyDE (Hypothetical Document Embeddings).

    The LLM generates an ideal administrative document that would perfectly
    answer the user's query.  Its ``content`` is embedded and searched
    instead of (or alongside) the raw query, bridging the colloquial→formal
    vocabulary gap at embedding time.

    Example::

        HypotheticalDocument(
            content=(
                "Conformément à l'article L. 821-1 du code de la sécurité sociale, "
                "l'Aide Personnalisée au Logement (APL) est accordée aux personnes "
                "occupant un logement conventionné. Pour en bénéficier, le demandeur "
                "doit déposer un dossier auprès de la Caisse d'Allocations Familiales "
                "compétente..."
            ),
            document_type="notice informative",
            keywords=["APL", "aide au logement", "CAF", "article L. 821-1"],
        )
    """

    content: str = Field(
        ...,
        description=(
            "Full text of a hypothetical ideal administrative document that "
            "would perfectly answer the user's query.  Write in formal French "
            "administrative style, citing relevant articles and official procedures."
        ),
    )
    document_type: str = Field(
        ...,
        description=(
            "Type of administrative document: circulaire, décret, notice "
            "informative, fiche pratique, arrêté, etc."
        ),
    )
    keywords: list[str] = Field(
        default_factory=list,
        description=(
            "Key administrative terms appearing in the document "
            "(used for observability and logging only)."
        ),
    )
