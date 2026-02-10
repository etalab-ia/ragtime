"""Display current RAG configuration."""

import json
from typing import Literal, Optional

import typer
from pydantic import ValidationError
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table

from config import get_env_override_docs, load_config_or_default


console = Console()


def show(
    path: str = typer.Option(
        "ragfacile.toml",
        "--config",
        "-c",
        help="Path to configuration file",
    ),
    format: Literal["toml", "json", "table"] = typer.Option(
        "table",
        "--format",
        "-f",
        help="Output format (toml, json, table)",
    ),
    section: Optional[str] = typer.Option(
        None,
        "--section",
        "-s",
        help="Show only specific section (e.g., generation, retrieval)",
    ),
    env_docs: bool = typer.Option(
        False,
        "--env-docs",
        help="Show environment variable override documentation",
    ),
) -> None:
    """Display current RAG configuration.

    Shows the active configuration from ragfacile.toml and environment variables.
    Supports multiple output formats for different use cases.

    Examples:
        # Show full config as table (default)
        rag-facile config show

        # Show config as TOML
        rag-facile config show --format toml

        # Show only generation section
        rag-facile config show --section generation

        # Show environment variable docs
        rag-facile config show --env-docs
    """
    if env_docs:
        # Show environment variable documentation
        docs = get_env_override_docs()
        console.print(
            Panel(docs, title="Environment Variable Overrides", border_style="blue")
        )
        return

    try:
        # Load config (includes env var overrides)
        config = load_config_or_default(path)
        config_dict = config.model_dump()

        # Filter by section if requested
        if section:
            if section not in config_dict:
                console.print(f"[red]✗ Unknown section: {section}[/red]")
                console.print(f"Available sections: {', '.join(config_dict.keys())}")
                raise typer.Exit(1)
            config_dict = {section: config_dict[section]}

        # Format output
        if format == "toml":
            _show_toml(config_dict, path)
        elif format == "json":
            _show_json(config_dict)
        else:  # table
            _show_table(config_dict, path)

    except ValidationError as e:
        console.print("[red]✗ Configuration validation error:[/red]")
        for error in e.errors():
            location = " → ".join(str(loc) for loc in error["loc"])
            console.print(f"  {location}: {error['msg']}")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]✗ Error loading configuration: {e}[/red]")
        raise typer.Exit(1)


def _show_toml(config_dict: dict, path: str) -> None:
    """Display configuration as TOML."""
    import tomli_w

    toml_str = tomli_w.dumps(config_dict)
    syntax = Syntax(toml_str, "toml", theme="monokai", line_numbers=True)
    console.print(Panel(syntax, title=f"Configuration: {path}", border_style="green"))


def _show_json(config_dict: dict) -> None:
    """Display configuration as JSON."""
    json_str = json.dumps(config_dict, indent=2)
    syntax = Syntax(json_str, "json", theme="monokai", line_numbers=False)
    console.print(syntax)


def _show_table(config_dict: dict, path: str) -> None:
    """Display configuration as formatted table."""
    # Show file path and preset
    meta = config_dict.get("meta", {})
    preset = meta.get("preset", "custom")
    schema_version = meta.get("schema_version", "unknown")

    console.print(
        Panel(
            f"[bold]Config File:[/bold] {path}\n"
            f"[bold]Active Preset:[/bold] {preset}\n"
            f"[bold]Schema Version:[/bold] {schema_version}",
            title="Configuration Overview",
            border_style="blue",
        )
    )

    # Key sections to highlight
    sections = [
        ("generation", "Response Generation", ["model", "temperature", "max_tokens"]),
        ("retrieval", "Retrieval", ["method", "top_k", "score_threshold"]),
        ("reranking", "Reranking", ["enabled", "model", "top_n"]),
        ("embedding", "Embedding", ["model", "batch_size"]),
        ("chunking", "Chunking", ["strategy", "chunk_size", "chunk_overlap"]),
        (
            "hallucination",
            "Hallucination Detection",
            ["enabled", "method", "threshold"],
        ),
    ]

    for section_key, section_title, fields in sections:
        if section_key not in config_dict:
            continue

        section_data = config_dict[section_key]
        table = Table(title=section_title, show_header=True, header_style="bold cyan")
        table.add_column("Setting", style="green")
        table.add_column("Value", style="yellow")

        # Show highlighted fields
        for field in fields:
            if field in section_data:
                value = section_data[field]
                # Handle nested dicts
                if isinstance(value, dict):
                    value = str(value)
                table.add_row(field, str(value))

        # Show remaining fields
        for key, value in section_data.items():
            if key not in fields and not isinstance(value, dict):
                table.add_row(key, str(value))

        console.print(table)
        console.print()

    # Show note about env vars
    console.print(
        "[dim]💡 Tip: Use --format toml or --format json for complete config[/dim]"
    )
    console.print("[dim]💡 Set RAG_<SECTION>_<KEY> env vars to override values[/dim]")
