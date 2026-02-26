#!/usr/bin/env python3
"""Build the release asset (zip) for distribution to lambda developers.

Generates a standalone Chainlit workspace pre-configured with the `balanced`
preset and Albert RAG backend, then zips it for upload to a GitHub Release.

Usage:
    # From repo root:
    uv run python tools/build_release_asset.py

    # With a specific version tag (default: read from apps/cli/pyproject.toml):
    uv run python tools/build_release_asset.py --version v0.17.0

    # Output directory (default: dist/):
    uv run python tools/build_release_asset.py --output dist/

Output:
    dist/rag-facile-workspace-v{version}.zip

    The zip contains a single top-level directory `my-rag-app/` with:
    - pyproject.toml (deps: rag-facile-lib + chainlit; dev: rag-facile-cli)
    - app.py (Chainlit app, pre-configured)
    - ragfacile.toml (balanced preset, Albert RAG backend)
    - .env.template (OPENAI_API_KEY= placeholder)
    - justfile (run, learn, sync recipes)
    - chainlit.md (welcome screen)
    - README.md
    - .gitignore
    - src/my-rag-app/__init__.py
"""

import argparse
import re
import shutil
import tempfile
import tomllib
import zipfile
from pathlib import Path

from rich.console import Console


console = Console()

REPO_ROOT = Path(__file__).resolve().parent.parent
WORKSPACE_NAME = "my-rag-app"
GITHUB_REPO = "https://github.com/etalab-ia/rag-facile.git"


def _get_version() -> str:
    """Read the current CLI version from apps/cli/pyproject.toml."""
    pyproject = REPO_ROOT / "apps" / "cli" / "pyproject.toml"
    with pyproject.open("rb") as f:
        data = tomllib.load(f)
    return data["project"]["version"]


def _get_git_sha() -> str:
    """Return the current HEAD commit SHA (full, 40 chars)."""
    import subprocess

    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
    )
    return result.stdout.strip()


def _render_template(template_path: Path, variables: dict[str, str]) -> str:
    """Simple Tera-style {{ var }} substitution."""
    content = template_path.read_text()
    for key, value in variables.items():
        content = content.replace("{{ " + key + " }}", value)
        snake = value.replace("-", "_")
        content = content.replace(
            "{{ " + key + " | replace(from='-', to='_') }}", snake
        )
    return content


def build_workspace(target_dir: Path, version: str, git_sha: str) -> None:
    """Generate the workspace tree at target_dir.

    Args:
        target_dir: Directory that will become my-rag-app/ in the zip.
        version: Release version tag (e.g. "0.17.0" without "v" prefix).
        git_sha: Full git SHA of the current HEAD commit, used as the uv
            source rev so the workspace always tracks the exact code it was
            built from (rather than a tag that may pre-date recent changes).
    """
    project_name = WORKSPACE_NAME
    snake_name = project_name.replace("-", "_")

    console.print(f"[bold]Building workspace [cyan]{project_name}[/cyan]...[/bold]")
    target_dir.mkdir(parents=True, exist_ok=True)

    # ── pyproject.toml ────────────────────────────────────────────────────────
    # Pin to the exact commit SHA, not the version tag.
    # This ensures the workspace always gets the packages that were present when
    # the zip was built, even if the version tag was created before recent merges.
    uv_sources = (
        f'rag-facile-lib = {{ git = "{GITHUB_REPO}", rev = "{git_sha}", subdirectory = "packages/rag-facile-lib" }}\n'
        f'albert-client = {{ git = "{GITHUB_REPO}", rev = "{git_sha}", subdirectory = "packages/albert-client" }}\n'
        f'rag-facile-cli = {{ git = "{GITHUB_REPO}", rev = "{git_sha}", subdirectory = "apps/cli" }}\n'
    )

    pyproject = f"""\
[project]
name = "{project_name}"
version = "0.1.0"
description = "RAG Facile application"
readme = "README.md"
requires-python = ">=3.13"
dependencies = [
    "rag-facile-lib",
    "chainlit>=1.3.0",
    "python-dotenv>=1.0.0",
]

[dependency-groups]
dev = [
    "rag-facile-cli",
]

[tool.setuptools]
py-modules = ["app"]

[tool.setuptools.packages.find]
where = ["src"]

[tool.uv]
package = true

[tool.uv.sources]
{uv_sources}"""

    (target_dir / "pyproject.toml").write_text(pyproject)
    console.print("[dim]  ✓ pyproject.toml[/dim]")

    # ── justfile ─────────────────────────────────────────────────────────────
    justfile = """\
default:
    @just --list

# Install / update dependencies
sync:
    uv sync

# Run the Chainlit application
run:
    uv run chainlit run app.py -w

# Open the interactive RAG learning assistant
learn:
    uv run rag-facile learn
"""
    (target_dir / "justfile").write_text(justfile)
    console.print("[dim]  ✓ justfile[/dim]")

    # ── Copy source files from the chainlit-chat golden master ───────────────
    template_dir = REPO_ROOT / "apps" / "chainlit-chat"

    variables: dict[str, str] = {
        "project_name": project_name,
        "description": "RAG Facile application",
        "openai_api_key": "",
        "openai_base_url": "https://albert.api.etalab.gouv.fr/v1",
        "system_prompt": "Vous êtes un assistant utile.",
        "welcome_message": f"Welcome to {project_name}!",
    }

    for filename in ["app.py", "chainlit.md", "chainlit_fr-FR.md"]:
        src = template_dir / filename
        if src.exists():
            content = _render_template(src, variables)
            (target_dir / filename).write_text(content)
            console.print(f"[dim]  ✓ {filename}[/dim]")

    # Copy public/ directory (Chainlit static assets)
    public_src = template_dir / "public"
    if public_src.exists():
        shutil.copytree(public_src, target_dir / "public")
        console.print("[dim]  ✓ public/[/dim]")

    # ── .chainlit/config.toml ────────────────────────────────────────────────
    chainlit_config_src = template_dir / ".chainlit" / "config.toml"
    if chainlit_config_src.exists():
        chainlit_dir = target_dir / ".chainlit"
        chainlit_dir.mkdir()
        shutil.copy(chainlit_config_src, chainlit_dir / "config.toml")
        console.print("[dim]  ✓ .chainlit/config.toml[/dim]")

    # ── ragfacile.toml ───────────────────────────────────────────────────────
    # Import here — this script is run from the monorepo, so rag_facile is on the path
    from rag_facile.core import RAGConfig  # noqa: PLC0415
    from rag_facile.core.loader import save_config  # noqa: PLC0415
    from rag_facile.core.presets import load_preset  # noqa: PLC0415
    from rag_facile.core.schema import (  # noqa: PLC0415
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

    preset = load_preset("balanced")
    config = RAGConfig(
        meta=MetaConfig(preset="balanced", schema_version="1.0.0"),
        generation=GenerationConfig(
            model="openweight-medium",
            temperature=0.7,
            max_tokens=1024,
            streaming=True,
            system_prompt="Vous êtes un assistant utile.",
        ),
        retrieval=RetrievalConfig(strategy="hybrid"),
        eval=EvalConfig(provider="albert", target_samples=50),
        ingestion=IngestionConfig(ocr=OCRConfig(enabled=True, dpi=300)),
        chunking=ChunkingConfig(strategy="semantic", chunk_size=512, chunk_overlap=50),
        storage=StorageConfig(
            provider="albert-collections",
            collections=preset.storage.collections,
        ),
        formatting=FormattingConfig(
            output_format="markdown",
            include_confidence=False,
            language="fr",
        ),
    )
    save_config(config, target_dir / "ragfacile.toml")
    console.print("[dim]  ✓ ragfacile.toml[/dim]")

    # ── .env.template ────────────────────────────────────────────────────────
    env_template = """\
# Albert API credentials — get an API key at https://albert.sites.beta.gouv.fr/
OPENAI_API_KEY=
OPENAI_BASE_URL=https://albert.api.etalab.gouv.fr/v1
"""
    (target_dir / ".env.template").write_text(env_template)
    console.print("[dim]  ✓ .env.template[/dim]")

    # ── README.md ────────────────────────────────────────────────────────────
    readme = f"""\
# {project_name}

A RAG application powered by [RAG Facile](https://github.com/etalab-ia/rag-facile)
and the [Albert API](https://albert.sites.beta.gouv.fr/).

## Quick Start

1. **Add your API key** — copy `.env.template` to `.env` and fill in `OPENAI_API_KEY`:
   ```bash
   cp .env.template .env
   # Edit .env and add your Albert API key
   ```

2. **Install dependencies**:
   ```bash
   just sync
   ```

3. **Start the app**:
   ```bash
   just run
   ```
   Your Chainlit app opens at http://localhost:8000.

4. **Chat with the RAG assistant**:
   ```bash
   just learn
   ```

## Available Commands

Run `just` to see all available commands.
"""
    (target_dir / "README.md").write_text(readme)
    console.print("[dim]  ✓ README.md[/dim]")

    # ── .gitignore ───────────────────────────────────────────────────────────
    gitignore = """\
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

# Distribution / packaging
build/
dist/
*.egg-info/

# Testing
.coverage
.pytest_cache/

# IDEs
.vscode/
.idea/

# OS
.DS_Store
Thumbs.db

# Chainlit
.chainlit/*
!.chainlit/config.toml
.files/

# Databases
*.db
*.sqlite3

# Logs
*.log
"""
    (target_dir / ".gitignore").write_text(gitignore)
    console.print("[dim]  ✓ .gitignore[/dim]")

    # ── .python-version ──────────────────────────────────────────────────────
    (target_dir / ".python-version").write_text("3.13\n")
    console.print("[dim]  ✓ .python-version[/dim]")

    # ── src/<name>/ ───────────────────────────────────────────────────────────
    src_dir = target_dir / "src" / snake_name
    src_dir.mkdir(parents=True)
    (src_dir / "__init__.py").write_text("")
    console.print(f"[dim]  ✓ src/{snake_name}/__init__.py[/dim]")

    console.print(f"[green]✓[/green] Workspace generated at [cyan]{target_dir}[/cyan]")


def create_zip(workspace_dir: Path, output_path: Path, workspace_name: str) -> None:
    """Zip the workspace directory into output_path.

    The zip root directory is workspace_name/ (e.g. my-rag-app/).
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for file_path in sorted(workspace_dir.rglob("*")):
            if file_path.is_file():
                # Skip __pycache__ and .venv
                parts = file_path.relative_to(workspace_dir).parts
                if any(p in ("__pycache__", ".venv", ".pytest_cache") for p in parts):
                    continue
                arcname = Path(workspace_name) / file_path.relative_to(workspace_dir)
                zf.write(file_path, arcname)

    size_kb = output_path.stat().st_size // 1024
    console.print(
        f"[green]✓[/green] Created [cyan]{output_path}[/cyan] ([dim]{size_kb} KB[/dim])"
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build the RAG Facile release asset zip."
    )
    parser.add_argument(
        "--version",
        help="Release version (e.g. '0.17.0'). Defaults to CLI pyproject.toml version.",
    )
    parser.add_argument(
        "--output",
        default="dist",
        help="Output directory for the zip file (default: dist/).",
    )
    args = parser.parse_args()

    version = args.version
    if version:
        # Strip leading "v" if provided
        version = re.sub(r"^v", "", version)
    else:
        version = _get_version()

    git_sha = _get_git_sha()
    tag = f"v{version}"
    zip_name = f"rag-facile-workspace-{tag}.zip"
    output_path = REPO_ROOT / args.output / zip_name

    console.print(
        f"\n[bold]RAG Facile Release Asset Builder[/bold] — version [cyan]{tag}[/cyan] "
        f"([dim]{git_sha[:8]}[/dim])\n"
    )

    with tempfile.TemporaryDirectory() as tmpdir:
        workspace_dir = Path(tmpdir) / WORKSPACE_NAME
        build_workspace(workspace_dir, version, git_sha)
        console.print()
        create_zip(workspace_dir, output_path, WORKSPACE_NAME)

    console.print(
        f"\n[bold green]Done![/bold green] Asset ready for upload: [cyan]{output_path}[/cyan]\n"
    )


if __name__ == "__main__":
    main()
