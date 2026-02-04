"""Generate synthetic Q/A evaluation datasets.

This module implements the Data Foundry feature - an agentic RAG evaluation
dataset generator that creates Question/Answer/Context triplets from French
government documents.
"""

import json
import os
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

console = Console()

# Supported document extensions
DOC_EXTENSIONS = {".pdf", ".md", ".txt"}


def run(
    input_dir: Annotated[
        Path,
        typer.Argument(
            help="Directory containing PDF/Markdown files to process",
            exists=True,
            file_okay=False,
            dir_okay=True,
            resolve_path=True,
        ),
    ],
    output: Annotated[
        Path,
        typer.Option(
            "--output",
            "-o",
            help="Output JSONL file path",
        ),
    ] = Path("golden_dataset.jsonl"),
    samples: Annotated[
        int,
        typer.Option(
            "--samples",
            "-n",
            help="Target number of Q/A pairs to generate",
        ),
    ] = 50,
    agent_id: Annotated[
        str,
        typer.Option(
            "--agent-id",
            envvar="DATA_FOUNDRY_AGENT_ID",
            help="Data Foundry agent ID on Letta Cloud",
        ),
    ] = "",
) -> None:
    """Generate synthetic Q/A evaluation dataset from documents.

    Uses the Data Foundry agent on Letta Cloud to generate high-quality
    Question/Answer/Context triplets in French from your documents.

    Example:
        rag-facile eval generate ./docs -o golden_dataset.jsonl -n 50
    """
    # Validate environment
    api_key = os.getenv("LETTA_API_KEY")
    if not api_key:
        console.print(
            "[red]Error: LETTA_API_KEY environment variable is required.[/red]"
        )
        console.print("[dim]Get your API key at https://app.letta.com/api-keys[/dim]")
        raise typer.Exit(1)

    if not agent_id:
        console.print(
            "[red]Error: DATA_FOUNDRY_AGENT_ID environment variable "
            "or --agent-id is required.[/red]"
        )
        raise typer.Exit(1)

    # Find documents
    documents = [
        f
        for f in input_dir.iterdir()
        if f.is_file() and f.suffix.lower() in DOC_EXTENSIONS
    ]

    if not documents:
        console.print(f"[yellow]No documents found in {input_dir}[/yellow]")
        console.print(f"[dim]Supported formats: {', '.join(DOC_EXTENSIONS)}[/dim]")
        raise typer.Exit(1)

    console.print("\n[cyan]Data Foundry[/cyan] - Synthetic RAG Evaluation Generator\n")
    console.print(f"  Documents: {len(documents)} files in {input_dir}")
    console.print(f"  Target: {samples} Q/A pairs")
    console.print(f"  Output: {output}\n")

    # Get provider
    try:
        from cli.commands.eval.providers import get_provider

        provider = get_provider("letta", api_key=api_key, agent_id=agent_id)
    except ImportError as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        # Upload documents
        task = progress.add_task("Uploading documents...", total=None)
        provider.upload_documents([str(doc) for doc in documents])
        progress.remove_task(task)

    # Generate samples
    console.print("[cyan]Generating samples...[/cyan]\n")

    generated_samples = []
    try:
        for sample in provider.generate(samples):
            generated_samples.append(sample)
            console.print(
                f"  [green]Sample {len(generated_samples)}:[/green] "
                f"{sample.user_input[:60]}..."
            )
    finally:
        # Always cleanup
        provider.cleanup()

    # Write output file
    if generated_samples:
        with open(output, "w", encoding="utf-8") as f:
            for sample in generated_samples:
                f.write(json.dumps(sample.to_dict(), ensure_ascii=False) + "\n")

        console.print(
            f"\n[green]Success![/green] Generated {len(generated_samples)} samples"
        )
        console.print(f"[dim]Output saved to: {output}[/dim]")
    else:
        console.print("\n[yellow]Warning: No samples were generated.[/yellow]")
        console.print(
            "[dim]The agent response may not have contained valid JSON samples.[/dim]"
        )
