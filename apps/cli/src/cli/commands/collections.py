"""List and discover Albert API collections."""

from typing import Annotated

import httpx
import typer
from rich.console import Console
from rich.table import Table


console = Console()


def list_collections(
    limit: Annotated[
        int,
        typer.Option("--limit", "-n", help="Maximum number of collections to show"),
    ] = 50,
) -> None:
    """List accessible collections on the Albert API.

    Shows all collections you have access to, including public collections
    shared across the platform. Public collections (marked in green) can be
    added to your RAG pipeline configuration.

    Requires ALBERT_API_KEY or OPENAI_API_KEY environment variable.

    Examples:
        # List all accessible collections
        rag-facile collections list

        # Limit results
        rag-facile collections list --limit 20
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
    try:
        result = client.list_collections(limit=limit)
    except httpx.HTTPStatusError as e:
        console.print(f"[red]✗ Failed to fetch collections: {e}[/red]")
        raise typer.Exit(1)

    collections = result.data
    if not collections:
        console.print("[yellow]No collections found.[/yellow]")
        raise typer.Exit(0)

    # Build table
    table = Table(title="📚 Collections", expand=True)
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

    # Educational hint: show public collection IDs for easy copy-paste
    public_cols = [c for c in collections if c.visibility == "public"]
    if public_cols:
        public_ids = [str(c.id) for c in public_cols]
        console.print(
            "[dim]💡 Add public collections to your RAG pipeline in ragfacile.toml:[/dim]"
        )
        console.print(
            f'[dim]   rag-facile config set storage.collections "[{", ".join(public_ids)}]"[/dim]'
        )
    else:
        console.print(
            "[dim]💡 Add collection IDs to your RAG pipeline in ragfacile.toml:[/dim]"
        )
        example_ids = [str(c.id) for c in collections[:2]]
        console.print(
            f'[dim]   rag-facile config set storage.collections "[{", ".join(example_ids)}]"[/dim]'
        )
