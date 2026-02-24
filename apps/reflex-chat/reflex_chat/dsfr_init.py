"""DSFR React component wrappers for Reflex.

Reflex v0.8.0+ uses Vite + React Router (SPA).
Initialization (DsfrInit) + header/footer components.

Architecture:
- DsfrInit: runs custom code once to init DSFR + import subcomponents
- DsfrHeader/Footer: reference the pre-initialized components without custom code
  (avoids Reflex issue #5923: duplicate identifier errors)
"""

import reflex as rx


# Custom code for DsfrInit: import + initialize DSFR + define wrappers
_DSFR_INIT_CODE = """
import { startReactDsfr } from "@codegouvfr/react-dsfr/spa";
import HeaderBase from "@codegouvfr/react-dsfr/Header";
import FooterBase from "@codegouvfr/react-dsfr/Footer";

// Initialize DSFR once at app startup
startReactDsfr({ defaultColorScheme: "system" });

// Export wrapped components for use by DsfrHeader/DsfrFooter
export const DsfrHeaderComponent = HeaderBase;
export const DsfrFooterComponent = FooterBase;
"""


class DsfrInit(rx.Component):
    """Initialize DSFR library at app startup.

    Renders as an empty fragment but injects custom code to initialize
    DSFR and import Header/Footer components. Must be placed at the top
    of the app before DsfrHeader/DsfrFooter.

    Workaround for Reflex issue #5923: duplicate identifier errors
    when multiple components define _get_custom_code().
    """

    library: str = "@codegouvfr/react-dsfr"
    tag: str = "Fragment"  # Render nothing visible

    @classmethod
    def _get_custom_code(cls) -> str:
        return _DSFR_INIT_CODE


class DsfrHeader(rx.NoSSRComponent):
    """DSFR Header component (Vite + React Router).

    Requires DsfrInit to be rendered first in the app.
    Initialized via DsfrInit._get_custom_code().
    """

    library: str = "@codegouvfr/react-dsfr"
    tag: str = "DsfrHeaderComponent"

    brand_top: rx.Var[str]
    service_title: rx.Var[str]
    service_tagline: rx.Var[str]
    home_link_props: rx.Var[dict]


class DsfrFooter(rx.NoSSRComponent):
    """DSFR Footer component (Vite + React Router).

    Requires DsfrInit to be rendered first in the app.
    Initialized via DsfrInit._get_custom_code().
    """

    library: str = "@codegouvfr/react-dsfr"
    tag: str = "DsfrFooterComponent"

    brand_top: rx.Var[str]
    accessibility: rx.Var[str]
    content_description: rx.Var[str]
    home_link_props: rx.Var[dict]


def dsfr_init() -> rx.Component:
    """Initialize DSFR at app startup (place at top of layout)."""
    return DsfrInit.create()


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
