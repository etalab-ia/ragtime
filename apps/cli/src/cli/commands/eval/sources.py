"""List known dataset sources for RAG evaluation."""

from typing import TypedDict

from rich.console import Console
from rich.table import Table

console = Console()


class DatasetSource(TypedDict):
    """Type definition for a dataset source."""

    name: str
    type: str
    url: str
    description: str
    datasets: list[str]


# Known dataset sources for French government RAG evaluation
KNOWN_SOURCES: list[DatasetSource] = [
    {
        "name": "AgentPublic",
        "type": "HuggingFace Organization",
        "url": "https://huggingface.co/AgentPublic",
        "description": "Official French government AI datasets (MediaTech collection)",
        "datasets": [
            "AgentPublic/legi",
            "AgentPublic/travail-emploi",
            "AgentPublic/service-public",
        ],
    },
    {
        "name": "Compar:IA",
        "type": "HuggingFace Organization",
        "url": "https://huggingface.co/ministere-culture",
        "description": "French Ministry of Culture chatbot arena - preferences & conversations",
        "datasets": [
            "ministere-culture/comparia-conversations",
            "ministere-culture/comparia-votes",
            "ministere-culture/comparia-reactions",
        ],
    },
    {
        "name": "Letta Evals",
        "type": "GitHub Repository",
        "url": "https://github.com/letta-ai/letta-evals",
        "description": "Example evaluation datasets from Letta",
        "datasets": [],
    },
    {
        "name": "MTEB French",
        "type": "Benchmark",
        "url": "https://huggingface.co/spaces/mteb/leaderboard",
        "description": "Massive Text Embedding Benchmark - French subset",
        "datasets": [],
    },
    {
        "name": "BEIR",
        "type": "Benchmark",
        "url": "https://github.com/beir-cellar/beir",
        "description": "Benchmarking IR - standard retrieval evaluation datasets",
        "datasets": [],
    },
]


def list_sources():
    """List known dataset sources for RAG evaluation."""
    table = Table(
        title="Known Dataset Sources",
        show_header=True,
        header_style="bold cyan",
    )
    table.add_column("Name", style="green")
    table.add_column("Type", style="yellow")
    table.add_column("Description")
    table.add_column("URL", style="blue")

    for source in KNOWN_SOURCES:
        table.add_row(
            source["name"],
            source["type"],
            source["description"],
            source["url"],
        )

    console.print(table)

    # Show highlighted datasets from key sources (find by name, not index)
    for source in KNOWN_SOURCES:
        if source.get("datasets"):
            if source["name"] == "AgentPublic":
                console.print(
                    "\n[bold cyan]AgentPublic Datasets (MediaTech Collection):[/bold cyan]"
                )
                for dataset in source["datasets"]:
                    console.print(f"  - {dataset}")
            elif source["name"] == "Compar:IA":
                console.print(
                    "\n[bold cyan]Compar:IA Datasets (Preference Data):[/bold cyan]"
                )
                for dataset in source["datasets"]:
                    console.print(f"  - {dataset}")

    console.print(
        "\n[dim]Use 'rag-facile eval search hf <query>' to search HuggingFace datasets[/dim]"
    )
