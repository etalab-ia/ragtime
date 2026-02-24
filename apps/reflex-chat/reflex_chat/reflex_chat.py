"""The main Chat app."""

import reflex as rx

from reflex_chat.components import chat, navbar


def index() -> rx.Component:
    """The main app."""
    return rx.vstack(
        navbar(),
        chat.chat(),
        chat.action_bar(),
        background_color=rx.color("slate", 1),
        color=rx.color("slate", 12),
        height="100dvh",
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
