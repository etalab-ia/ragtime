"""MediaTech public collections from AgentPublic.

Well-known public collections available on the Albert API, sourced from
https://huggingface.co/collections/AgentPublic/mediatech

These datasets are chunked, vectorized, and ready to use in RAG pipelines.
Collection IDs are specific to the Albert API instance — use
``rag-facile collections list --public`` to discover current IDs.

Once IDs are known, add them to ragfacile.toml::

    [storage]
    collections = [42, 87]
"""

from __future__ import annotations

from typing import TypedDict


class MediaTechEntry(TypedDict):
    """Metadata for a MediaTech collection."""

    description: str
    presets: list[str]


#: Maps dataset name → metadata.
#: Names match the HuggingFace dataset names at AgentPublic/<name>.
MEDIATECH_CATALOG: dict[str, MediaTechEntry] = {
    "legi": {
        "description": "Législation française (codes, lois, décrets)",
        "presets": ["legal"],
    },
    "constit": {
        "description": "Conseil constitutionnel (décisions, textes fondamentaux)",
        "presets": ["legal"],
    },
    "cnil": {
        "description": "Commission nationale de l'informatique et des libertés",
        "presets": ["legal"],
    },
    "dole": {
        "description": "Direction de l'information légale et administrative",
        "presets": ["legal"],
    },
    "travail-emploi": {
        "description": "Droit du travail et de l'emploi",
        "presets": ["hr"],
    },
    "service-public": {
        "description": "Fiches pratiques Service-Public.fr",
        "presets": ["balanced", "fast", "accurate"],
    },
    "local-administrations-directory": {
        "description": "Annuaire des administrations locales",
        "presets": ["balanced"],
    },
    "state-administrations-directory": {
        "description": "Annuaire des administrations de l'État",
        "presets": ["balanced"],
    },
    "data-gouv-datasets-catalog": {
        "description": "Catalogue des jeux de données data.gouv.fr",
        "presets": ["balanced"],
    },
}
