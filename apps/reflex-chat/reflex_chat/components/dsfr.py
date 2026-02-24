"""DSFR React component wrappers for Reflex.

Wraps @codegouvfr/react-dsfr Header and Footer as Reflex NoSSRComponents.

Key challenge: @codegouvfr/react-dsfr uses subpath exports
(@codegouvfr/react-dsfr/Header, /Footer, /spa) which npm/bun cannot install
as separate packages. Solution: use the root package for installation
and define thin local wrapper functions via _get_custom_code() that import
from the correct subpaths and call startReactDsfr() at module load time.
"""

import reflex as rx

# The actual installable npm package (not a subpath).
_DSFR_PACKAGE = "@codegouvfr/react-dsfr"

# Shared custom code: imports subpaths + initializes DSFR once.
_DSFR_INIT_AND_WRAPPERS = """
import { startReactDsfr } from "@codegouvfr/react-dsfr/spa";
import _DsfrHeaderBase from "@codegouvfr/react-dsfr/Header";
import _DsfrFooterBase from "@codegouvfr/react-dsfr/Footer";

startReactDsfr({ defaultColorScheme: "system" });

function RagFacileDsfrHeader({ brandTop, serviceTitle, serviceTagline }) {
  return (
    <_DsfrHeaderBase
      brandTop={<>{brandTop}</>}
      serviceTitle={serviceTitle}
      serviceTagline={serviceTagline}
      homeLinkProps={{ href: "/", title: "Accueil - " + serviceTitle }}
    />
  );
}

function RagFacileDsfrFooter({ brandTop, accessibility, contentDescription }) {
  return (
    <_DsfrFooterBase
      brandTop={<>{brandTop}</>}
      homeLinkProps={{ href: "/", title: "Accueil" }}
      accessibility={accessibility}
      contentDescription={contentDescription}
    />
  );
}
"""


class DsfrHeader(rx.NoSSRComponent):
    """Wraps DSFR Header via a local React wrapper function."""

    library: str = _DSFR_PACKAGE
    tag: str = "RagFacileDsfrHeader"

    brand_top: rx.Var[str]
    service_title: rx.Var[str]
    service_tagline: rx.Var[str]

    @classmethod
    def _get_custom_code(cls) -> str:
        return _DSFR_INIT_AND_WRAPPERS


class DsfrFooter(rx.NoSSRComponent):
    """Wraps DSFR Footer via a local React wrapper function."""

    library: str = _DSFR_PACKAGE
    tag: str = "RagFacileDsfrFooter"

    brand_top: rx.Var[str]
    accessibility: rx.Var[str]
    content_description: rx.Var[str]

    @classmethod
    def _get_custom_code(cls) -> str:
        return _DSFR_INIT_AND_WRAPPERS


def dsfr_header() -> rx.Component:
    """Render the DSFR government identity header."""
    return DsfrHeader.create(
        brand_top="République\nFrançaise",
        service_title="RAG Facile",
        service_tagline="Assistant RAG pour les services publics",
    )


def dsfr_footer() -> rx.Component:
    """Render the DSFR government identity footer."""
    return DsfrFooter.create(
        brand_top="République\nFrançaise",
        accessibility="non compliant",
        content_description=(
            "RAG Facile est un starter kit open source pour construire "
            "des assistants RAG pour les services publics français."
        ),
    )
