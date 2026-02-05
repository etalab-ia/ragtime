from importlib.metadata import version as get_version

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

# Print banner on every invocation
console.print(BANNER)

app = typer.Typer(
    add_completion=False,
    invoke_without_command=True,
    no_args_is_help=True,
    help="RAG Facile CLI - Build RAG applications for the French government",
)


def version():
    """Show the CLI version."""
    print(f"rag-facile v{get_version('rag-facile-cli')}")


# Register commands in alphabetical order
app.command(
    name="generate-dataset",
    help="Generate synthetic Q/A evaluation dataset from documents",
)(generate_dataset.run)

app.command(name="setup", help="Setup a new workspace")(setup.run)

app.command()(version)


if __name__ == "__main__":
    app()
