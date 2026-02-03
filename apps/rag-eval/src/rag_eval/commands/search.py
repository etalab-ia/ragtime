"""Search for evaluation datasets using HuggingFace Hub API."""

import os
from dataclasses import dataclass
from typing import Annotated, Optional

import typer
from dotenv import load_dotenv
from huggingface_hub import HfApi, DatasetInfo
from huggingface_hub.utils import HfHubHTTPError
from rich.console import Console
from rich.table import Table

load_dotenv()

console = Console()
app = typer.Typer(help="Search for evaluation datasets")


@dataclass
class DatasetResult:
    """Simplified dataset result for display."""

    id: str
    author: str | None
    downloads: int
    likes: int
    tags: list[str]

    @property
    def url(self) -> str:
        return f"https://huggingface.co/datasets/{self.id}"

    @classmethod
    def from_dataset_info(cls, info: DatasetInfo) -> "DatasetResult":
        """Create from HuggingFace DatasetInfo."""
        return cls(
            id=info.id,
            author=info.author,
            downloads=info.downloads or 0,
            likes=info.likes or 0,
            tags=list(info.tags) if info.tags else [],
        )


def search_huggingface(
    query: str | None = None,
    *,
    author: str | None = None,
    limit: int = 20,
    sort: str = "downloads",
) -> list[DatasetResult]:
    """Search HuggingFace for datasets using the official Hub API.

    Args:
        query: Search query string (optional)
        author: Filter by author/organization (e.g., "AgentPublic")
        limit: Maximum number of results to return
        sort: Sort order ("downloads", "likes", "created", "modified")

    Returns:
        List of matching datasets
    """
    api = HfApi()

    # list_datasets returns an iterator (sorting is always descending)
    datasets_iter = api.list_datasets(
        search=query if query else None,
        author=author,
        sort=sort,
        limit=limit,
    )

    results = [DatasetResult.from_dataset_info(info) for info in datasets_iter]

    return results


def display_datasets(datasets: list[DatasetResult], title: str = "Search Results"):
    """Display datasets in a rich table."""
    if not datasets:
        console.print("[yellow]No datasets found.[/yellow]")
        return

    table = Table(
        title=title,
        show_header=True,
        header_style="bold cyan",
    )
    table.add_column("Dataset ID", style="green", no_wrap=True)
    table.add_column("Downloads", justify="right", style="yellow")
    table.add_column("Likes", justify="right", style="magenta")
    table.add_column("Tags", style="dim", max_width=40)

    for ds in datasets:
        # Truncate tags for display
        tags_str = ", ".join(ds.tags[:5])
        if len(ds.tags) > 5:
            tags_str += f" (+{len(ds.tags) - 5})"

        table.add_row(
            ds.id,
            f"{ds.downloads:,}",
            str(ds.likes),
            tags_str,
        )

    console.print(table)
    console.print(f"\n[dim]Found {len(datasets)} dataset(s)[/dim]")


@app.command(name="hf")
def search_hf(
    query: Annotated[str, typer.Argument(help="Search query for datasets")],
    author: Annotated[
        Optional[str],
        typer.Option("--author", "-a", help="Filter by author/organization"),
    ] = None,
    limit: Annotated[
        int,
        typer.Option("--limit", "-n", help="Maximum number of results"),
    ] = 20,
    sort: Annotated[
        str,
        typer.Option(
            "--sort", "-s", help="Sort by: downloads, likes, created, modified"
        ),
    ] = "downloads",
):
    """Search HuggingFace for evaluation datasets.

    Examples:
        rag-eval search hf "french QA"
        rag-eval search hf "RAG evaluation" --author AgentPublic
        rag-eval search hf "legislation" -a AgentPublic -n 10
        rag-eval search hf "french" --sort likes
    """
    hf_token = os.getenv("HF_TOKEN")
    if not hf_token:
        console.print(
            "[yellow]Warning: HF_TOKEN not set. Some datasets may not be accessible.[/yellow]"
        )
        console.print("[dim]Set HF_TOKEN in your .env file for full access.[/dim]\n")

    with console.status(f"[cyan]Searching HuggingFace for '{query}'..."):
        try:
            datasets = search_huggingface(query, author=author, limit=limit, sort=sort)
        except HfHubHTTPError as e:
            console.print(f"[red]Error searching HuggingFace: {e}[/red]")
            raise typer.Exit(1)

    title = f"HuggingFace Datasets: '{query}'"
    if author:
        title += f" (author: {author})"

    display_datasets(datasets, title=title)


@app.command(name="agent-public")
def search_agent_public(
    query: Annotated[
        Optional[str],
        typer.Argument(help="Optional search query within AgentPublic datasets"),
    ] = None,
    limit: Annotated[
        int,
        typer.Option("--limit", "-n", help="Maximum number of results"),
    ] = 50,
):
    """Search datasets from the AgentPublic organization (MediaTech collection).

    This is a convenience command that filters HuggingFace search to the
    AgentPublic organization, which hosts French government datasets.

    Examples:
        rag-eval search agent-public
        rag-eval search agent-public "legislation"
    """
    with console.status("[cyan]Searching AgentPublic datasets..."):
        try:
            datasets = search_huggingface(
                query,
                author="AgentPublic",
                limit=limit,
            )
        except HfHubHTTPError as e:
            console.print(f"[red]Error searching HuggingFace: {e}[/red]")
            raise typer.Exit(1)

    display_datasets(datasets, title="AgentPublic Datasets (MediaTech Collection)")


@app.command(name="comparia")
def search_comparia(
    query: Annotated[
        Optional[str],
        typer.Argument(help="Optional search query within Compar:IA datasets"),
    ] = None,
    limit: Annotated[
        int,
        typer.Option("--limit", "-n", help="Maximum number of results"),
    ] = 50,
):
    """Search datasets from Compar:IA (French Ministry of Culture chatbot arena).

    Compar:IA is a conversational AI comparison tool that collects user preferences
    and conversations across 30+ models. Useful for preference tuning and evaluation.

    Key datasets:
    - comparia-conversations: 289k+ questions & answers from real users
    - comparia-votes: 97k+ user preferences comparing two models
    - comparia-reactions: 59k+ message-level reactions

    Examples:
        rag-eval search comparia
        rag-eval search comparia "votes"
    """
    with console.status("[cyan]Searching Compar:IA datasets..."):
        try:
            datasets = search_huggingface(
                query,
                author="ministere-culture",
                limit=limit,
            )
        except HfHubHTTPError as e:
            console.print(f"[red]Error searching HuggingFace: {e}[/red]")
            raise typer.Exit(1)

    display_datasets(datasets, title="Compar:IA Datasets (ministere-culture)")
