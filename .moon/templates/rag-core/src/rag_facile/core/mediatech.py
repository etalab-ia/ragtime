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
# Reverse lookup: collection ID → name (built lazily)
_id_to_name: dict[int, str] | None = None


def get_collection_name(collection_id: int) -> str | None:
    """Get the human-readable name for a collection ID.

    Looks up the ID in the MediaTech catalog.  Returns *None* if the
    ID is not a known MediaTech collection.
    """
    global _id_to_name  # noqa: PLW0603
    if _id_to_name is None:
        _id_to_name = {entry["id"]: name for name, entry in MEDIATECH_CATALOG.items()}
    return _id_to_name.get(collection_id)


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
