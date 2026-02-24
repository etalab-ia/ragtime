"""DSFR initialization wrapper.

This module is imported at app startup to initialize DSFR before any
components try to render. Wraps Header and Footer with initialization.
"""

import reflex as rx


# Custom code that initializes DSFR and exports wrapped components
_DSFR_WRAPPER_CODE = """
import { startReactDsfr } from "@codegouvfr/react-dsfr/spa";
import HeaderBase from "@codegouvfr/react-dsfr/Header";
import FooterBase from "@codegouvfr/react-dsfr/Footer";

// Initialize DSFR at module load time (before anything renders)
startReactDsfr({ defaultColorScheme: "system" });

// Export wrapped components that are guaranteed to have DSFR initialized
export const Header = HeaderBase;
export const Footer = FooterBase;
"""


class DsfrHeader(rx.NoSSRComponent):
    """DSFR Header (initialized)."""

    library: str = "@codegouvfr/react-dsfr"
    tag: str = "Header"

    brand_top: rx.Var[str]
    service_title: rx.Var[str]
    service_tagline: rx.Var[str]
    home_link_props: rx.Var[dict]

    @classmethod
    def _get_custom_code(cls) -> str:
        return _DSFR_WRAPPER_CODE


class DsfrFooter(rx.NoSSRComponent):
    """DSFR Footer (initialized)."""

    library: str = "@codegouvfr/react-dsfr"
    tag: str = "Footer"

    brand_top: rx.Var[str]
    accessibility: rx.Var[str]
    content_description: rx.Var[str]
    home_link_props: rx.Var[dict]

    @classmethod
    def _get_custom_code(cls) -> str:
        return _DSFR_WRAPPER_CODE


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
