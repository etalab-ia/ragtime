"""Evaluation commands for RAG Facile CLI."""

import typer

from cli.commands.eval import generate, search, sources

app = typer.Typer(
    help="Search, generate, and manage evaluation datasets",
    add_completion=False,
    invoke_without_command=True,
    no_args_is_help=True,
)

app.add_typer(search.app, name="search")
app.command(name="sources")(sources.list_sources)
app.command(name="generate")(generate.run)
