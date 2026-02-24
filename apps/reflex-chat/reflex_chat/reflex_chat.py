"""The main Chat app."""

import reflex as rx

from reflex_chat.components import chat, navbar
from reflex_chat.dsfr_init import dsfr_footer, dsfr_header


def index() -> rx.Component:
    """The main app."""
    return rx.vstack(
        dsfr_header(),
        navbar(),
        chat.chat(),
        chat.action_bar(),
        dsfr_footer(),
        background_color=rx.color("slate", 1),
        color=rx.color("slate", 12),
        min_height="100dvh",
        align_items="stretch",
        spacing="0",
    )


# Add state and page to the app.
app = rx.App(
    theme=rx.theme(
        appearance="light",
        accent_color="blue",
        gray_color="slate",
        radius="small",
    ),
    stylesheets=["/dsfr-theme.css"],
)
app.add_page(index)
