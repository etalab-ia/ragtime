"""rag-facile chat command.

start_chat() is the primary entry point — called from main.py when the user runs
`rag-facile` with no subcommand, or explicitly via `rag-facile chat`.
"""

from cli.commands.chat.agent import start_chat


def run() -> None:
    """Launch the interactive RAG assistant."""
    start_chat()


__all__ = ["run", "start_chat"]
