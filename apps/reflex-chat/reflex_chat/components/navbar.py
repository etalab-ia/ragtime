import reflex as rx
from reflex.style import set_color_mode

from reflex_chat.state import State


def sidebar_chat(chat: str) -> rx.Component:
    """A sidebar chat item.

    Args:
        chat: The chat item.
    """
    return rx.drawer.close(
        rx.hstack(
            rx.button(
                chat,
                on_click=lambda: State.set_chat(chat),
                width="80%",
                variant="surface",
            ),
            rx.button(
                rx.icon(
                    tag="trash",
                    on_click=State.delete_chat(chat),
                    stroke_width=1,
                ),
                width="20%",
                variant="surface",
                color_scheme="red",
            ),
            width="100%",
        ),
        key=chat,
    )


def sidebar(trigger) -> rx.Component:
    """The sidebar component."""
    # TODO: Fix Reflex component kwargs type errors (tracked for future PR)
    return rx.drawer.root(
        rx.drawer.trigger(trigger),  # type: ignore[missing-argument]
        rx.drawer.overlay(),  # type: ignore[missing-argument]
        rx.drawer.portal(  # type: ignore[missing-argument]
            rx.drawer.content(
                rx.vstack(
                    rx.heading("Conversations", color=rx.color("slate", 11)),
                    rx.divider(),
                    rx.foreach(State.chat_titles, lambda chat: sidebar_chat(chat)),
                    align_items="stretch",
                    width="100%",
                ),
                top="auto",
                right="auto",
                height="100%",
                width="20em",
                padding="2em",
                background_color=rx.color("slate", 2),
                outline="none",
            )
        ),
        direction="left",
    )


def modal(trigger) -> rx.Component:
    """A modal to create a new chat."""
    # TODO: Fix Reflex component kwargs type errors (tracked for future PR)
    return rx.dialog.root(
        rx.dialog.trigger(trigger),  # type: ignore[missing-argument]
        rx.dialog.content(
            rx.form(
                rx.hstack(
                    rx.input(
                        placeholder="Nom du chat",
                        name="new_chat_name",
                        flex="1",
                        min_width="20ch",
                    ),
                    rx.button("Nouveau chat"),
                    spacing="2",
                    wrap="wrap",
                    width="100%",
                ),
                on_submit=State.create_chat,
            ),
            background_color=rx.color("slate", 1),
        ),
        open=State.is_modal_open,
        on_open_change=State.set_is_modal_open,
    )


def theme_toggle() -> rx.Component:
    """DSFR-style theme switcher dropdown (Clair / Sombre / Systeme)."""
    return rx.menu.root(
        rx.menu.trigger(
            rx.icon_button(
                rx.color_mode_cond(
                    rx.icon("sun", size=18),
                    rx.icon("moon", size=18),
                ),
                variant="ghost",
                color_scheme="gray",
                cursor="pointer",
                size="2",
            ),
        ),
        rx.menu.content(
            rx.menu.item(
                rx.hstack(
                    rx.icon("sun", size=14),
                    rx.text("Theme clair"),
                    spacing="2",
                    align_items="center",
                ),
                on_click=set_color_mode("light"),
            ),
            rx.menu.item(
                rx.hstack(
                    rx.icon("moon", size=14),
                    rx.text("Theme sombre"),
                    spacing="2",
                    align_items="center",
                ),
                on_click=set_color_mode("dark"),
            ),
            rx.menu.item(
                rx.hstack(
                    rx.icon("monitor", size=14),
                    rx.text("Suivre le systeme"),
                    spacing="2",
                    align_items="center",
                ),
                on_click=set_color_mode("system"),
            ),
        ),
    )


def navbar():
    return rx.hstack(
        rx.badge(
            State.current_chat,
            rx.tooltip(
                rx.icon("info", size=14),
                content="La conversation en cours.",
            ),
            size="3",
            variant="solid",
            color_scheme="blue",
            margin_inline_end="auto",
        ),
        rx.hstack(
            modal(
                rx.icon_button("message-square-plus"),
            ),
            sidebar(
                rx.icon_button(
                    "messages-square",
                    background_color=rx.color("slate", 6),
                )
            ),
            theme_toggle(),
            gap="1rem",  # DSFR 4v between action buttons
            align_items="center",
        ),
        justify_content="space-between",
        align_items="center",
        padding="0.5rem 1rem",  # DSFR 2v / 4v
        border_bottom=f"1px solid {rx.color('slate', 3)}",
        background_color=rx.color("slate", 2),
    )
