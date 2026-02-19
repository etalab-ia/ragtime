from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as get_version
from typing import Any, Optional

import click
import typer
from rich.console import Console

from cli.commands import (
    collections,
    config,
    generate_dataset,
    setup,
    uninstall,
    upgrade,
)


console = Console()

BANNER = """[magenta]
 ██████╗  █████╗  ██████╗     ███████╗ █████╗  ██████╗██╗██╗     ███████╗
 ██╔══██╗██╔══██╗██╔════╝     ██╔════╝██╔══██╗██╔════╝██║██║     ██╔════╝
 ██████╔╝███████║██║  ███╗    █████╗  ███████║██║     ██║██║     █████╗
 ██╔══██╗██╔══██║██║   ██║    ██╔══╝  ██╔══██║██║     ██║██║     ██╔══╝
 ██║  ██║██║  ██║╚██████╔╝    ██║     ██║  ██║╚██████╗██║███████╗███████╗
 ╚═╝  ╚═╝╚═╝  ╚═╝ ╚═════╝     ╚═╝     ╚═╝  ╚═╝ ╚═════╝╚═╝╚══════╝╚══════╝
[/magenta]"""


class AlphabeticalGroup(typer.core.TyperGroup):
    """Display commands in alphabetical order in help output."""

    def list_commands(self, ctx: click.Context) -> list[str]:
        return sorted(super().list_commands(ctx))

    def main(self, *args: Any, **kwargs: Any) -> Any:
        # Print banner and version before any argument parsing or error handling,
        # so they always appear regardless of subcommand validity.
        try:
            console.print(BANNER)
            try:
                cli_version = get_version("rag-facile-cli")
                console.print(f"[cyan]rag-facile v{cli_version}[/cyan]\n")
            except PackageNotFoundError:
                pass
        except Exception:
            # Skip if terminal doesn't support Unicode (e.g., Git Bash on Windows with cp1252)
            pass
        return super().main(*args, **kwargs)


app = typer.Typer(
    cls=AlphabeticalGroup,
    add_completion=False,
    invoke_without_command=True,
    help="RAG Facile CLI - Build RAG applications for the French government",
)


@app.callback()
def main_callback(
    ctx: typer.Context,
    version: Optional[bool] = typer.Option(
        None,
        "--version",
        "-v",
        help="Show the CLI version and exit",
    ),
) -> None:
    """RAG Facile CLI - Build RAG applications for the French government."""
    if version:
        raise typer.Exit()

    # Show help when no subcommand is given (banner + version already printed above).
    if ctx.invoked_subcommand is None:
        console.print(ctx.get_help())
        raise typer.Exit()


# Register commands in alphabetical order

# Collections command group
collections_app = typer.Typer(
    name="collections",
    help="Discover and manage Albert API collections",
    no_args_is_help=True,
)
collections_app.command("list", help="List accessible collections")(
    collections.list_collections
)
app.add_typer(collections_app, name="collections")

# Config command group
config_app = typer.Typer(
    name="config",
    help="Manage RAG configuration",
    no_args_is_help=True,
)
config_app.command("show", help="Display current configuration")(config.show)
config_app.command("validate", help="Validate configuration file")(config.validate)
config_app.command("set", help="Set configuration value")(config.set_value)
config_app.add_typer(
    config.preset(), name="preset", help="Manage configuration presets"
)
app.add_typer(config_app, name="config")

app.command(
    name="generate-dataset",
    help="Generate synthetic Q/A evaluation dataset from documents",
)(generate_dataset.run)

app.command(name="setup", help="Setup a new workspace")(setup.run)

app.command(
    name="uninstall", help="Remove the RAG Facile CLI (--all for toolchain too)"
)(uninstall.run)

app.command(name="upgrade", help="Upgrade to the latest version")(upgrade.run)


if __name__ == "__main__":
    app()
