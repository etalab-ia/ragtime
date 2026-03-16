from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as get_version
from typing import Any, Optional

import click
import typer
from rich.console import Console

from cli.commands import (
    collections,
    config,
    eval,
    generate_dataset,
    learn,
    setup,
    traces,
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


# Getting Started command definitions — single source of truth for both
# panel registration and sort-key logic in PanelAlphabeticalGroup.
_GETTING_STARTED_DEFS: dict[str, tuple] = {
    "learn": (
        learn.run,
        "Open the interactive RAG learning assistant",
    ),
    "setup": (setup.run, "Scaffold a new workspace (advanced)"),
}

_PANEL_GETTING_STARTED = "🚀 Getting Started"
_PANEL_ADVANCED_TOOLS = "🔧 Advanced Tools"


class PanelAlphabeticalGroup(typer.core.TyperGroup):
    """Sort commands by panel (Getting Started first), then alphabetically within each panel."""

    def list_commands(self, ctx: click.Context) -> list[str]:
        all_names = list(super().list_commands(ctx))
        return sorted(
            all_names,
            key=lambda n: (0 if n in _GETTING_STARTED_DEFS else 1, n),
        )

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
    cls=PanelAlphabeticalGroup,
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
    debug: bool = typer.Option(
        False,
        "--debug",
        help="Show agent tool calls and reasoning steps.",
        is_eager=False,
    ),
) -> None:
    """RAG Facile CLI - Build RAG applications for the French government."""
    if version:
        raise typer.Exit()

    # No subcommand → show help.
    if ctx.invoked_subcommand is None:
        console.print(ctx.get_help())
        raise typer.Exit()


# Register Getting Started commands first so their panel renders at the top
for _name, (_func, _help) in _GETTING_STARTED_DEFS.items():
    app.command(name=_name, help=_help, rich_help_panel=_PANEL_GETTING_STARTED)(_func)

# Advanced Tools — registered after Getting Started so their panel renders below

# Collections command group
collections_app = typer.Typer(
    name="collections",
    help="Discover and manage Albert API collections",
    no_args_is_help=True,
)
collections_app.command("list", help="List accessible collections")(
    collections.list_collections
)
app.add_typer(
    collections_app, name="collections", rich_help_panel=_PANEL_ADVANCED_TOOLS
)

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
app.add_typer(config_app, name="config", rich_help_panel=_PANEL_ADVANCED_TOOLS)

# Eval command group
eval_app = typer.Typer(
    name="eval",
    help="Run and view RAG evaluations (Inspect AI)",
    no_args_is_help=True,
)
eval_app.command("run", help="Run evaluation on a dataset")(eval.run)
eval_app.command("view", help="Open Inspect AI log viewer")(eval.view)
eval_app.command("list", help="List past evaluation runs")(eval.list_runs)
app.add_typer(eval_app, name="eval", rich_help_panel=_PANEL_ADVANCED_TOOLS)

app.command(
    name="generate-dataset",
    help="Generate synthetic Q/A evaluation dataset from documents",
    rich_help_panel=_PANEL_ADVANCED_TOOLS,
)(generate_dataset.run)

# Traces command group
_TRACES_COMMANDS: dict[str, tuple] = {
    "export": (traces.export_traces, "Export traces as JSONL"),
    "list": (traces.list_traces, "List recent traces"),
    "prune": (traces.prune_traces, "Delete traces older than N days"),
    "show": (traces.show_trace, "Show full detail of a trace"),
    "stats": (traces.stats_traces, "Show aggregate statistics"),
}
traces_app = typer.Typer(
    name="traces",
    help="Inspect and manage RAG pipeline traces",
    no_args_is_help=True,
)
for _name, (_func, _help) in _TRACES_COMMANDS.items():
    traces_app.command(name=_name, help=_help)(_func)
app.add_typer(traces_app, name="traces", rich_help_panel=_PANEL_ADVANCED_TOOLS)


if __name__ == "__main__":
    app()
