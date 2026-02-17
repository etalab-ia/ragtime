"""Set configuration values via CLI."""

from pathlib import Path

import typer
from pydantic import ValidationError
from rich.console import Console

from rag_facile.core import load_config_or_default, parse_value, save_config


console = Console()


def set_value(
    key: str = typer.Argument(
        ...,
        help="Config key in dot notation (e.g., generation.model)",
    ),
    value: str = typer.Argument(
        ...,
        help="Value to set",
    ),
    config_path: str = typer.Option(
        "ragfacile.toml",
        "--config",
        "-c",
        help="Path to configuration file",
    ),
    create: bool = typer.Option(
        False,
        "--create",
        help="Create config file if it doesn't exist",
    ),
) -> None:
    """Set a configuration value.

    Updates a configuration value and saves it to the config file.
    The key should be in dot notation (e.g., generation.model).

    Examples:
        # Set generation model
        rag-facile config set generation.model openweight-large

        # Set temperature
        rag-facile config set generation.temperature 0.5

        # Enable hallucination detection
        rag-facile config set hallucination.enabled true

        # Set retrieval top_k
        rag-facile config set retrieval.top_k 20
    """
    path = Path(config_path)

    # Check if file exists
    if not path.exists() and not create:
        console.print(f"[red]✗ Configuration file not found: {config_path}[/red]")
        console.print("[dim]💡 Use --create to create a new config file[/dim]")
        console.print(
            "[dim]💡 Or apply a preset: rag-facile config preset apply balanced[/dim]"
        )
        raise typer.Exit(1)

    try:
        # Load existing config or create new one
        config = load_config_or_default(config_path)

        # Parse key path
        key_parts = key.split(".")
        if len(key_parts) < 2:
            console.print(f"[red]✗ Invalid key format: {key}[/red]")
            console.print(
                "[dim]💡 Use dot notation: section.field (e.g., generation.model)[/dim]"
            )
            raise typer.Exit(1)

        section = key_parts[0]
        field_path = key_parts[1:]

        # Validate section exists
        if not hasattr(config, section):
            console.print(f"[red]✗ Unknown section: {section}[/red]")
            available = [attr for attr in dir(config) if not attr.startswith("_")]
            console.print(f"Available sections: {', '.join(available)}")
            raise typer.Exit(1)

        # Navigate to the nested field
        current = getattr(config, section)
        for part in field_path[:-1]:
            if not hasattr(current, part):
                console.print(
                    f"[red]✗ Unknown field: {'.'.join(key_parts[: key_parts.index(part) + 1])}[/red]"
                )
                raise typer.Exit(1)
            current = getattr(current, part)

        # Get field name
        field_name = field_path[-1]

        if not hasattr(current, field_name):
            console.print(f"[red]✗ Unknown field: {key}[/red]")
            raise typer.Exit(1)

        # Parse value
        parsed_value = parse_value(value)

        # Get old value for comparison
        old_value = getattr(current, field_name)

        # Set new value
        setattr(current, field_name, parsed_value)

        # Validate entire config (this will raise if type is wrong)
        save_config(config, config_path)

        # Success
        console.print(f"[green]✓ Updated {key}[/green]")
        console.print(f"  [dim]Old value:[/dim] {old_value}")
        console.print(f"  [dim]New value:[/dim] {parsed_value}")
        console.print(f"  [dim]Saved to:[/dim] {config_path}")

    except ValidationError as e:
        console.print("[red]✗ Validation error:[/red]")
        for error in e.errors():
            location = " → ".join(str(loc) for loc in error["loc"])
            console.print(f"  {location}: {error['msg']}")
        raise typer.Exit(1)

    except Exception as e:
        console.print(f"[red]✗ Error: {e}[/red]")
        raise typer.Exit(1)
