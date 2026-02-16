"""MediaTech public collections from AgentPublic.

Well-known public collections available on the Albert API, sourced from
https://huggingface.co/collections/AgentPublic/mediatech

These datasets are chunked, vectorized, and ready to use in RAG pipelines.
Collection IDs are specific to the etalab Albert API instance.

Use ``rag-facile collections list`` to discover all available collections.
"""

from __future__ import annotations

from typing import TypedDict


class MediaTechEntry(TypedDict):
    """Metadata for a MediaTech collection."""

    id: int
    description: str
    presets: list[str]


#: Maps collection name → metadata.
#: IDs correspond to the etalab Albert API instance (albert.api.etalab.gouv.fr).
MEDIATECH_CATALOG: dict[str, MediaTechEntry] = {
    "service-public": {
        "id": 785,
        "description": "Fiches pratiques Service Public",
        "presets": ["balanced", "fast", "accurate"],
    },
    "travail-emploi": {
        "id": 784,
        "description": "Fiches pratiques Travail Emploi",
        "presets": ["hr"],
    },
    "annuaire-administrations-etat": {
        "id": 783,
        "description": "Annuaire des administrations d'état",
        "presets": ["balanced"],
    },
    "data-gouv-datasets-catalog": {
        "id": 1094,
        "description": "Catalogue des jeux de données publiées sur data.gouv.fr",
        "presets": ["balanced"],
    },
}
