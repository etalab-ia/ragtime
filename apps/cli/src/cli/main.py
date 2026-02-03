from importlib.metadata import version as get_version

import typer
from rich.console import Console

from cli.commands import eval, generate

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

app.add_typer(generate.app, name="generate", help="Generate workspaces and apps")
app.add_typer(eval.app, name="eval")


@app.command()
def version():
    """Show the CLI version."""
    print(f"rag-facile v{get_version('rag-facile-cli')}")


if __name__ == "__main__":
    app()
