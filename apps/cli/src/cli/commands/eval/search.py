"""Search for evaluation datasets using HuggingFace Hub API."""

import os
from dataclasses import dataclass
from typing import Annotated, Optional

import typer
from dotenv import load_dotenv
from huggingface_hub import DatasetInfo, HfApi
from huggingface_hub.utils import HfHubHTTPError
from rich.console import Console
from rich.table import Table

load_dotenv()

console = Console()
app = typer.Typer(
    help="Search for evaluation datasets",
    invoke_without_command=True,
    no_args_is_help=True,
)


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
    task: str | None = None,
    task_id: str | None = None,
    language: str | None = None,
    limit: int = 20,
    sort: str = "downloads",
) -> list[DatasetResult]:
    """Search HuggingFace for datasets using the official Hub API.

    Args:
        query: Search query string (optional)
        author: Filter by author/organization (e.g., "AgentPublic")
        task: Filter by task category (e.g., "question-answering")
        task_id: Filter by specific task (e.g., "question-answering")
        language: Filter by language code (e.g., "fr" for French, "en" for English)
        limit: Maximum number of results to return
        sort: Sort order ("downloads", "likes", "created", "modified")

    Returns:
        List of matching datasets
    """
    api = HfApi()

    # list_datasets returns an iterator (sorting is always descending)
    # Modern huggingface_hub API (>=1.0) accepts filter parameters directly
    datasets_iter = api.list_datasets(
        search=query if query else None,
        author=author,
        task_categories=task,
        task_ids=task_id,
        language=language,
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
    task: Annotated[
        Optional[str],
        typer.Option(
            "--task", "-t", help="Filter by task (e.g., 'question-answering')"
        ),
    ] = None,
    task_id: Annotated[
        Optional[str],
        typer.Option("--task-id", help="Filter by specific task ID"),
    ] = None,
    language: Annotated[
        Optional[str],
        typer.Option(
            "--language", "-l", help="Filter by language code (e.g., 'fr', 'en')"
        ),
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
        rag-facile eval search hf "french QA"
        rag-facile eval search hf "RAG evaluation" --author AgentPublic
        rag-facile eval search hf "question" --task question-answering --language fr
        rag-facile eval search hf "legislation" -a AgentPublic -n 10
        rag-facile eval search hf "french" --sort likes
    """
    hf_token = os.getenv("HF_TOKEN")
    if not hf_token:
        console.print(
            "[yellow]Warning: HF_TOKEN not set. Some datasets may not be accessible.[/yellow]"
        )
        console.print("[dim]Set HF_TOKEN in your .env file for full access.[/dim]\n")

    with console.status(f"[cyan]Searching HuggingFace for '{query}'..."):
        try:
            datasets = search_huggingface(
                query,
                author=author,
                task=task,
                task_id=task_id,
                language=language,
                limit=limit,
                sort=sort,
            )
        except HfHubHTTPError as e:
            console.print(f"[red]Error searching HuggingFace: {e}[/red]")
            raise typer.Exit(1)

    title = f"HuggingFace Datasets: '{query}'"
    if author:
        title += f" (author: {author})"
    if task:
        title += f" (task: {task})"
    if language:
        title += f" (language: {language})"

    display_datasets(datasets, title=title)


@app.command(name="agent-public")
def search_agent_public(
    query: Annotated[
        Optional[str],
        typer.Argument(help="Optional search query within AgentPublic datasets"),
    ] = None,
    task: Annotated[
        Optional[str],
        typer.Option(
            "--task", "-t", help="Filter by task (e.g., 'question-answering')"
        ),
    ] = None,
    language: Annotated[
        Optional[str],
        typer.Option(
            "--language", "-l", help="Filter by language code (e.g., 'fr', 'en')"
        ),
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
        rag-facile eval search agent-public
        rag-facile eval search agent-public "legislation"
        rag-facile eval search agent-public --task question-answering --language fr
    """
    with console.status("[cyan]Searching AgentPublic datasets..."):
        try:
            datasets = search_huggingface(
                query,
                author="AgentPublic",
                task=task,
                language=language,
                limit=limit,
            )
        except HfHubHTTPError as e:
            console.print(f"[red]Error searching HuggingFace: {e}[/red]")
            raise typer.Exit(1)

    title = "AgentPublic Datasets (MediaTech Collection)"
    if task:
        title += f" - {task}"
    if language:
        title += f" ({language})"

    display_datasets(datasets, title=title)


@app.command(name="comparia")
def search_comparia(
    query: Annotated[
        Optional[str],
        typer.Argument(help="Optional search query within Compar:IA datasets"),
    ] = None,
    task: Annotated[
        Optional[str],
        typer.Option(
            "--task", "-t", help="Filter by task (e.g., 'question-answering')"
        ),
    ] = None,
    language: Annotated[
        Optional[str],
        typer.Option(
            "--language", "-l", help="Filter by language code (e.g., 'fr', 'en')"
        ),
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
        rag-facile eval search comparia
        rag-facile eval search comparia "votes"
        rag-facile eval search comparia --task question-answering --language fr
    """
    with console.status("[cyan]Searching Compar:IA datasets..."):
        try:
            datasets = search_huggingface(
                query,
                author="ministere-culture",
                task=task,
                language=language,
                limit=limit,
            )
        except HfHubHTTPError as e:
            console.print(f"[red]Error searching HuggingFace: {e}[/red]")
            raise typer.Exit(1)

    title = "Compar:IA Datasets (ministere-culture)"
    if task:
        title += f" - {task}"
    if language:
        title += f" ({language})"

    display_datasets(datasets, title=title)
