"""Setup new RAG Facile workspaces using Init + Patch architecture."""

import os
import shutil
import subprocess
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
_GITHUB_REPO = "https://github.com/etalab-ia/rag-facile.git"

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


def _get_library_git_ref() -> dict[str, str]:
    """Determine the git ref for rag-facile-lib and albert-client sources.

    Returns a dict with either {"tag": "v0.15.0"} or {"branch": "main"}.
    Priority: RAG_FACILE_BRANCH env var > CLI version tag > "main" fallback.
    """
    # Dev testing: use branch from env var (same pattern as install.sh)
    branch = os.environ.get("RAG_FACILE_BRANCH")
    if branch:
        return {"branch": branch}

    # Production: use tag matching CLI version
    try:
        cli_version = get_version("rag-facile-cli")
        return {"tag": f"v{cli_version}"}
    except PackageNotFoundError:
        return {"branch": "main"}


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
        [
            "bash",
            "-c",
            "bash <(curl -fsSL https://moonrepo.dev/install/proto.sh) --yes",
        ],
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
    "Local": {"template": "retrieval", "available": True},
    "Albert RAG": {"template": "retrieval", "available": True},
}

# Project structure options
PROJECT_STRUCTURES = {
    "Simple (recommended for getting started)": "standalone",
    "Monorepo (for multi-app projects)": "monorepo",
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

    # Fallback: check if we're in the rag-facile repo (development mode)
    repo_root = Path(__file__).resolve().parents[5]
    local_templates = repo_root / ".moon" / "templates"
    if local_templates.exists():
        return local_templates

    raise FileNotFoundError(
        "Templates not found. This is a packaging error - please reinstall the CLI."
    )


def get_default_config_template() -> Path:
    """Get the default ragfacile.toml template."""
    # Try bundled location (installed CLI)
    bundled = Path(__file__).resolve().parent.parent / "templates" / "ragfacile.toml"
    if bundled.exists():
        return bundled

    # Try development location (repo structure)
    repo_root = Path(__file__).resolve().parents[5]
    dev = repo_root / "apps" / "cli" / "src" / "cli" / "templates" / "ragfacile.toml"
    if dev.exists():
        return dev

    raise FileNotFoundError(
        "ragfacile.toml template not found. This is a packaging error - please reinstall the CLI."
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


def _print_no_serve_message(target_display: str) -> None:
    """Print app location and skip dev server message."""
    console.print()
    console.print(f"[dim]Your app is at: {target_display}[/dim]")
    console.print("[dim]Run the dev server manually when ready.[/dim]")


def generate_config_file(
    workspace_root: Path,
    preset: str,
    preset_config: PresetConfig,
    selected_modules: list[str] | None = None,
) -> None:
    """Generate ragfacile.toml at workspace root using config package.

    Args:
        workspace_root: Root directory where ragfacile.toml will be created
        preset: Name of the preset (fast, balanced, accurate, legal, hr)
        preset_config: Preset configuration dict with model_alias, temperature, etc.
        selected_modules: List of selected modules to determine storage backend
    """
    from rag_facile.core import RAGConfig
    from rag_facile.core.loader import save_config
    from rag_facile.core.schema import (
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
        storage=StorageConfig(provider=storage_backend),
        formatting=FormattingConfig(
            output_format="markdown",
            include_confidence=False,
            language=preset_config["language"],
        ),
    )

    # Write to ragfacile.toml
    config_path = workspace_root / "ragfacile.toml"
    save_config(config, config_path)


def generate_standalone(
    target_path: Path,
    target_display: str,
    frontend_choice: str,
    selected_modules: list[str],
    env_config: dict[str, str],
    preset: str,
    preset_config: PresetConfig,
    no_serve: bool = False,
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

    # Build uv.sources for library and albert-client
    uv_sources = f"""[tool.uv.sources]
rag-facile-lib = {{ git = "{_GITHUB_REPO}", {ref_key} = "{ref_value}", subdirectory = "packages/rag-facile-lib" }}
albert-client = {{ git = "{_GITHUB_REPO}", {ref_key} = "{ref_value}", subdirectory = "packages/albert-client" }}
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
    else:
        frontend_dep = '"reflex>=0.7.0",'
        # App package at root, src/ for additional user code
        setuptools_block = f"""\
[tool.setuptools.packages.find]
include = ["{snake_name}*"]
where = [".", "src"]"""

    pyproject_content = f'''[project]
name = "{project_name}"
version = "0.1.0"
description = "{variables["description"]}"
readme = "README.md"
requires-python = ">=3.13"
dependencies = [
    "rag-facile-lib",
    {frontend_dep}
    "python-dotenv>=1.0.0",
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
        ".envrc",
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
    src_dir.mkdir(parents=True)
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

    # Generate ragfacile.toml with preset configuration
    generate_config_file(target_path, preset, preset_config, selected_modules)
    console.print("[green]✓[/green] Created ragfacile.toml")

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

    # Step 5: Start the dev server (unless --no-serve)
    if no_serve:
        _print_no_serve_message(target_display)
        return

    console.print()
    console.print(
        f"[bold green]Step 5:[/bold green] Starting {frontend_choice} dev server..."
    )
    console.print()
    console.print(f"[dim]Your app is at: {target_display}[/dim]")
    console.print()

    # Run dev server with uv (no moon in standalone mode)
    if frontend_choice == "Chainlit":
        dev_cmd = ["uv", "run", "chainlit", "run", "app.py", "-w"]
    else:
        dev_cmd = ["uv", "run", "reflex", "run"]

    subprocess.run(dev_cmd, cwd=target_path)


def _init_git_repo(target_path: Path) -> None:
    """Initialize a git repository at target_path, printing status."""
    if not run_command(["git", "init"], "initialize git repository", cwd=target_path):
        console.print("[yellow]  ⚠ git init failed — run manually: git init[/yellow]")
    else:
        console.print("[dim]  ✓ git repository initialized[/dim]")


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
    no_serve: Annotated[
        bool,
        typer.Option(
            "--no-serve",
            help="Skip launching the dev server after setup",
        ),
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
    """Setup a new RAG Facile workspace with interactive configuration.

    Uses the Init + Patch architecture:
    1. Bootstrap with `moon init`
    2. Apply RAG Facile configuration
    3. Generate selected app and packages
    """
    # 0. Ensure toolchain is installed (proto, moon, uv)
    if not ensure_toolchain():
        raise typer.Exit(1)

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

    # Select project structure (only shown with --expert)
    if expert:
        structure_choice = questionary.select(
            "What type of project structure do you want?",
            choices=list(PROJECT_STRUCTURES.keys()),
        ).ask()
        if not structure_choice:
            console.print("[red]Aborted.[/red]")
            raise typer.Exit(1)
        is_standalone = PROJECT_STRUCTURES[structure_choice] == "standalone"
    else:
        is_standalone = True

    # Select preset
    if not preset:
        if yes:
            preset = "balanced"
        else:
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

        env_config["openai_api_key"] = questionary.text(
            "OpenAI/Albert API Key:",
            default=os.getenv("OPENAI_API_KEY", ""),
        ).ask()
        if env_config["openai_api_key"] is None:
            console.print("[red]Aborted.[/red]")
            raise typer.Exit(1)

    # Use base URL from preset
    env_config["openai_base_url"] = preset_config["openai_base_url"]

    console.print()
    console.print("[bold blue]Configuration Summary[/bold blue]")
    console.print(f"  Target: {target_display}")
    console.print(
        f"  Structure: {'Simple (standalone)' if is_standalone else 'Monorepo'}"
    )
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

    # Branch based on project structure choice
    if is_standalone:
        generate_standalone(
            target_path=target_path,
            target_display=target_display,
            frontend_choice=frontend_choice,
            selected_modules=selected_modules,
            env_config=env_config,
            preset=preset,
            preset_config=preset_config,
            no_serve=no_serve,
        )
        return  # Exit after standalone generation

    # ========== MONOREPO GENERATION ==========

    import shutil

    # 1. Bootstrap with moon init
    console.print()
    console.print("[bold green]Step 1:[/bold green] Initializing Moon workspace...")
    if not target_path.exists():
        target_path.mkdir(parents=True)

    _init_git_repo(target_path)

    if not run_command(["moon", "init", "--yes"], "moon init", cwd=target_path):
        raise typer.Exit(1)
    console.print("[green]✓[/green] Moon workspace initialized")

    # 2. Write workspace configuration files directly (no sys-config template needed)
    console.print()
    console.print(
        "[bold green]Step 2:[/bold green] Applying RAG Facile configuration..."
    )
    moon_dir = target_path / ".moon"
    moon_dir.mkdir(
        parents=True, exist_ok=True
    )  # Ensure .moon/ exists (moon init creates it; this is a safety net)

    (moon_dir / "toolchain.yml").write_text(
        "$schema: 'https://moonrepo.dev/schemas/toolchain.json'\n"
        "python:\n"
        "  version: '3.13.11'\n"
        "  packageManager: uv\n"
    )
    console.print("[dim]  ✓ .moon/toolchain.yml[/dim]")

    (moon_dir / "workspace.yml").write_text(
        "projects:\n"
        "  - 'apps/*'\n"
        "  - 'packages/*'\n"
        "vcs:\n"
        "  manager: git\n"
        "  defaultBranch: main\n"
        "telemetry: false\n"
        "generator:\n"
        "  templates:\n"
        "    - .moon/templates\n"
    )
    console.print("[dim]  ✓ .moon/workspace.yml[/dim]")

    (target_path / "pyproject.toml").write_text(
        "[project]\n"
        f'name = "{target_path.name}"\n'
        'version = "0.1.0"\n'
        'description = "RAG Facile workspace"\n'
        'requires-python = ">=3.13"\n'
        "dependencies = []\n"
        "\n"
        "[dependency-groups]\n"
        'dev = ["ruff>=0.9", "ty>=0.0.1a7"]\n'
        "\n"
        "[tool.ruff]\n"
        "# Exclude moon templates (contain Jinja2 syntax, not valid Python/TOML)\n"
        'extend-exclude = [".moon/templates"]\n'
        "\n"
        "[tool.ruff.lint]\n"
        'exclude = [".moon/templates"]\n'
        "\n"
        "[tool.ruff.format]\n"
        'exclude = [".moon/templates"]\n'
        "\n"
        "[tool.ty.src]\n"
        'exclude = [".moon/templates"]\n'
        "\n"
        "[tool.uv]\n"
        "managed = true\n"
        "\n"
        "[tool.uv.workspace]\n"
        'members = ["apps/*", "packages/*"]\n'
    )
    console.print("[dim]  ✓ pyproject.toml[/dim]")

    (target_path / ".python-version").write_text("3.13\n")
    console.print("[dim]  ✓ .python-version[/dim]")

    (target_path / ".prototools").write_text(
        f"# Proto toolchain configuration for {target_path.name}\n"
        'python = "3.13.11"\n'
        "\n"
        "[plugins]\n"
        'just = "source:https://raw.githubusercontent.com/Phault/proto-toml-plugins/main/just/plugin.toml"\n'
        "\n"
        "[tools.just]\n"
        'version = "1.34.0"\n'
    )
    console.print("[dim]  ✓ .prototools[/dim]")

    (target_path / "justfile").write_text(
        f"# {target_path.name} - RAG Facile project\n"
        "\n"
        "# Display available commands\n"
        "default:\n"
        "    @just --list\n"
        "\n"
        "# Run a specific app (e.g., just run chainlit-chat)\n"
        "run name:\n"
        '    cd "apps/{{{{ name }}}}" && just run\n'
        "\n"
        "# Format code (write changes)\n"
        "format:\n"
        "    uv run ruff format .\n"
        "\n"
        "# Check formatting without writing\n"
        "format-check:\n"
        "    uv run ruff format --check .\n"
        "\n"
        "# Run linter\n"
        "lint:\n"
        "    uv run ruff check .\n"
        "\n"
        "# Run linter with auto-fix\n"
        "lint-fix:\n"
        "    uv run ruff check --fix .\n"
        "\n"
        "# Run type checker\n"
        "type-check:\n"
        "    uv run ty check .\n"
        "\n"
        "# Run all checks (format-check, lint, type-check)\n"
        "check: format-check lint type-check\n"
        "\n"
        "# Sync dependencies and install pre-commit hooks\n"
        "sync:\n"
        "    uv sync\n"
        "    uv run pre-commit install\n"
        "\n"
        "# Add a new app from template (e.g., just add chainlit-chat)\n"
        "add template:\n"
        "    moon generate {{{{template}}}}\n"
    )
    console.print("[dim]  ✓ justfile[/dim]")

    (target_path / ".gitignore").write_text(_GITIGNORE_CONTENT)
    console.print("[dim]  ✓ .gitignore[/dim]")

    console.print("[green]✓[/green] Workspace configuration written")

    # 3. Copy app template and run moon generate for the frontend
    console.print()
    console.print(
        f"[bold green]Step 3:[/bold green] Generating {frontend_choice} app..."
    )

    # Copy only the frontend template (pipeline packages come from rag-facile-lib)
    frontend_template = FRONTENDS[frontend_choice]
    templates_dir = get_templates_dir()
    target_templates = moon_dir / "templates"
    target_templates.mkdir(parents=True, exist_ok=True)

    src_tmpl = templates_dir / frontend_template
    dst_tmpl = target_templates / frontend_template
    if dst_tmpl.exists():
        shutil.rmtree(dst_tmpl)
    shutil.copytree(src_tmpl, dst_tmpl)
    console.print(f"[dim]  ✓ copied {frontend_template} template[/dim]")

    # Build moon generate command; inject git ref for rag-facile-lib
    git_ref = _get_library_git_ref()
    ref_key, ref_value = next(iter(git_ref.items()))

    app_cmd = ["moon", "generate", frontend_template, "--defaults"]
    if force:
        app_cmd.append("--force")
    app_cmd.extend(
        [
            "--",
            f"--openai_api_key={env_config['openai_api_key']}",
            f"--openai_base_url={env_config['openai_base_url']}",
            f"--rag_facile_ref_key={ref_key}",
            f"--rag_facile_ref_value={ref_value}",
        ]
    )

    if not run_command(app_cmd, f"generate {frontend_template}", cwd=target_path):
        raise typer.Exit(1)
    console.print(f"[green]✓[/green] {frontend_choice} app generated")

    # Post-generation: rename Reflex app package to match project_name
    if frontend_choice == "Reflex":
        app_dir = target_path / "apps" / frontend_template
        static_pkg = app_dir / "app"
        if static_pkg.exists():
            rxconfig = app_dir / "rxconfig.py"
            if rxconfig.exists():
                import re

                match = re.search(r'app_name="([^"]+)"', rxconfig.read_text())
                if match:
                    app_module_name = match.group(1)
                    target_pkg = app_dir / app_module_name
                    static_pkg.rename(target_pkg)
                    static_main = target_pkg / "app.py"
                    if static_main.exists():
                        static_main.rename(target_pkg / f"{app_module_name}.py")
                    console.print(f"[dim]  ✓ Renamed app/ → {app_module_name}/[/dim]")

    # 4. Create config and env files
    console.print()
    console.print("[bold green]Step 4:[/bold green] Creating configuration files...")

    env_content = f"""\
OPENAI_API_KEY={env_config["openai_api_key"]}
OPENAI_BASE_URL={env_config["openai_base_url"]}
"""
    # .env at workspace root (apps pick it up via direnv)
    (target_path / ".env").write_text(env_content)
    console.print("[green]✓[/green] Created .env")

    # Also write .env into the generated app directory
    app_dir = target_path / "apps" / frontend_template
    (app_dir / ".env").write_text(env_content)

    generate_config_file(target_path, preset, preset_config, selected_modules)
    console.print("[green]✓[/green] Created ragfacile.toml")

    (target_path / ".python-version").write_text("3.13\n")

    # Done with generation!
    console.print()
    console.print("[bold green]✨ Workspace generation complete![/bold green]")

    # Run uv sync to install dependencies
    console.print()
    console.print("[bold green]Step 5:[/bold green] Installing dependencies...")
    if not run_command(["uv", "sync"], "install dependencies", cwd=target_path):
        console.print("[yellow]Warning: uv sync failed. Run it manually.[/yellow]")

    # Start the dev server (unless --no-serve)
    if no_serve:
        _print_no_serve_message(target_display)
        return

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
