"""Display current RAG configuration."""

import json
from typing import Literal, Optional

import typer
from pydantic import ValidationError
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table
from rich.text import Text

from rag_facile.core import (
    PIPELINE_STAGES,
    PipelineStage,
    flatten_model_fields,
    get_env_override_docs,
    load_config_or_default,
)


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


def _format_value(value: object) -> str:
    """Format a config value for display.

    Lists are joined with commas for readability instead of showing
    raw Python list syntax.
    """
    if isinstance(value, list):
        return ", ".join(str(item) for item in value)
    return str(value)


def _show_table(config_dict: dict, path: str) -> None:
    """Display configuration as formatted tables in RAG pipeline order.

    Each pipeline stage is shown with a step number, description, and a table
    of settings with their values and descriptions. This layout is designed to
    teach users about the RAG pipeline as they explore their configuration.
    """
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

    # Pre-compute all rows per stage so we can determine the widest setting
    # name across every table and use it as a fixed column width.
    stages_rows: list[tuple[int, PipelineStage, list[tuple[str, str, str]]]] = []
    setting_width = len("Setting")  # minimum: the column header itself

    for step_number, stage in enumerate(PIPELINE_STAGES, start=1):
        if stage.key not in config_dict:
            continue
        section_model = stage.model(**config_dict[stage.key])
        rows = [
            (key, _format_value(value), description)
            for key, value, description in flatten_model_fields(section_model)
        ]
        for key, _, _ in rows:
            setting_width = max(setting_width, len(key))
        stages_rows.append((step_number, stage, rows))

    for step_number, stage, rows in stages_rows:
        # Stage header: step number + emoji + title
        header = Text()
        header.append(f" {step_number}. ", style="bold blue")
        header.append(f"{stage.emoji} ", style="")
        header.append(stage.title, style="bold")
        console.print(header)

        # Stage description
        console.print(f"    [dim]{stage.description}[/dim]")
        console.print()

        # Build table with Setting / Value / Description columns.
        # expand=True makes all tables the same full-terminal width.
        # Setting uses a fixed min_width so the column aligns across tables.
        table = Table(
            show_header=True,
            header_style="bold cyan",
            pad_edge=False,
            expand=True,
        )
        table.add_column(
            "Setting", style="green", no_wrap=True, min_width=setting_width
        )
        table.add_column("Value", style="yellow", ratio=1)
        table.add_column("Description", style="dim", ratio=2)

        for key, value, description in rows:
            table.add_row(key, value, description)

        console.print(table)
        console.print()

    # Helpful tips
    console.print(
        "[dim]💡 Tip: Use --format toml or --format json for complete config[/dim]"
    )
    console.print("[dim]💡 Set RAG_<SECTION>_<KEY> env vars to override values[/dim]")
