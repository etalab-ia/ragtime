"""Setup new RAG Facile workspaces using Init + Patch architecture."""

import os
import shutil
import subprocess
from pathlib import Path
from collections.abc import Callable
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


# Path constants for locating source files in development vs bundled mode
REPO_ROOT = Path(__file__).resolve().parents[5]  # Root of rag-facile repository
BUNDLED_ROOT = (
    Path(__file__).resolve().parent.parent
)  # cli/ directory in installed package


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


def _get_source_path(
    dev_path_parts: tuple[str, ...],
    bundle_path_parts: tuple[str, ...],
    error_message: str,
) -> Path:
    """Helper to find a source path in development or bundled mode.

    Args:
        dev_path_parts: Path components relative to REPO_ROOT for development mode
        bundle_path_parts: Path components relative to BUNDLED_ROOT for installed CLI
        error_message: Error message to show if neither path exists

    Returns:
        Path to the source file/directory

    Raises:
        FileNotFoundError: If neither development nor bundled path exists
    """
    # In development mode, use the packages directory from repo root
    local_source = REPO_ROOT.joinpath(*dev_path_parts)
    if local_source.exists():
        return local_source

    # For installed CLI, source is bundled at cli/<name>_src
    package_source = BUNDLED_ROOT.joinpath(*bundle_path_parts)
    if package_source.exists():
        return package_source

    raise FileNotFoundError(error_message)


def get_context_source() -> Path:
    """Get the context source directory for inline copying."""
    return _get_source_path(
        ("packages", "context", "src", "context"),
        ("context_src",),
        "context source not found. This is a packaging error - please reinstall the CLI.",
    )


def get_reranking_source() -> Path:
    """Get the reranking source directory for inline copying."""
    return _get_source_path(
        ("packages", "reranking", "src", "reranking"),
        ("reranking_src",),
        "reranking source not found. This is a packaging error - please reinstall the CLI.",
    )


def get_retrieval_source() -> Path:
    """Get the retrieval source directory for inline copying."""
    return _get_source_path(
        ("packages", "retrieval", "src", "retrieval"),
        ("retrieval_src",),
        "retrieval source not found. This is a packaging error - please reinstall the CLI.",
    )


def get_storage_source() -> Path:
    """Get the storage source directory for inline copying."""
    return _get_source_path(
        ("packages", "storage", "src", "storage"),
        ("storage_src",),
        "storage source not found. This is a packaging error - please reinstall the CLI.",
    )


def get_pipelines_source() -> Path:
    """Get the pipelines source directory for inline copying."""
    return _get_source_path(
        ("packages", "pipelines", "src", "pipelines"),
        ("pipelines_src",),
        "pipelines source not found. This is a packaging error - please reinstall the CLI.",
    )


def get_ingestion_source() -> Path:
    """Get the ingestion source directory for inline copying."""
    return _get_source_path(
        ("packages", "ingestion", "src", "ingestion"),
        ("ingestion_src",),
        "ingestion source not found. This is a packaging error - please reinstall the CLI.",
    )


def get_albert_client_source() -> Path:
    """Get the albert-client source directory for inline copying."""
    return _get_source_path(
        ("packages", "albert-client", "src", "albert"),
        ("albert_src",),
        "albert-client source not found. This is a packaging error - please reinstall the CLI.",
    )


def get_rag_core_source() -> Path:
    """Get the rag-core source directory for inline copying."""
    return _get_source_path(
        ("packages", "rag-core", "src", "rag_core"),
        ("rag_core_src",),
        "rag-core source not found. This is a packaging error - please reinstall the CLI.",
    )


def get_default_config_template() -> Path:
    """Get the default ragfacile.toml template."""
    return _get_source_path(
        ("apps", "cli", "src", "cli", "templates", "ragfacile.toml"),
        ("templates", "ragfacile.toml"),
        "ragfacile.toml template not found. This is a packaging error - please reinstall the CLI.",
    )


def _copy_module_to_standalone(
    target_path: Path,
    module_name: str,
    get_source_func: Callable[[], Path],
    display_name: str,
    step: int,
) -> None:
    """Copy a package module into a standalone project directory.

    Handles directory cleanup, __pycache__ removal, and user-facing
    progress output.  Used by :func:`generate_standalone` to inline
    pipeline packages (albert, rag_core, context, ingestion, reranking, retrieval, storage, pipelines).

    Args:
        target_path: Root of the standalone project.
        module_name: Directory name for the copied module (e.g. ``"rag_core"``).
        get_source_func: Callable that returns the source :class:`Path`.
        display_name: Human-readable name for console output.
        step: Step number shown in the progress output.
    """
    console.print()
    console.print(f"[bold green]Step {step}:[/bold green] Adding {display_name}...")

    try:
        source = get_source_func()
        target_dir = target_path / module_name
        if target_dir.exists():
            shutil.rmtree(target_dir)
        shutil.copytree(source, target_dir)
        pycache = target_dir / "__pycache__"
        if pycache.exists():
            shutil.rmtree(pycache)
        console.print(f"[green]✓[/green] {display_name} added")
    except FileNotFoundError as e:
        console.print(f"[yellow]Warning: {e}[/yellow]")
        console.print(
            f"[yellow]You'll need to install {module_name} manually.[/yellow]"
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
    """Generate ragfacile.toml at workspace root using config package.

    Args:
        workspace_root: Root directory where ragfacile.toml will be created
        preset: Name of the preset (fast, balanced, accurate, legal, hr)
        preset_config: Preset configuration dict with model_alias, temperature, etc.
        selected_modules: List of selected modules to determine storage backend
    """
    from rag_core import RAGConfig
    from rag_core.loader import save_config
    from rag_core.schema import (
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
    force: bool,
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

    # Step 1: Create target directory
    console.print()
    console.print("[bold green]Step 1:[/bold green] Creating project directory...")
    if not target_path.exists():
        target_path.mkdir(parents=True)
    console.print("[green]✓[/green] Directory created")

    # Step 2: Generate standalone pyproject.toml
    console.print()
    console.print("[bold green]Step 2:[/bold green] Generating project files...")

    # Create pyproject.toml for standalone mode
    # pypdf required for both Local and Albert RAG (albert has local fallback)
    pdf_dep = (
        '\n    "pypdf>=5.0.0",'
        if ("Local" in selected_modules or "Albert RAG" in selected_modules)
        else ""
    )
    # Single source of truth for pipeline modules copied into standalone projects.
    # Used both for setuptools packages list and for the copy loop below.
    modules_to_copy = [
        ("albert", get_albert_client_source, "Albert client module"),
        ("rag_core", get_rag_core_source, "RAG core module"),
        ("context", get_context_source, "context module"),
        ("ingestion", get_ingestion_source, "ingestion module"),
        ("reranking", get_reranking_source, "reranking module"),
        ("retrieval", get_retrieval_source, "retrieval module"),
        ("storage", get_storage_source, "storage module"),
        ("pipelines", get_pipelines_source, "pipelines module"),
    ]
    setuptools_packages_list = sorted([module[0] for module in modules_to_copy])
    setuptools_packages = f"packages = {setuptools_packages_list}"

    # For standalone, all pipeline packages are local modules (not dependencies)
    pyproject_content = f'''[project]
name = "{project_name}"
version = "0.1.0"
description = "{variables["description"]}"
readme = "README.md"
requires-python = ">=3.13"
dependencies = [
    "chainlit>=1.3.0",
    "httpx>=0.24.0",
    "openai>=1.0.0",
    "pydantic>=2.0.0",
    "python-dotenv>=1.0.0",
    "tomli-w>=1.0.0",{pdf_dep}
]

[tool.setuptools]
py-modules = ["app"]
{setuptools_packages}

[tool.uv]
package = true
'''

    if frontend_choice == "Reflex":
        pyproject_content = f'''[project]
name = "{project_name}"
version = "0.1.0"
description = "{variables["description"]}"
readme = "README.md"
requires-python = ">=3.13"
dependencies = [
    "reflex>=0.7.0",
    "httpx>=0.24.0",
    "openai>=1.0.0",
    "pydantic>=2.0.0",
    "python-dotenv>=1.0.0",
    "tomli-w>=1.0.0",{pdf_dep}
]

[tool.setuptools]
{setuptools_packages}

[tool.uv]
package = true
'''

    (target_path / "pyproject.toml").write_text(pyproject_content)
    console.print("[dim]  ✓ pyproject.toml[/dim]")

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

    console.print("[green]✓[/green] Project files generated")

    # Steps 3-10: Copy pipeline modules as local packages
    for i, (module_name, source_func, display_name) in enumerate(
        modules_to_copy, start=3
    ):
        _copy_module_to_standalone(
            target_path, module_name, source_func, display_name, step=i
        )

    # Step 8: Create ragfacile.toml config file
    step_num = 8 if "Local" in selected_modules else 7
    console.print()
    console.print(
        f"[bold green]Step {step_num}:[/bold green] Creating configuration file..."
    )

    try:
        config_template = get_default_config_template()
        target_config = target_path / "ragfacile.toml"
        shutil.copy(config_template, target_config)
        console.print("[green]✓[/green] Created ragfacile.toml (balanced preset)")
    except FileNotFoundError as e:
        console.print(f"[yellow]Warning: {e}[/yellow]")
        console.print(
            "[yellow]You can create config later with: rag-facile config preset apply balanced[/yellow]"
        )

    # Step 9: Create .env file
    step_num = 9 if "Local" in selected_modules else 8
    console.print()
    console.print(
        f"[bold green]Step {step_num}:[/bold green] Creating environment file..."
    )

    env_content = f"""\
OPENAI_API_KEY={env_config["openai_api_key"]}
OPENAI_BASE_URL={env_config["openai_base_url"]}
"""
    (target_path / ".env").write_text(env_content)
    console.print("[green]✓[/green] Created .env file")

    # Generate ragfacile.toml with preset configuration
    console.print("[dim]  ✓ Generating configuration...[/dim]")
    generate_config_file(target_path, preset, preset_config, selected_modules)
    console.print("[green]✓[/green] Created ragfacile.toml")

    # Step 5: Create .python-version
    (target_path / ".python-version").write_text("3.13\n")
    console.print("[dim]  ✓ .python-version[/dim]")

    # Done with generation!
    console.print()
    console.print("[bold green]✨ Project generation complete![/bold green]")

    # Step 6: Install dependencies
    step_num += 1
    console.print()
    console.print(
        f"[bold green]Step {step_num}:[/bold green] Installing dependencies..."
    )
    if not run_command(["uv", "sync"], "install dependencies", cwd=target_path):
        console.print("[yellow]Warning: uv sync failed. Run it manually.[/yellow]")

    # Step 7: Start the dev server
    step_num += 1
    console.print()
    console.print(
        f"[bold green]Step {step_num}:[/bold green] Starting {frontend_choice} dev server..."
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
    preset: Annotated[
        str | None,
        typer.Option(help="Configuration preset (fast, balanced, accurate, legal, hr)"),
    ] = None,
    force: Annotated[
        bool,
        typer.Option("--force", "-f", help="Overwrite existing files"),
    ] = False,
    expert: Annotated[
        bool,
        typer.Option(
            "--expert",
            help="Show advanced options (project structure, pipeline selection)",
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

    # Select frontend
    frontend_choice = questionary.select(
        "Select your frontend app:",
        choices=list(FRONTENDS.keys()),
    ).ask()
    if not frontend_choice:
        console.print("[red]Aborted.[/red]")
        raise typer.Exit(1)

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

    # Confirm
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
            force=force,
        )
        return  # Exit after standalone generation

    # ========== MONOREPO GENERATION (existing flow) ==========

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
        "albert-client",
        "ingestion",
        "pipelines",
        "rag-core",
        "retrieval",
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

    if not run_command(app_cmd, f"generate {frontend_template}", cwd=target_path):
        raise typer.Exit(1)
    console.print(f"[green]✓[/green] {frontend_choice} app generated")

    # Post-generation: rename Reflex app package to match project_name
    # Moon templates can't use filters in directory names, so the template
    # generates a static "app/" directory that needs renaming.
    if frontend_choice == "Reflex":
        app_dir = target_path / "apps" / frontend_template
        static_pkg = app_dir / "app"
        if static_pkg.exists():
            # Read project_name from rxconfig.py to get the actual app_name
            rxconfig = app_dir / "rxconfig.py"
            if rxconfig.exists():
                import re

                match = re.search(r'app_name="([^"]+)"', rxconfig.read_text())
                if match:
                    app_module_name = match.group(1)
                    target_pkg = app_dir / app_module_name
                    static_pkg.rename(target_pkg)
                    # Rename app.py to {module_name}.py inside the package
                    static_main = target_pkg / "app.py"
                    if static_main.exists():
                        static_main.rename(target_pkg / f"{app_module_name}.py")
                    console.print(f"[dim]  ✓ Renamed app/ → {app_module_name}/[/dim]")

    # Create .env file from template values
    app_dir = target_path / "apps" / frontend_template
    env_file = app_dir / ".env"
    env_content = f"""\
OPENAI_API_KEY={env_config["openai_api_key"]}
OPENAI_BASE_URL={env_config["openai_base_url"]}
"""
    env_file.write_text(env_content)
    console.print("[green]✓[/green] Created .env file")

    # Generate ragfacile.toml at workspace root with preset configuration
    console.print("[dim]  ✓ Generating configuration...[/dim]")
    generate_config_file(target_path, preset, preset_config, selected_modules)
    console.print("[green]✓[/green] Created ragfacile.toml at workspace root")

    # Create .env at workspace root (in addition to app-level .env)
    root_env_file = target_path / ".env"
    root_env_file.write_text(env_content)
    console.print("[green]✓[/green] Created .env file at workspace root")

    # 4. Generate albert-client package (always required)
    console.print()
    console.print(
        "[bold green]Step 4:[/bold green] Generating albert-client package..."
    )
    albert_cmd = ["moon", "generate", "albert-client", "--defaults"]
    if force:
        albert_cmd.append("--force")
    if not run_command(albert_cmd, "generate albert-client", cwd=target_path):
        raise typer.Exit(1)
    console.print("[green]✓[/green] albert-client package generated")

    # 5. Generate rag-core package (always required for config management)
    console.print()
    console.print("[bold green]Step 5:[/bold green] Generating rag-core package...")
    config_cmd = ["moon", "generate", "rag-core", "--defaults"]
    if force:
        config_cmd.append("--force")
    if not run_command(config_cmd, "generate rag-core", cwd=target_path):
        raise typer.Exit(1)
    console.print("[green]✓[/green] rag-core package generated")

    # Copy ragfacile.toml config file to workspace root
    try:
        config_template = get_default_config_template()
        target_config = target_path / "ragfacile.toml"
        shutil.copy(config_template, target_config)
        console.print("[green]✓[/green] Created ragfacile.toml (balanced preset)")
    except FileNotFoundError as e:
        console.print(f"[yellow]Warning: {e}[/yellow]")
        console.print(
            "[yellow]You can create config later with: rag-facile config preset apply balanced[/yellow]"
        )

    # 6. Generate ingestion package (always required for document parsing)
    console.print()
    console.print("[bold green]Step 6:[/bold green] Generating ingestion package...")
    ingestion_cmd = ["moon", "generate", "ingestion", "--defaults"]
    if force:
        ingestion_cmd.append("--force")
    if not run_command(ingestion_cmd, "generate ingestion", cwd=target_path):
        raise typer.Exit(1)
    console.print("[green]✓[/green] ingestion package generated")

    # 7. Generate pipelines package (always required for pipeline coordination)
    console.print()
    console.print("[bold green]Step 7:[/bold green] Generating pipelines package...")
    pipelines_cmd = ["moon", "generate", "pipelines", "--defaults"]
    if force:
        pipelines_cmd.append("--force")
    if not run_command(pipelines_cmd, "generate pipelines", cwd=target_path):
        raise typer.Exit(1)
    console.print("[green]✓[/green] pipelines package generated")

    # 8. Generate selected packages
    if selected_modules:
        console.print()
        console.print("[bold green]Step 8:[/bold green] Generating packages...")

        # Collect unique templates (both PDF and Albert RAG use same retrieval template)
        templates_to_generate = set()
        for module in selected_modules:
            module_info = MODULES[module]
            if module_info["available"]:
                templates_to_generate.add(str(module_info["template"]))

        for template_name in templates_to_generate:
            console.print(f"  Generating {template_name}...")
            # Don't pass DEST - let the template.yml destination be used
            pkg_cmd: list[str] = ["moon", "generate", template_name, "--defaults"]
            if force:
                pkg_cmd.append("--force")
            if not run_command(pkg_cmd, f"generate {template_name}", cwd=target_path):
                raise typer.Exit(1)
            console.print(f"  [green]✓[/green] {template_name} package generated")

    # Done with generation!
    console.print()
    console.print("[bold green]✨ Workspace generation complete![/bold green]")

    # Run uv sync to install dependencies
    console.print()
    console.print("[bold green]Step 9:[/bold green] Installing dependencies...")
    if not run_command(["uv", "sync"], "install dependencies", cwd=target_path):
        console.print("[yellow]Warning: uv sync failed. Run it manually.[/yellow]")

    # Start the dev server
    console.print()
    console.print(
        f"[bold green]Step 10:[/bold green] Starting {frontend_choice} dev server..."
    )
    console.print()
    console.print(f"[dim]Your app is at: {target_display}[/dim]")
    console.print()

    # Run dev server (this will block and show output)
    dev_cmd = ["moon", "run", f"{FRONTENDS[frontend_choice]}:dev"]
    subprocess.run(dev_cmd, cwd=target_path)
