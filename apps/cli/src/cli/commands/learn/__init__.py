"""rag-facile learn command.

start_chat() is the primary entry point — called from main.py when the user runs
`rag-facile learn`.
"""

from cli.commands.learn.agent import start_chat


def run(debug: bool = False) -> None:
    """Launch the interactive RAG assistant."""
    start_chat(debug=debug)


__all__ = ["run", "start_chat"]
