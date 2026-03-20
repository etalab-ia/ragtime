"""Setup new Ragtime standalone workspaces."""

import json
import os
import subprocess
import urllib.error
import urllib.request
from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as get_version
from pathlib import Path
from typing import Annotated, Literal, TypedDict

import questionary
import typer
from rich.console import Console


console = Console()


class PresetConfig(TypedDict):
    """Type definition for preset configuration."""

    description: str
    model_alias: str
    retrieval_module: str
    temperature: float
    language: Literal["fr", "en"]
    system_prompt: str
    openai_base_url: str


# GitHub repository URL for installing the library from source
_GITHUB_REPO = "https://github.com/etalab-ia/ragtime.git"

# GitHub API URL for fetching the latest release
_GITHUB_API_LATEST = "https://api.github.com/repos/etalab-ia/ragtime/releases/latest"

# Default .gitignore for generated projects
_GITIGNORE_CONTENT = """\
# Secrets — never commit these
.env
.env.*
!.env.example
!.env.template

# Python
__pycache__/
*.py[codz]
*.so
.Python

# Virtual environments
.venv/
venv/
env/
ENV/

# Distribution / packaging
build/
dist/
*.egg-info/
*.egg

# Testing
.coverage
.coverage.*
.pytest_cache/
htmlcov/

# Type checkers / linters
.mypy_cache/
.ruff_cache/
.pyre/

# IDEs
.vscode/
.idea/
*.swp
*.swo

# OS
.DS_Store
Thumbs.db

# Moon build system
.moon/cache
private/

# Chainlit
.chainlit/*
!.chainlit/config.toml
.files/

# Reflex
.web/
.states/
assets/external/
backend.zip
frontend.zip

# Databases
*.db
*.sqlite3

# Logs
*.log
"""


def _get_latest_release_tag() -> str | None:
    """Fetch the latest ragtime release tag from GitHub. Returns None on failure."""
    try:
        req = urllib.request.Request(
            _GITHUB_API_LATEST,
            headers={
                "Accept": "application/vnd.github+json",
                "User-Agent": "ragtime-cli",
            },
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read())
            return data.get("tag_name")
    except (urllib.error.URLError, json.JSONDecodeError):
        return None


def _get_library_git_ref() -> dict[str, str]:
    """Determine the git ref for ragtime-lib and albert-client sources.

    Returns a dict with either {"tag": "v0.19.0"} or {"branch": "main"}.
    Priority: RAG_FACILE_BRANCH env var > latest GitHub release > CLI version tag > "main" fallback.
    """
    # Dev/CI override: use branch from env var (same pattern as install.sh)
    branch = os.environ.get("RAG_FACILE_BRANCH")
    if branch:
        return {"branch": branch}

    # Prefer the latest published release so new workspaces always get the
    # most recent version, even when running an older CLI.
    latest_tag = _get_latest_release_tag()
    if latest_tag:
        return {"tag": latest_tag}

    # Offline fallback: use the version tag matching the installed CLI.
    try:
        cli_version = get_version("ragtime-cli")
        return {"tag": f"v{cli_version}"}
    except PackageNotFoundError:
        return {"branch": "main"}


# Available frontends
FRONTENDS = {
    "Chainlit": "chainlit-chat",
    "Reflex": "reflex-chat",
}

# Available modules (packages)
MODULES = {
    "Local": {"template": "retrieval", "available": True},
    "Albert RAG": {"template": "retrieval", "available": True},
}

# Configuration presets
PRESET_CONFIGS: dict[str, PresetConfig] = {
    "fast": {
        "description": "Fast responses, lower accuracy",
        "model_alias": "openweight-small",
        "retrieval_module": "Local",
        "temperature": 0.7,
        "language": "fr",
        "system_prompt": "Vous êtes un assistant utile et concis.",
        "openai_base_url": "https://albert.api.etalab.gouv.fr/v1",
    },
    "balanced": {
        "description": "Balanced speed and accuracy (recommended)",
        "model_alias": "openweight-medium",
        "retrieval_module": "Local",
        "temperature": 0.7,
        "language": "fr",
        "system_prompt": "Vous êtes un assistant utile.",
        "openai_base_url": "https://albert.api.etalab.gouv.fr/v1",
    },
    "accurate": {
        "description": "Best accuracy, slower responses",
        "model_alias": "openweight-large",
        "retrieval_module": "Local",
        "temperature": 0.7,
        "language": "fr",
        "system_prompt": "Vous êtes un assistant expert et précis.",
        "openai_base_url": "https://albert.api.etalab.gouv.fr/v1",
    },
    "legal": {
        "description": "Optimized for legal documents",
        "model_alias": "openweight-large",
        "retrieval_module": "Local",
        "temperature": 0.3,
        "language": "fr",
        "system_prompt": "Vous êtes un assistant spécialisé dans l'analyse de documents juridiques.",
        "openai_base_url": "https://albert.api.etalab.gouv.fr/v1",
    },
    "hr": {
        "description": "Optimized for HR documents",
        "model_alias": "openweight-medium",
        "retrieval_module": "Local",
        "temperature": 0.7,
        "language": "fr",
        "system_prompt": "Vous êtes un assistant spécialisé dans les ressources humaines.",
        "openai_base_url": "https://albert.api.etalab.gouv.fr/v1",
    },
}


def get_templates_dir() -> Path:
    """Get the templates directory bundled with the CLI package."""
    # Templates are bundled in the package at cli/templates
    package_templates = Path(__file__).resolve().parent.parent / "templates"
    # Check if it exists AND contains the expected frontend templates
    if package_templates.exists() and (package_templates / "chainlit-chat").exists():
        return package_templates

    # Fallback: check if we're in the ragtime repo (development mode)
    repo_root = Path(__file__).resolve().parents[5]
    local_templates = repo_root / ".moon" / "templates"
    if local_templates.exists():
        return local_templates

    raise FileNotFoundError(
        "Templates not found. This is a packaging error - please reinstall the CLI."
    )


def get_default_config_template() -> Path:
    """Get the default ragtime.toml template."""
    # Try bundled location (installed CLI)
    bundled = Path(__file__).resolve().parent.parent / "templates" / "ragtime.toml"
    if bundled.exists():
        return bundled

    # Try development location (repo structure)
    repo_root = Path(__file__).resolve().parents[5]
    dev = repo_root / "apps" / "cli" / "src" / "cli" / "templates" / "ragtime.toml"
    if dev.exists():
        return dev

    raise FileNotFoundError(
        "ragtime.toml template not found. This is a packaging error - please reinstall the CLI."
    )


def render_template_file(template_path: Path, variables: dict[str, str | bool]) -> str:
    """Render a template file with Tera-style variables.

    Handles simple variable substitution like {{ var }} and conditionals.
    For complex templates, we copy and do simple replacements.
    """
    content = template_path.read_text()

    # Simple variable substitution (Tera-style: {{ var }})
    for key, value in variables.items():
        if isinstance(value, bool):
            continue  # Skip booleans, handled by conditionals
        content = content.replace("{{ " + key + " }}", str(value))
        # Also handle filter syntax like {{ project_name | replace(from='-', to='_') }}
        snake_key = str(value).replace("-", "_")
        content = content.replace(
            "{{ " + key + " | replace(from='-', to='_') }}", snake_key
        )

    # Handle Tera conditionals: {%- if var %}...{%- endif %}
    import re

    # Process each conditional block
    for key, value in variables.items():
        if not isinstance(value, bool):
            continue

        # Pattern for {%- if var %}...{%- endif %}
        pattern = rf"\{{% ?-? ?if {key} ?%\}}(.*?)\{{% ?-? ?endif ?%\}}"
        if value:
            # Keep the content, remove the tags
            content = re.sub(pattern, r"\1", content, flags=re.DOTALL)
        else:
            # Remove the entire block
            content = re.sub(pattern, "", content, flags=re.DOTALL)

    return content


def generate_config_file(
    workspace_root: Path,
    preset: str,
    preset_config: PresetConfig,
    selected_modules: list[str] | None = None,
) -> None:
    """Generate ragtime.toml at workspace root using config package.

    Args:
        workspace_root: Root directory where ragtime.toml will be created
        preset: Name of the preset (fast, balanced, accurate, legal, hr)
        preset_config: Preset configuration dict with model_alias, temperature, etc.
        selected_modules: List of selected modules to determine storage backend
    """
    from ragtime.core import RAGConfig
    from ragtime.core.loader import save_config
    from ragtime.core.presets import load_preset
    from ragtime.core.schema import (
        ChunkingConfig,
        EvalConfig,
        FormattingConfig,
        GenerationConfig,
        IngestionConfig,
        MetaConfig,
        OCRConfig,
        RetrievalConfig,
        StorageConfig,
    )

    # Determine storage backend based on selected modules
    # If Albert RAG is selected, use albert-collections; otherwise use local-sqlite
    if selected_modules and "Albert RAG" in selected_modules:
        storage_backend = "albert-collections"
    else:
        storage_backend = "local-sqlite"

    # Load public collection IDs from the preset (only relevant for Albert backend).
    # These populate the collection toggle buttons in the chat UI.
    collections: list[int] = []
    if storage_backend == "albert-collections":
        collections = load_preset(preset).storage.collections

    # Create config with preset values
    config = RAGConfig(
        meta=MetaConfig(preset=preset, schema_version="1.0.0"),
        generation=GenerationConfig(
            model=preset_config["model_alias"],
            temperature=preset_config["temperature"],
            max_tokens=1024,
            streaming=True,
            system_prompt=preset_config["system_prompt"],
        ),
        retrieval=RetrievalConfig(strategy="hybrid"),
        eval=EvalConfig(provider="albert", target_samples=50),
        ingestion=IngestionConfig(
            ocr=OCRConfig(enabled=True, dpi=300),
        ),
        chunking=ChunkingConfig(strategy="semantic", chunk_size=512, chunk_overlap=50),
        storage=StorageConfig(provider=storage_backend, collections=collections),
        formatting=FormattingConfig(
            output_format="markdown",
            include_confidence=False,
            language=preset_config["language"],
        ),
    )

    # Write to ragtime.toml
    config_path = workspace_root / "ragtime.toml"
    save_config(config, config_path)


def generate_standalone(
    target_path: Path,
    target_display: str,
    frontend_choice: str,
    selected_modules: list[str],
    env_config: dict[str, str],
    preset: str,
    preset_config: PresetConfig,
) -> None:
    """Generate a standalone (non-monorepo) project structure."""
    templates_dir = get_templates_dir()
    frontend_template = FRONTENDS[frontend_choice]
    template_dir = templates_dir / frontend_template

    # Template variables
    project_name = target_path.name

    variables: dict[str, str | bool] = {
        "project_name": project_name,
        "description": f"{project_name} - RAG application",
        "openai_api_key": env_config["openai_api_key"],
        "openai_base_url": env_config["openai_base_url"],
        "system_prompt": preset_config["system_prompt"],
        "welcome_message": f"Welcome to {project_name}!",
    }

    # Determine git ref for library sources
    git_ref = _get_library_git_ref()
    ref_key, ref_value = next(iter(git_ref.items()))

    # Step 1: Create target directory and initialize git repo
    console.print()
    console.print("[bold green]Step 1:[/bold green] Creating project directory...")
    if not target_path.exists():
        target_path.mkdir(parents=True)
    console.print("[green]✓[/green] Directory created")

    _init_git_repo(target_path)

    # Step 2: Generate standalone pyproject.toml
    console.print()
    console.print("[bold green]Step 2:[/bold green] Generating project files...")

    # Build uv.sources for library, albert-client, and CLI (dev dep)
    uv_sources = f"""[tool.uv.sources]
ragtime-lib = {{ git = "{_GITHUB_REPO}", {ref_key} = "{ref_value}", subdirectory = "packages/ragtime-lib" }}
albert-client = {{ git = "{_GITHUB_REPO}", {ref_key} = "{ref_value}", subdirectory = "packages/albert-client" }}
ragtime-cli = {{ git = "{_GITHUB_REPO}", {ref_key} = "{ref_value}", subdirectory = "apps/cli" }}
"""

    # Frontend-specific dependency and setuptools config
    snake_name = project_name.replace("-", "_")
    if frontend_choice == "Chainlit":
        frontend_dep = '"chainlit>=1.3.0",'
        # app.py at root (Chainlit convention) + src/<name>/ for user code
        setuptools_block = """\
[tool.setuptools]
py-modules = ["app"]

[tool.setuptools.packages.find]
where = ["src"]"""
        # Chainlit uses supabase for auth and asyncpg for data layer
        extra_deps = """\
    "supabase>=2.0.0",
    "asyncpg>=0.29.0",
"""
    else:
        frontend_dep = '"reflex>=0.7.0",'
        # App package at root, src/ for additional user code
        setuptools_block = f"""\n[tool.setuptools.packages.find]
include = ["{snake_name}*"]
where = [".", "src"]"""
        extra_deps = ""

    pyproject_content = f'''[project]
name = "{project_name}"
version = "0.1.0"
description = "{variables["description"]}"
readme = "README.md"
requires-python = ">=3.13"
dependencies = [
    "ragtime-lib",
    {frontend_dep}
    "python-dotenv>=1.0.0",
{extra_deps}]

[dependency-groups]
dev = [
    "ragtime-cli",
]

{setuptools_block}

[tool.uv]
package = true

{uv_sources}'''

    (target_path / "pyproject.toml").write_text(pyproject_content)
    console.print("[dim]  ✓ pyproject.toml[/dim]")

    (target_path / ".gitignore").write_text(_GITIGNORE_CONTENT)
    console.print("[dim]  ✓ .gitignore[/dim]")

    # Copy and render app files from template
    files_to_copy = [
        ".env.template",
        "README.md",
        "justfile",
    ]

    if frontend_choice == "Chainlit":
        files_to_copy.extend(["app.py", "chainlit.md"])
    else:
        files_to_copy.extend(["rxconfig.py"])

    for filename in files_to_copy:
        src = template_dir / filename
        if src.exists():
            content = render_template_file(src, variables)
            (target_path / filename).write_text(content)
            console.print(f"[dim]  ✓ {filename}[/dim]")

    # For Reflex, we also need to copy the app package directory
    if frontend_choice == "Reflex":
        # The template uses static "app" directory (moon doesn't support filters in paths)
        template_app_dir = template_dir / "app"
        if template_app_dir.exists():
            snake_name = project_name.replace("-", "_")
            target_app_dir = target_path / snake_name
            target_app_dir.mkdir(exist_ok=True)

            for src_file in template_app_dir.rglob("*"):
                if src_file.is_file():
                    rel_path = src_file.relative_to(template_app_dir)
                    rel_path_str = str(rel_path)

                    # Rename app.py to {snake_name}.py (Reflex expects {app_name}/{app_name}.py)
                    if rel_path_str == "app.py":
                        rel_path_str = f"{snake_name}.py"

                    target_file = target_app_dir / rel_path_str
                    target_file.parent.mkdir(parents=True, exist_ok=True)
                    content = render_template_file(src_file, variables)
                    target_file.write_text(content)
                    console.print(f"[dim]  ✓ {snake_name}/{rel_path_str}[/dim]")

    # Create src/<project_name>/ for user's own modules
    src_dir = target_path / "src" / snake_name
    src_dir.mkdir(parents=True, exist_ok=True)
    (src_dir / "__init__.py").write_text("")
    console.print(f"[dim]  ✓ src/{snake_name}/__init__.py[/dim]")

    console.print("[green]✓[/green] Project files generated")

    # Step 3: Create configuration files
    console.print()
    console.print("[bold green]Step 3:[/bold green] Creating configuration files...")

    # Create .env file
    env_content = f"""\
OPENAI_API_KEY={env_config["openai_api_key"]}
OPENAI_BASE_URL={env_config["openai_base_url"]}
"""
    (target_path / ".env").write_text(env_content)
    console.print("[green]✓[/green] Created .env file")

    # Generate ragtime.toml with preset configuration
    generate_config_file(target_path, preset, preset_config, selected_modules)
    console.print("[green]✓[/green] Created ragtime.toml")

    # Create .python-version
    (target_path / ".python-version").write_text("3.13\n")
    console.print("[dim]  ✓ .python-version[/dim]")

    # Done with generation!
    console.print()
    console.print("[bold green]✨ Project generation complete![/bold green]")

    # Step 4: Install dependencies
    console.print()
    console.print("[bold green]Step 4:[/bold green] Installing dependencies...")
    if not run_command(["uv", "sync"], "install dependencies", cwd=target_path):
        console.print("[yellow]Warning: uv sync failed. Run it manually.[/yellow]")

    _initial_git_commit(target_path)

    # Step 5: Print next steps (don't auto-start)
    console.print()
    console.print("[bold green]✨ Setup complete![/bold green]")
    console.print()
    console.print(f"[dim]Your app is at: {target_display}[/dim]")
    console.print()

    if frontend_choice == "Chainlit":
        console.print("[bold]Next steps:[/bold]")
        console.print()
        console.print("  1. [cyan]Start the app:[/cyan]")
        console.print(f"     [dim]cd {target_display} && just run[/dim]")
        console.print()
        console.print(
            "  2. [cyan](Optional) Enable Supabase auth and data persistence:[/cyan]"
        )
        console.print("     [dim]• Run 'supabase init' to set up local Supabase[/dim]")
        console.print("     [dim]• Run 'supabase start' to start services[/dim]")
        console.print(
            "     [dim]• Add SUPABASE_URL and SUPABASE_ANON_KEY to .env[/dim]"
        )
        console.print(
            "     [dim]• Run 'chainlit create-secret' and add CHAINLIT_AUTH_SECRET to .env[/dim]"
        )
        console.print(
            "     [dim]• Create your first user in Supabase Studio (http://127.0.0.1:54323)[/dim]"
        )
        console.print()
        console.print(
            "  [dim]Note: The app works without Supabase (auth disabled).[/dim]"
        )
        console.print(
            "  [dim]Enable it to persist conversations across sessions.[/dim]"
        )
    else:
        console.print("[bold]Next steps:[/bold]")
        console.print()
        console.print("  [cyan]Start the app:[/cyan]")
        console.print(f"     [dim]cd {target_display} && just run[/dim]")
        console.print()
        console.print("  [dim]The app will open in your browser automatically.[/dim]")


def _init_git_repo(target_path: Path) -> None:
    """Initialize a git repository at target_path, printing status."""
    if not run_command(["git", "init"], "initialize git repository", cwd=target_path):
        console.print("[yellow]  ⚠ git init failed — run manually: git init[/yellow]")
    else:
        console.print("[dim]  ✓ git repository initialized[/dim]")


def _initial_git_commit(target_path: Path) -> None:
    """Stage all generated files and create the initial commit (best-effort)."""
    try:
        subprocess.run(
            ["git", "add", "."],
            cwd=target_path,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "commit", "-m", "chore: initial workspace setup by ragtime"],
            cwd=target_path,
            check=True,
            capture_output=True,
        )
        console.print("[dim]  ✓ initial commit created[/dim]")
    except FileNotFoundError:
        pass  # git not installed
    except subprocess.CalledProcessError:
        console.print(
            "[yellow]  ⚠ initial commit skipped — configure git identity first:[/yellow]"
            "\n[dim]    git config --global user.name 'Your Name'[/dim]"
            "\n[dim]    git config --global user.email 'you@example.com'[/dim]"
            "\n[dim]  Then run: git add . && git commit -m 'initial setup'[/dim]"
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


def run(
    target: Annotated[
        str,
        typer.Argument(help="Target directory for the new workspace"),
    ] = "",
    expert: Annotated[
        bool,
        typer.Option(
            "--expert",
            help="Show advanced options (project structure, frontend, pipeline selection)",
        ),
    ] = False,
    force: Annotated[
        bool,
        typer.Option("--force", "-f", help="Overwrite existing files"),
    ] = False,
    preset: Annotated[
        str | None,
        typer.Option(help="Configuration preset (fast, balanced, accurate, legal, hr)"),
    ] = None,
    yes: Annotated[
        bool,
        typer.Option(
            "--yes",
            "-y",
            help="Skip all prompts (use defaults and env vars for API key)",
        ),
    ] = False,
):
    """Scaffold a new standalone Ragtime workspace with interactive configuration."""
    # 1. Gather inputs interactively (or use defaults with --yes)
    if not target:
        if yes:
            console.print("[red]Error: target directory is required with --yes[/red]")
            raise typer.Exit(1)
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
    if target_path.exists() and any(target_path.iterdir()) and not force and not yes:
        overwrite = questionary.confirm(
            f"Directory {target_path} is not empty. Continue anyway?",
            default=False,
        ).ask()
        if not overwrite:
            console.print("[yellow]Aborted.[/yellow]")
            raise typer.Exit(0)

    # Select preset (expert-only interactive picker; --preset flag still works for everyone)
    if not preset:
        if expert and not yes:
            preset = questionary.select(
                "Choose a configuration preset:",
                choices=[
                    questionary.Choice(
                        f"{name} - {config['description']}",
                        value=name,
                    )
                    for name, config in PRESET_CONFIGS.items()
                ],
                default="balanced",
            ).ask()
            if not preset:
                console.print("[red]Aborted.[/red]")
                raise typer.Exit(1)
        else:
            preset = "balanced"

    # Validate preset if provided via flag
    if preset not in PRESET_CONFIGS:
        console.print(f"[red]Error: Invalid preset '{preset}'[/red]")
        console.print(f"[dim]Valid presets: {', '.join(PRESET_CONFIGS.keys())}[/dim]")
        raise typer.Exit(1)

    preset_config = PRESET_CONFIGS[preset]

    # Select frontend (only shown with --expert)
    if expert:
        frontend_choice = questionary.select(
            "Select your frontend app:",
            choices=list(FRONTENDS.keys()),
        ).ask()
        if not frontend_choice:
            console.print("[red]Aborted.[/red]")
            raise typer.Exit(1)
    else:
        frontend_choice = "Chainlit"

    # Select RAG pipeline (only shown with --expert)
    if expert:
        module_choice = questionary.select(
            "Select your RAG pipeline:",
            choices=[
                questionary.Choice(
                    "Albert RAG - Server-side parsing, search & reranking (recommended)",
                    value="Albert RAG",
                ),
                questionary.Choice(
                    "Local - Local text extraction (offline, simple)",
                    value="Local",
                ),
            ],
        ).ask()
        if not module_choice:
            console.print("[red]Aborted.[/red]")
            raise typer.Exit(1)
    else:
        module_choice = "Albert RAG"

    selected_modules = [module_choice]

    # Prompt for environment configuration (use current env as defaults)
    env_config = {}

    if yes:
        # Non-interactive: use env var or empty string
        env_config["openai_api_key"] = os.getenv("OPENAI_API_KEY", "")
    else:
        console.print()
        console.print("[bold blue]Environment Configuration[/bold blue]")
        console.print(
            "[dim]These values will be saved to .env in your app directory.[/dim]"
        )
        console.print(
            "[dim]Get an API key at https://albert.sites.beta.gouv.fr/access/[/dim]"
        )
        console.print()

        # Prompt for API key without displaying it in clear text
        existing_key = os.getenv("OPENAI_API_KEY", "")
        use_existing_key = False
        if existing_key:
            use_existing = questionary.confirm(
                "Use existing OPENAI_API_KEY from environment?",
                default=True,
            ).ask()
            if use_existing is None:
                console.print("[red]Aborted.[/red]")
                raise typer.Exit(1)
            if use_existing:
                use_existing_key = True
                env_config["openai_api_key"] = existing_key

        if not use_existing_key:
            message = (
                "Enter new OpenAI/Albert API Key:"
                if existing_key
                else "OpenAI/Albert API Key:"
            )
            env_config["openai_api_key"] = questionary.password(message).ask()
            if env_config["openai_api_key"] is None:
                console.print("[red]Aborted.[/red]")
                raise typer.Exit(1)

    # Use base URL from preset
    env_config["openai_base_url"] = preset_config["openai_base_url"]

    console.print()
    console.print("[bold blue]Configuration Summary[/bold blue]")
    console.print(f"  Target: {target_display}")
    console.print("  Structure: Standalone")
    console.print(f"  Preset: {preset} ({preset_config['description']})")
    console.print(f"  Frontend: {frontend_choice}")
    console.print(f"  Model: {preset_config['model_alias']}")
    console.print(f"  Pipeline: {module_choice}")
    console.print(f"  API: {env_config['openai_base_url']}")
    console.print()

    # Confirm (skip with --yes)
    if not yes:
        if not questionary.confirm("Proceed with generation?", default=True).ask():
            console.print("[yellow]Aborted.[/yellow]")
            raise typer.Exit(0)

    generate_standalone(
        target_path=target_path,
        target_display=target_display,
        frontend_choice=frontend_choice,
        selected_modules=selected_modules,
        env_config=env_config,
        preset=preset,
        preset_config=preset_config,
    )
