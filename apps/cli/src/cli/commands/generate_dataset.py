"""Generate synthetic Q/A evaluation datasets.

This module implements the Data Foundry feature - an agentic RAG evaluation
dataset generator that creates Question/Answer/Context triplets from French
government documents.
"""

import json
import logging
import os
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from rag_core import get_config


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
    agent_id: Annotated[
        str,
        typer.Option(
            "--agent-id",
            envvar="DATA_FOUNDRY_AGENT_ID",
            help="Data Foundry agent ID on Letta Cloud (for Letta provider)",
        ),
    ] = "",
    debug: Annotated[
        bool,
        typer.Option(
            "--debug",
            help="Enable debug logging (verbose output to file and console)",
        ),
    ] = False,
    output: Annotated[
        Path,
        typer.Option(
            "--output",
            "-o",
            help="Output JSONL file path",
        ),
    ] = Path("golden_dataset.jsonl"),
    provider: Annotated[
        str,
        typer.Option(
            "--provider",
            "-p",
            help="Data Foundry provider to use (letta or albert, default: from config)",
        ),
    ] = "",
    samples: Annotated[
        int | None,
        typer.Option(
            "--samples",
            "-n",
            help="Target number of Q/A pairs to generate (default: from config)",
        ),
    ] = None,
) -> None:
    """Generate synthetic Q/A evaluation dataset from documents.

    Uses a Data Foundry provider (Letta Cloud or Albert API) to generate
    high-quality Question/Answer/Context triplets in French from your documents.

    Example with Letta Cloud:
        rag-facile generate-dataset ./docs -o golden_dataset.jsonl -n 50 --provider letta

    Example with Albert API:
        rag-facile generate-dataset ./docs -o golden_dataset.jsonl -n 50 --provider albert
    """
    # Load config for defaults
    rag_config = get_config()

    # Use config defaults if CLI args not provided
    if not provider:
        provider = rag_config.eval.provider
    if samples is None:
        samples = rag_config.eval.target_samples

    # Validate provider is specified (either from CLI or config)
    if not provider:
        console.print("Error: --provider is required (letta or albert)")
        raise typer.Exit(1)

    if provider not in ("letta", "albert"):
        console.print(f"Error: Unknown provider '{provider}'. Use 'letta' or 'albert'.")
        raise typer.Exit(1)

    # Validate provider-specific requirements
    if provider == "letta":
        api_key = os.getenv("LETTA_API_KEY")
        if not api_key:
            console.print("Error: LETTA_API_KEY environment variable is required.")
            console.print("Get your API key at https://app.letta.com/api-keys")
            raise typer.Exit(1)

        if not agent_id:
            console.print(
                "Error: DATA_FOUNDRY_AGENT_ID environment variable "
                "or --agent-id is required."
            )
            raise typer.Exit(1)
    elif provider == "albert":
        api_key = os.getenv("OPENAI_API_KEY")
        base_url = os.getenv("OPENAI_BASE_URL")
        model = os.getenv("OPENAI_MODEL") or rag_config.generation.model

        env_vars_to_check = {
            "OPENAI_API_KEY": api_key,
            "OPENAI_BASE_URL": base_url,
            "OPENAI_MODEL": model,
        }
        missing = [k for k, v in env_vars_to_check.items() if not v]
        if missing:
            console.print(
                f"Error: Missing environment variables for 'albert' provider: "
                f"{', '.join(missing)}"
            )
            if "OPENAI_MODEL" in missing:
                console.print(
                    "\nTip: OPENAI_MODEL can be set via environment variable or "
                    "in ragfacile.toml under [generation] section"
                )
            raise typer.Exit(1)

    # Find documents
    documents = [
        f
        for f in input_dir.iterdir()
        if f.is_file() and f.suffix.lower() in DOC_EXTENSIONS
    ]

    if not documents:
        console.print(f"No documents found in {input_dir}")
        console.print(f"Supported formats: {', '.join(DOC_EXTENSIONS)}")
        raise typer.Exit(1)

    console.print("\n[cyan]Data Foundry[/cyan] - Synthetic RAG Evaluation Generator\n")
    console.print(f"  Documents: {len(documents)} files in {input_dir}")
    console.print(f"  Provider: {provider}")
    console.print(f"  Target: {samples} Q/A pairs")
    console.print(f"  Output: {output}\n")

    # Setup logging to trace provider interactions
    log_file = Path(str(output) + ".log")
    log_level = logging.DEBUG if debug else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler() if debug else logging.NullHandler(),
        ],
    )
    logger = logging.getLogger("generate-dataset")
    logger.info("Starting generate-dataset session")
    logger.info(f"Provider: {provider}")
    logger.info(f"Debug mode: {'enabled' if debug else 'disabled'}")
    logger.info(f"Input directory: {input_dir}")
    logger.info(f"Output file: {output}")
    logger.info(f"Log file: {log_file}")
    logger.info(f"Documents found: {len(documents)}")
    for doc in documents:
        logger.debug(f"  - {doc.name}")

    # Get provider instance
    try:
        from cli.commands.providers import get_provider

        if provider == "letta":
            provider_instance = get_provider(
                "letta", api_key=api_key, agent_id=agent_id
            )
        else:  # albert
            provider_instance = get_provider(
                "albert", api_key=api_key, base_url=base_url, model=model
            )
    except ImportError as e:
        console.print(f"Error: {e}")
        raise typer.Exit(1)

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        # Upload documents
        task = progress.add_task("Uploading documents...", total=None)
        provider_instance.upload_documents([str(doc) for doc in documents])
        progress.remove_task(task)

    # Print debug info (provider-specific IDs for debugging)
    if debug:
        if hasattr(provider_instance, "folder_id") and provider_instance.folder_id:
            console.print(f"Debug - Letta Folder ID: {provider_instance.folder_id}")
        if (
            hasattr(provider_instance, "collection_id")
            and provider_instance.collection_id
        ):
            console.print(
                f"Debug - Albert Collection ID: {provider_instance.collection_id}"
            )

    # Generate samples
    console.print("[cyan]Generating samples...[/cyan]\n")

    generated_samples = []
    samples_started = False
    try:
        for sample in provider_instance.generate(samples):
            # Print conversation ID on first sample (for Letta provider debugging)
            if (
                not samples_started
                and debug
                and hasattr(provider_instance, "conversation_id")
                and provider_instance.conversation_id
            ):
                console.print(
                    f"Debug - Letta Conversation ID: "
                    f"{provider_instance.conversation_id}\n"
                )
                samples_started = True

            generated_samples.append(sample)
            console.print(
                f"  [green]Sample {len(generated_samples)}:[/green] "
                f"{sample.user_input[:60]}..."
            )
    finally:
        # Always cleanup
        provider_instance.cleanup()

    # Write output file
    if generated_samples:
        with open(output, "w", encoding="utf-8") as f:
            for sample in generated_samples:
                f.write(json.dumps(sample.to_dict(), ensure_ascii=False) + "\n")

        console.print(
            f"\n[green]Success![/green] Generated {len(generated_samples)} samples"
        )
        console.print(f"Output saved to: {output}")
    else:
        console.print("\n[yellow]Warning: No samples were generated.[/yellow]")
        console.print("The agent response may not have contained valid JSON samples.")
