"""Generate command - orchestrates workspace generation using Init + Patch."""

import os
import shutil
import subprocess
from pathlib import Path
from typing import Annotated

import questionary
import typer
from rich.console import Console

app = typer.Typer()
console = Console()


def setup_proto_paths() -> None:
    """Add proto bin and shims directories to PATH for this session."""
    proto_home = Path(os.environ.get("PROTO_HOME", Path.home() / ".proto"))
    proto_bin = proto_home / "bin"
    proto_shims = proto_home / "shims"

    proto_paths = f"{proto_shims}:{proto_bin}"
    if proto_paths not in os.environ.get("PATH", ""):
        os.environ["PATH"] = f"{proto_paths}:{os.environ.get('PATH', '')}"


def verify_tool(name: str) -> str | None:
    """Verify a tool is available and return its version, or None if not found."""
    if not shutil.which(name):
        return None
    try:
        result = subprocess.run(
            [name, "--version"], capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0:
            # Extract first line of version output
            return result.stdout.strip().split("\n")[0]
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass
    return None


def install_proto() -> bool:
    """Install proto using the official installer."""
    console.print("[yellow]Installing proto...[/yellow]")
    result = subprocess.run(
        ["bash", "-c", "bash <(curl -fsSL https://moonrepo.dev/install/proto.sh) --yes"],
        capture_output=False,
    )
    if result.returncode != 0:
        console.print("[red]Failed to install proto. Please install manually:[/red]")
        console.print(
            "[dim]bash <(curl -fsSL https://moonrepo.dev/install/proto.sh) --yes[/dim]"
        )
        return False

    # Update PATH to find the newly installed proto
    setup_proto_paths()
    return True


def install_via_proto(tool: str) -> bool:
    """Install a tool using proto."""
    console.print(f"[yellow]Installing {tool} via proto...[/yellow]")
    result = subprocess.run(["proto", "install", tool], capture_output=False)
    if result.returncode != 0:
        console.print(f"[red]Failed to install {tool}. Please install manually:[/red]")
        console.print(f"[dim]proto install {tool}[/dim]")
        return False
    return True


def ensure_toolchain() -> bool:
    """Ensure proto, moon, and uv are installed, installing them if needed."""
    # Add proto paths to PATH (in case already installed)
    setup_proto_paths()

    # 1. Ensure proto is installed
    version = verify_tool("proto")
    if version:
        console.print(f"[dim]✓ proto ({version})[/dim]")
    else:
        if not install_proto():
            return False
        version = verify_tool("proto")
        if not version:
            console.print("[red]proto installed but not working[/red]")
            return False
        console.print(f"[green]✓ proto installed ({version})[/green]")

    # 2. Ensure moon is installed
    version = verify_tool("moon")
    if version:
        console.print(f"[dim]✓ moon ({version})[/dim]")
    else:
        if not install_via_proto("moon"):
            return False
        version = verify_tool("moon")
        if not version:
            console.print("[red]moon installed but not working[/red]")
            return False
        console.print(f"[green]✓ moon installed ({version})[/green]")

    # 3. Ensure uv is installed
    version = verify_tool("uv")
    if version:
        console.print(f"[dim]✓ uv ({version})[/dim]")
    else:
        if not install_via_proto("uv"):
            return False
        version = verify_tool("uv")
        if not version:
            console.print("[red]uv installed but not working[/red]")
            return False
        console.print(f"[green]✓ uv installed ({version})[/green]")

    console.print()
    return True


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
    """Get the templates directory bundled with the CLI package."""
    # Templates are bundled in the package at cli/templates
    package_templates = Path(__file__).resolve().parent.parent / "templates"
    if package_templates.exists():
        return package_templates

    # Fallback: check if we're in the rag-facile repo (development mode)
    repo_root = Path(__file__).resolve().parents[5]
    local_templates = repo_root / ".moon" / "templates"
    if local_templates.exists():
        return local_templates

    raise FileNotFoundError(
        "Templates not found. This is a packaging error - please reinstall the CLI."
    )


def run_command(cmd: list[str], description: str, cwd: Path | None = None) -> bool:
    """Run a shell command and handle errors."""
    console.print(f"[dim]{' '.join(cmd)}[/dim]")
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=cwd)
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
    # 0. Ensure toolchain is installed (proto, moon, uv)
    if not ensure_toolchain():
        raise typer.Exit(1)

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
    # On macOS, /tmp resolves to /private/tmp - normalize for cleaner output
    target_display = str(target_path).replace("/private/tmp/", "/tmp/")

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

    # Prompt for environment configuration (use current env as defaults)
    console.print()
    console.print("[bold blue]Environment Configuration[/bold blue]")
    console.print(
        "[dim]These values will be saved to .env in your app directory.[/dim]"
    )
    console.print(
        "[dim]Get an API key at https://albert.sites.beta.gouv.fr/access/[/dim]"
    )
    console.print()

    env_config = {}

    env_config["openai_api_key"] = questionary.text(
        "OpenAI/Albert API Key:",
        default=os.getenv("OPENAI_API_KEY", ""),
    ).ask()
    if env_config["openai_api_key"] is None:
        console.print("[red]Aborted.[/red]")
        raise typer.Exit(1)

    env_config["openai_base_url"] = questionary.text(
        "OpenAI Base URL:",
        default=os.getenv("OPENAI_BASE_URL", "https://albert.api.etalab.gouv.fr/v1"),
    ).ask()
    if env_config["openai_base_url"] is None:
        console.print("[red]Aborted.[/red]")
        raise typer.Exit(1)

    env_config["openai_model"] = questionary.text(
        "Default model:",
        default=os.getenv("OPENAI_MODEL", "openweight-large"),
    ).ask()
    if env_config["openai_model"] is None:
        console.print("[red]Aborted.[/red]")
        raise typer.Exit(1)

    console.print()
    console.print("[bold blue]Configuration Summary[/bold blue]")
    console.print(f"  Target: {target_display}")
    console.print(f"  Frontend: {frontend_choice}")
    console.print(
        f"  Modules: {', '.join(selected_modules) if selected_modules else 'None'}"
    )
    console.print(f"  API: {env_config['openai_base_url']}")
    console.print()

    # Confirm
    if not questionary.confirm("Proceed with generation?", default=True).ask():
        console.print("[yellow]Aborted.[/yellow]")
        raise typer.Exit(0)

    # Get templates directory
    templates_dir = get_templates_dir()
    if not templates_dir.exists():
        console.print(
            f"[red]Error: Templates directory not found at {templates_dir}[/red]"
        )
        console.print(
            "[dim]Make sure you're running from within the rag-facile repository.[/dim]"
        )
        raise typer.Exit(1)

    # 2. Bootstrap with moon init
    console.print()
    console.print("[bold green]Step 1:[/bold green] Initializing Moon workspace...")
    if not target_path.exists():
        target_path.mkdir(parents=True)

    # moon init must be run from within the target directory
    if not run_command(
        ["moon", "init", "--yes"],
        "moon init",
        cwd=target_path,
    ):
        raise typer.Exit(1)
    console.print("[green]✓[/green] Moon workspace initialized")

    # 3. Apply system configuration patch
    console.print()
    console.print(
        "[bold green]Step 2:[/bold green] Applying RAG Facile configuration..."
    )

    # Copy templates to target (moon generate expects templates in the workspace)
    target_templates = target_path / ".moon" / "templates"
    if not target_templates.exists():
        target_templates.mkdir(parents=True)

    # Copy all templates to target workspace
    import shutil

    console.print(f"[dim]Copying templates from {templates_dir}[/dim]")
    for template_name in [
        "sys-config",
        "chainlit-chat",
        "reflex-chat",
        "pdf-context",
        "chroma-context",
    ]:
        src = templates_dir / template_name
        dst = target_templates / template_name
        if src.exists():
            if dst.exists():
                shutil.rmtree(dst)
            shutil.copytree(src, dst)
            console.print(f"[dim]  ✓ {template_name}[/dim]")
        else:
            console.print(f"[yellow]  ⚠ {template_name} not found at {src}[/yellow]")

    # Patch workspace.yml to add generator.templates BEFORE running moon generate
    # (moon needs this config to find templates, but sys-config template provides it)
    workspace_yml = target_path / ".moon" / "workspace.yml"
    if workspace_yml.exists():
        import yaml

        with open(workspace_yml) as f:
            config = yaml.safe_load(f) or {}
        if "generator" not in config:
            config["generator"] = {"templates": [".moon/templates"]}
            with open(workspace_yml, "w") as f:
                yaml.dump(config, f, default_flow_style=False)
            console.print("[dim]  ✓ Added generator.templates config[/dim]")

    # Run moon generate for sys-config (DEST is . since we're in the target)
    sys_config_cmd = ["moon", "generate", "sys-config", ".", "--defaults", "--force"]
    if not run_command(sys_config_cmd, "apply system config", cwd=target_path):
        raise typer.Exit(1)
    console.print("[green]✓[/green] System configuration applied")

    # 4. Generate the app with feature flags
    console.print()
    console.print(
        f"[bold green]Step 3:[/bold green] Generating {frontend_choice} app..."
    )

    frontend_template = FRONTENDS[frontend_choice]
    # Don't pass DEST - let template.yml destination be used
    app_cmd = ["moon", "generate", frontend_template, "--defaults"]
    if force:
        app_cmd.append("--force")

    # Add template variables and feature flags after --
    app_cmd.append("--")

    # Pass env config values to moon template
    app_cmd.append(f"--openai_api_key={env_config['openai_api_key']}")
    app_cmd.append(f"--openai_base_url={env_config['openai_base_url']}")
    app_cmd.append(f"--openai_model={env_config['openai_model']}")

    # Add feature flags (boolean variables passed as flags)
    if "PDF" in selected_modules:
        app_cmd.append("--use_pdf")
    if "Chroma" in selected_modules:
        app_cmd.append("--use_chroma")

    if not run_command(app_cmd, f"generate {frontend_template}", cwd=target_path):
        raise typer.Exit(1)
    console.print(f"[green]✓[/green] {frontend_choice} app generated")

    # Create .env file from template values
    app_dir = target_path / "apps" / frontend_template
    env_file = app_dir / ".env"
    env_content = f"""\
OPENAI_API_KEY={env_config["openai_api_key"]}
OPENAI_BASE_URL={env_config["openai_base_url"]}
OPENAI_MODEL={env_config["openai_model"]}
"""
    env_file.write_text(env_content)
    console.print("[green]✓[/green] Created .env file")

    # 5. Generate selected packages
    if selected_modules:
        console.print()
        console.print("[bold green]Step 4:[/bold green] Generating packages...")

        for module in selected_modules:
            module_info = MODULES[module]
            if not module_info["available"]:
                console.print(
                    f"[yellow]⚠[/yellow] {module} is not yet available, skipping..."
                )
                continue

            template_name = str(module_info["template"])
            console.print(f"  Generating {module}...")
            # Don't pass DEST - let the template.yml destination be used
            pkg_cmd: list[str] = ["moon", "generate", template_name, "--defaults"]
            if force:
                pkg_cmd.append("--force")
            if not run_command(pkg_cmd, f"generate {template_name}", cwd=target_path):
                raise typer.Exit(1)
            console.print(f"  [green]✓[/green] {module} package generated")

    # Done with generation!
    console.print()
    console.print("[bold green]✨ Workspace generation complete![/bold green]")

    # Run uv sync to install dependencies
    console.print()
    console.print("[bold green]Step 5:[/bold green] Installing dependencies...")
    if not run_command(["uv", "sync"], "install dependencies", cwd=target_path):
        console.print("[yellow]Warning: uv sync failed. Run it manually.[/yellow]")

    # Start the dev server
    console.print()
    console.print(
        f"[bold green]Step 6:[/bold green] Starting {frontend_choice} dev server..."
    )
    console.print()
    console.print(f"[dim]Your app is at: {target_display}[/dim]")
    console.print()

    # Run dev server (this will block and show output)
    dev_cmd = ["moon", "run", f"{FRONTENDS[frontend_choice]}:dev"]
    subprocess.run(dev_cmd, cwd=target_path)


if __name__ == "__main__":
    app()
