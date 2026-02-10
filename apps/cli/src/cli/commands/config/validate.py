"""Validate RAG configuration file."""

from pathlib import Path

import typer
from pydantic import ValidationError
from rich.console import Console

from config import RAGConfig, validate_config


console = Console()


def validate(
    path: str = typer.Option(
        "ragfacile.toml",
        "--config",
        "-c",
        help="Path to configuration file",
    ),
) -> None:
    """Validate RAG configuration file.

    Checks that the configuration file is valid TOML and passes all
    Pydantic validation rules. Reports detailed errors if validation fails.

    Examples:
        # Validate default config
        rag-facile config validate

        # Validate specific file
        rag-facile config validate --config custom.toml
    """
    config_path = Path(path)

    # Check file exists
    if not config_path.exists():
        console.print(f"[red]✗ Configuration file not found: {path}[/red]")
        console.print(
            "[dim]💡 Create one with: rag-facile config preset apply balanced[/dim]"
        )
        raise typer.Exit(1)

    try:
        # Validate configuration
        config = validate_config(path)

        # Success
        console.print(f"[green]✓ Configuration is valid: {path}[/green]")
        console.print(f"  [dim]Schema version:[/dim] {config.meta.schema_version}")
        console.print(f"  [dim]Active preset:[/dim] {config.meta.preset}")

        # Show warnings for common issues
        _show_warnings(config)

    except ValidationError as e:
        console.print(f"[red]✗ Configuration validation failed: {path}[/red]")
        console.print()

        for error in e.errors():
            location = " → ".join(str(loc) for loc in error["loc"])
            console.print(f"  [red]✗[/red] {location}")
            console.print(f"    {error['msg']}")
            console.print()

        raise typer.Exit(1)

    except Exception as e:
        console.print(f"[red]✗ Error reading configuration: {e}[/red]")
        raise typer.Exit(1)


def _show_warnings(config: RAGConfig) -> None:
    """Show warnings for potential configuration issues.

    Args:
        config: Validated RAG configuration to check
    """
    warnings = []

    # Check for common misconfigurations
    if config.reranking.enabled and config.retrieval.top_k < config.reranking.top_n:
        warnings.append(
            f"retrieval.top_k ({config.retrieval.top_k}) is less than "
            f"reranking.top_n ({config.reranking.top_n}). "
            "Reranking will have no effect."
        )

    if config.context.max_tokens > config.generation.max_tokens * 8:
        warnings.append(
            f"context.max_tokens ({config.context.max_tokens}) is very large "
            f"compared to generation.max_tokens ({config.generation.max_tokens}). "
            "This may cause context truncation issues."
        )

    if config.hallucination.enabled and config.hallucination.fallback == "regenerate":
        warnings.append(
            "hallucination.fallback is set to 'regenerate' which can cause infinite loops. "
            "Consider using 'warn' or 'reject' instead."
        )

    # Display warnings
    if warnings:
        console.print()
        console.print("[yellow]⚠ Warnings:[/yellow]")
        for warning in warnings:
            console.print(f"  [yellow]•[/yellow] {warning}")
