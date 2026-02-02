"""Generate command - orchestrates workspace generation using Init + Patch architecture."""

import subprocess
import sys
from pathlib import Path
from typing import Annotated

import questionary
import typer
from rich.console import Console

app = typer.Typer()
console = Console()

# Available frontends
FRONTENDS = {
    "Chainlit": "chainlit-chat",
    "Reflex": "reflex-chat",
}

# Available modules (packages)
MODULES = {
    "PDF": {"template": "pdf-context", "available": True},
    "Chroma": {"template": "chroma-context", "available": False},
}


def get_templates_dir() -> Path:
    """Get the templates directory from the rag-facile repository."""
    # When running from installed CLI, we need to find the templates
    # For now, assume we're running from within the rag-facile repo
    repo_root = Path(__file__).resolve().parents[5]
    return repo_root / ".moon" / "templates"


def run_command(cmd: list[str], description: str) -> bool:
    """Run a shell command and handle errors."""
    console.print(f"[dim]{' '.join(cmd)}[/dim]")
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        console.print(f"[red]Error: {description} failed[/red]")
        if result.stderr:
            console.print(f"[red]{result.stderr}[/red]")
        return False
    return True


@app.command()
def workspace(
    target: Annotated[
        str,
        typer.Argument(help="Target directory for the new workspace"),
    ] = "",
    force: Annotated[
        bool,
        typer.Option("--force", "-f", help="Overwrite existing files"),
    ] = False,
):
    """Generate a new RAG Facile workspace with interactive configuration.

    Uses the Init + Patch architecture:
    1. Bootstrap with `moon init`
    2. Apply RAG Facile configuration
    3. Generate selected app and packages
    """
    # 1. Gather inputs interactively
    if not target:
        target = questionary.text(
            "Target directory:",
            default="./my-rag-app",
        ).ask()
        if not target:
            console.print("[red]Aborted.[/red]")
            raise typer.Exit(1)

    target_path = Path(target).resolve()

    # Check if target exists and has content
    if target_path.exists() and any(target_path.iterdir()) and not force:
        overwrite = questionary.confirm(
            f"Directory {target_path} is not empty. Continue anyway?",
            default=False,
        ).ask()
        if not overwrite:
            console.print("[yellow]Aborted.[/yellow]")
            raise typer.Exit(0)

    # Select frontend
    frontend_choice = questionary.select(
        "Select your frontend app:",
        choices=list(FRONTENDS.keys()),
    ).ask()
    if not frontend_choice:
        console.print("[red]Aborted.[/red]")
        raise typer.Exit(1)

    # Select modules (multi-select)
    module_choices = questionary.checkbox(
        "Select modules to include:",
        choices=[
            questionary.Choice(
                f"{name} {'(Coming Soon)' if not info['available'] else ''}",
                value=name,
                disabled="Coming Soon" if not info["available"] else None,
            )
            for name, info in MODULES.items()
        ],
    ).ask()
    if module_choices is None:
        console.print("[red]Aborted.[/red]")
        raise typer.Exit(1)

    # Filter to only available modules
    selected_modules = [m for m in module_choices if MODULES[m]["available"]]

    console.print()
    console.print("[bold blue]Configuration Summary[/bold blue]")
    console.print(f"  Target: {target_path}")
    console.print(f"  Frontend: {frontend_choice}")
    console.print(f"  Modules: {', '.join(selected_modules) if selected_modules else 'None'}")
    console.print()

    # Confirm
    if not questionary.confirm("Proceed with generation?", default=True).ask():
        console.print("[yellow]Aborted.[/yellow]")
        raise typer.Exit(0)

    # Get templates directory
    templates_dir = get_templates_dir()
    if not templates_dir.exists():
        console.print(f"[red]Error: Templates directory not found at {templates_dir}[/red]")
        console.print("[dim]Make sure you're running from within the rag-facile repository.[/dim]")
        raise typer.Exit(1)

    force_flag = ["--force"] if force else []

    # 2. Bootstrap with moon init
    console.print()
    console.print("[bold green]Step 1:[/bold green] Initializing Moon workspace...")
    if not target_path.exists():
        target_path.mkdir(parents=True)

    if not run_command(
        ["moon", "init", str(target_path), "--yes"],
        "moon init",
    ):
        raise typer.Exit(1)
    console.print("[green]✓[/green] Moon workspace initialized")

    # 3. Apply system configuration patch
    console.print()
    console.print("[bold green]Step 2:[/bold green] Applying RAG Facile configuration...")

    # Copy templates to target (moon generate expects templates in the workspace)
    target_templates = target_path / ".moon" / "templates"
    if not target_templates.exists():
        target_templates.mkdir(parents=True)

    # Copy all templates to target workspace
    import shutil

    for template_name in ["sys-config", "chainlit-chat", "reflex-chat", "pdf-context", "chroma-context"]:
        src = templates_dir / template_name
        dst = target_templates / template_name
        if src.exists():
            if dst.exists():
                shutil.rmtree(dst)
            shutil.copytree(src, dst)

    # Run moon generate for sys-config
    if not run_command(
        ["moon", "generate", "sys-config", "--dest", str(target_path), "--force"],
        "apply system config",
    ):
        raise typer.Exit(1)
    console.print("[green]✓[/green] System configuration applied")

    # 4. Generate the app with feature flags
    console.print()
    console.print(f"[bold green]Step 3:[/bold green] Generating {frontend_choice} app...")

    frontend_template = FRONTENDS[frontend_choice]
    app_cmd = ["moon", "generate", frontend_template, "--dest", str(target_path)] + force_flag

    # Add feature flags based on selected modules
    if "PDF" in selected_modules:
        app_cmd.extend(["--var", "use_pdf=true"])
    if "Chroma" in selected_modules:
        app_cmd.extend(["--var", "use_chroma=true"])

    if not run_command(app_cmd, f"generate {frontend_template}"):
        raise typer.Exit(1)
    console.print(f"[green]✓[/green] {frontend_choice} app generated")

    # 5. Generate selected packages
    if selected_modules:
        console.print()
        console.print("[bold green]Step 4:[/bold green] Generating packages...")

        for module in selected_modules:
            module_info = MODULES[module]
            if not module_info["available"]:
                console.print(f"[yellow]⚠[/yellow] {module} is not yet available, skipping...")
                continue

            template_name = module_info["template"]
            console.print(f"  Generating {module}...")
            if not run_command(
                ["moon", "generate", template_name, "--dest", str(target_path)] + force_flag,
                f"generate {template_name}",
            ):
                raise typer.Exit(1)
            console.print(f"  [green]✓[/green] {module} package generated")

    # Done!
    console.print()
    console.print("[bold green]✨ Workspace generation complete![/bold green]")
    console.print()
    console.print("Next steps:")
    console.print(f"  cd {target_path}")
    console.print("  uv sync")
    console.print("  # Configure your .env file")
    console.print("  moon run chainlit-chat:dev  # or reflex-chat:dev")


if __name__ == "__main__":
    app()
