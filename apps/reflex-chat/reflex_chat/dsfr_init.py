"""DSFR React component wrappers for Reflex.

Reflex v0.8.0+ uses Vite + React Router (SPA).
Follows react-dsfr Vite setup pattern: call startReactDsfr() once in custom code.
"""

import reflex as rx


# Custom code injected via _get_custom_code() - runs at module load time
_DSFR_INIT_CODE = """
import { startReactDsfr } from "@codegouvfr/react-dsfr/spa";

// Initialize DSFR once at module load
startReactDsfr({ defaultColorScheme: "system" });
"""


class DsfrHeader(rx.NoSSRComponent):
    """DSFR Header component (Vite + React Router)."""

    library: str = "@codegouvfr/react-dsfr"
    tag: str = "Header"
    is_default: bool = True

    brand_top: rx.Var[str]
    service_title: rx.Var[str]
    service_tagline: rx.Var[str]
    home_link_props: rx.Var[dict]

    @classmethod
    def _get_custom_code(cls) -> str:
        return _DSFR_INIT_CODE


class DsfrFooter(rx.NoSSRComponent):
    """DSFR Footer component (Vite + React Router) — custom code via DsfrHeader."""

    library: str = "@codegouvfr/react-dsfr"
    tag: str = "Footer"
    is_default: bool = True

    brand_top: rx.Var[str]
    accessibility: rx.Var[str]
    content_description: rx.Var[str]
    home_link_props: rx.Var[dict]


def dsfr_header() -> rx.Component:
    """Render DSFR Header."""
    return DsfrHeader.create(
        brand_top="République\nFrançaise",
        service_title="RAG Facile",
        service_tagline="Assistant RAG pour les services publics",
        home_link_props={"href": "/", "title": "Accueil - RAG Facile"},
    )


def dsfr_footer() -> rx.Component:
    """Render DSFR Footer."""
    return DsfrFooter.create(
        brand_top="République\nFrançaise",
        accessibility="non compliant",
        content_description=(
            "RAG Facile est un starter kit open source pour construire "
            "des assistants RAG pour les services publics français."
        ),
        home_link_props={"href": "/", "title": "Accueil"},
    )
