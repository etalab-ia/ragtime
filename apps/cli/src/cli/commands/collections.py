"""List and discover Albert API collections."""

from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table


console = Console()


def list_collections(
    public: Annotated[
        bool,
        typer.Option("--public", help="Show only public collections"),
    ] = False,
    limit: Annotated[
        int,
        typer.Option("--limit", "-n", help="Maximum number of collections to show"),
    ] = 50,
) -> None:
    """List accessible collections on the Albert API.

    Requires ALBERT_API_KEY or OPENAI_API_KEY environment variable.

    Examples:
        # List all accessible collections
        rag-facile collections list

        # List only public collections
        rag-facile collections list --public

        # Limit results
        rag-facile collections list --public --limit 20
    """
    try:
        from albert import AlbertClient
    except ImportError:
        console.print("[red]✗ albert-client package is required.[/red]")
        console.print("[dim]Install with: uv pip install albert-client[/dim]")
        raise typer.Exit(1)

    # Initialize client (will raise if no API key)
    try:
        client = AlbertClient()
    except ValueError as e:
        console.print(f"[red]✗ {e}[/red]")
        console.print(
            "[dim]Set ALBERT_API_KEY or OPENAI_API_KEY environment variable.[/dim]"
        )
        raise typer.Exit(1)

    # Fetch collections
    visibility = "public" if public else None
    try:
        result = client.list_collections(visibility=visibility, limit=limit)
    except Exception as e:
        console.print(f"[red]✗ Failed to fetch collections: {e}[/red]")
        raise typer.Exit(1)

    collections = result.data
    if not collections:
        label = "public " if public else ""
        console.print(f"[yellow]No {label}collections found.[/yellow]")
        raise typer.Exit(0)

    # Build table
    title = "📚 Public Collections" if public else "📚 Collections"
    table = Table(title=title, expand=True)
    table.add_column("ID", style="cyan", no_wrap=True, min_width=6)
    table.add_column("Name", style="bold", min_width=20)
    table.add_column("Description", ratio=1)
    table.add_column("Docs", justify="right", no_wrap=True, min_width=6)
    table.add_column("Visibility", no_wrap=True, min_width=10)

    for col in collections:
        visibility_style = "green" if col.visibility == "public" else "dim"
        table.add_row(
            str(col.id),
            col.name or "—",
            col.description or "—",
            f"{col.documents:,}" if col.documents else "0",
            f"[{visibility_style}]{col.visibility or '—'}[/{visibility_style}]",
        )

    console.print()
    console.print(table)
    console.print()

    # Educational hint
    console.print(
        "[dim]💡 Add collections to your RAG pipeline in ragfacile.toml:[/dim]"
    )
    if collections:
        example_ids = [str(c.id) for c in collections[:2]]
        console.print(
            f'[dim]   rag-facile config set storage.collections "[{", ".join(example_ids)}]"[/dim]'
        )
