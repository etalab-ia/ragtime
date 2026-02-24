"""DSFR React component wrappers for Reflex.

Simple direct wrappers with NO custom initialization code.
startReactDsfr() is called at app root level instead (see reflex_chat.py).
"""

import reflex as rx


class DsfrHeader(rx.NoSSRComponent):
    """DSFR Header component."""

    library: str = "@codegouvfr/react-dsfr"
    tag: str = "Header"
    is_default: bool = True

    brand_top: rx.Var[str]
    service_title: rx.Var[str]
    service_tagline: rx.Var[str]
    home_link_props: rx.Var[dict]


class DsfrFooter(rx.NoSSRComponent):
    """DSFR Footer component."""

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
