import typer
from rich.console import Console

from rag_eval.commands import search, sources

console = Console()

BANNER = """[cyan]
 ██████╗  █████╗  ██████╗     ███████╗██╗   ██╗ █████╗ ██╗
 ██╔══██╗██╔══██╗██╔════╝     ██╔════╝██║   ██║██╔══██╗██║
 ██████╔╝███████║██║  ███╗    █████╗  ██║   ██║███████║██║
 ██╔══██╗██╔══██║██║   ██║    ██╔══╝  ╚██╗ ██╔╝██╔══██║██║
 ██║  ██║██║  ██║╚██████╔╝    ███████╗ ╚████╔╝ ██║  ██║███████╗
 ╚═╝  ╚═╝╚═╝  ╚═╝ ╚═════╝     ╚══════╝  ╚═══╝  ╚═╝  ╚═╝╚══════╝
[/cyan]"""

app = typer.Typer(
    add_completion=False,
    help="RAG Evaluation CLI - Search and manage evaluation datasets",
)


@app.callback()
def main_callback():
    """Print banner when CLI is invoked."""
    console.print(BANNER)


app.add_typer(search.app, name="search")
app.command(name="sources")(sources.list_sources)


@app.command()
def version():
    """Show the current version."""
    from rag_eval import __version__

    console.print(f"rag-eval v{__version__}")


if __name__ == "__main__":
    app()
