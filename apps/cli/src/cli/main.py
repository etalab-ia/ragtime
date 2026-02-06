from importlib.metadata import version as get_version
from typing import Optional

import typer
from rich.console import Console

from cli.commands import setup, generate_dataset

console = Console()

BANNER = """[magenta]
 ██████╗  █████╗  ██████╗     ███████╗ █████╗  ██████╗██╗██╗     ███████╗
 ██╔══██╗██╔══██╗██╔════╝     ██╔════╝██╔══██╗██╔════╝██║██║     ██╔════╝
 ██████╔╝███████║██║  ███╗    █████╗  ███████║██║     ██║██║     █████╗
 ██╔══██╗██╔══██║██║   ██║    ██╔══╝  ██╔══██║██║     ██║██║     ██╔══╝
 ██║  ██║██║  ██║╚██████╔╝    ██║     ██║  ██║╚██████╗██║███████╗███████╗
 ╚═╝  ╚═╝╚═╝  ╚═╝ ╚═════╝     ╚═╝     ╚═╝  ╚═╝ ╚═════╝╚═╝╚══════╝╚══════╝
[/magenta]"""

app = typer.Typer(
    add_completion=False,
    invoke_without_command=True,
    no_args_is_help=True,
    help="RAG Facile CLI - Build RAG applications for the French government",
)


@app.callback()
def main_callback(
    version: Optional[bool] = typer.Option(
        None,
        "--version",
        "-v",
        help="Show the CLI version and exit",
    ),
) -> None:
    """RAG Facile CLI - Build RAG applications for the French government."""
    try:
        console.print(BANNER)
    except UnicodeEncodeError:
        # Skip banner if terminal doesn't support Unicode (e.g., Git Bash on Windows with cp1252)
        pass

    if version:
        cli_version = get_version("rag-facile-cli")
        console.print(f"[cyan]rag-facile v{cli_version}[/cyan]")
        raise typer.Exit()


# Register commands in alphabetical order
app.command(
    name="generate-dataset",
    help="Generate synthetic Q/A evaluation dataset from documents",
)(generate_dataset.run)

app.command(name="setup", help="Setup a new workspace")(setup.run)


if __name__ == "__main__":
    app()
