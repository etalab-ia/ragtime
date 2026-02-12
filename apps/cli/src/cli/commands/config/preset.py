"""Manage configuration presets."""

from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from rag_core import (
    apply_preset,
    compare_presets,
    get_preset_description,
    list_presets,
    load_preset,
)


console = Console()
app = typer.Typer(
    name="preset",
    help="Manage configuration presets",
    no_args_is_help=True,
)


@app.command("list")
def list_cmd() -> None:
    """List available configuration presets.

    Shows all available presets with descriptions and key characteristics.

    Example:
        rag-facile config preset list
    """
    presets = list_presets()

    table = Table(title="Available Presets", show_header=True, header_style="bold cyan")
    table.add_column("Preset", style="green", width=12)
    table.add_column("Description", style="white")

    for preset_name in presets:
        description = get_preset_description(preset_name)
        table.add_row(preset_name, description)

    console.print(table)
    console.print()
    console.print(
        "[dim]💡 Apply a preset with: rag-facile config preset apply <name>[/dim]"
    )
    console.print(
        "[dim]💡 Compare presets with: rag-facile config preset compare fast accurate[/dim]"
    )


@app.command("show")
def show(
    name: str = typer.Argument(
        ...,
        help="Preset name",
    ),
) -> None:
    """Show detailed preset configuration.

    Displays the complete configuration for a specific preset.

    Example:
        rag-facile config preset show legal
    """
    try:
        config = load_preset(name)
        console.print(f"[bold cyan]Preset: {name}[/bold cyan]")
        console.print(get_preset_description(name))
        console.print()

        # Key settings
        settings = [
            ("Generation Model", config.generation.model),
            ("Temperature", config.generation.temperature),
            ("Retrieval Method", config.retrieval.method),
            ("Retrieval Top K", config.retrieval.top_k),
            ("Reranking Enabled", config.reranking.enabled),
            (
                "Reranking Top N",
                config.reranking.top_n if config.reranking.enabled else "N/A",
            ),
            ("Hallucination Detection", config.hallucination.enabled),
        ]

        table = Table(show_header=True, header_style="bold")
        table.add_column("Setting", style="green")
        table.add_column("Value", style="yellow")

        for setting, value in settings:
            table.add_row(setting, str(value))

        console.print(table)
        console.print()
        console.print(
            f"[dim]💡 Apply this preset with: rag-facile config preset apply {name}[/dim]"
        )

    except ValueError as e:
        console.print(f"[red]✗ {e}[/red]")
        raise typer.Exit(1)


@app.command("apply")
def apply(
    name: str = typer.Argument(
        ...,
        help="Preset name",
    ),
    output: str = typer.Option(
        "ragfacile.toml",
        "--output",
        "-o",
        help="Output configuration file",
    ),
    force: bool = typer.Option(
        False,
        "--force",
        "-f",
        help="Overwrite existing file without confirmation",
    ),
) -> None:
    """Apply a configuration preset.

    Creates or overwrites a configuration file with the selected preset.
    By default, prompts for confirmation if the file already exists.

    Examples:
        # Apply balanced preset (default)
        rag-facile config preset apply balanced

        # Apply legal preset to custom location
        rag-facile config preset apply legal --output config/legal.toml

        # Force overwrite without confirmation
        rag-facile config preset apply accurate --force
    """
    output_path = Path(output)

    # Check if file exists and prompt for confirmation
    if output_path.exists() and not force:
        console.print(f"[yellow]⚠ File already exists: {output}[/yellow]")
        confirm = typer.confirm("Overwrite?")
        if not confirm:
            console.print("[dim]Cancelled[/dim]")
            raise typer.Exit(0)

    try:
        # Apply preset
        apply_preset(name, output)

        # Success
        console.print(f"[green]✓ Applied preset '{name}' to {output}[/green]")
        console.print(f"  [dim]Description:[/dim] {get_preset_description(name)}")
        console.print()
        console.print("[dim]💡 View config with: rag-facile config show[/dim]")
        console.print("[dim]💡 Validate config with: rag-facile config validate[/dim]")

    except ValueError as e:
        console.print(f"[red]✗ {e}[/red]")
        raise typer.Exit(1)
    except OSError as e:
        console.print(f"[red]✗ Error writing config file: {e}[/red]")
        raise typer.Exit(1)


@app.command("compare")
def compare(
    preset1: str = typer.Argument(
        ...,
        help="First preset name",
    ),
    preset2: str = typer.Argument(
        ...,
        help="Second preset name",
    ),
) -> None:
    """Compare two configuration presets.

    Shows differences between two presets to help choose the right one.

    Example:
        rag-facile config preset compare fast accurate
    """
    try:
        differences = compare_presets(preset1, preset2)

        if not differences:
            console.print(
                f"[green]✓ Presets '{preset1}' and '{preset2}' are identical[/green]"
            )
            return

        console.print(f"[bold]Comparing: {preset1} vs {preset2}[/bold]")
        console.print()

        table = Table(show_header=True, header_style="bold cyan")
        table.add_column("Setting", style="white")
        table.add_column(preset1, style="yellow")
        table.add_column(preset2, style="green")

        for field, (val1, val2) in sorted(differences.items()):
            table.add_row(field, str(val1), str(val2))

        console.print(table)
        console.print()
        console.print(
            "[dim]💡 Apply a preset with: rag-facile config preset apply <name>[/dim]"
        )

    except ValueError as e:
        console.print(f"[red]✗ {e}[/red]")
        raise typer.Exit(1)


def preset() -> typer.Typer:
    """Return the preset command group.

    This function exists for consistent imports in the parent module.
    """
    return app
