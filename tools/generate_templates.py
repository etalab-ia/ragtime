#!/usr/bin/env python3
"""Template generation script for RAG Facile.

Generates Moon templates from golden master apps and packages.
Uses LibCST for Python code parameterization.

Usage:
    python generate_templates.py --all
    python generate_templates.py --template chainlit-chat
"""

import argparse
import shutil
from pathlib import Path

import libcst as cst
import yaml
from rich.console import Console


console = Console()

# Repository root (tools/ is at repo/tools/)
REPO_ROOT = Path(__file__).resolve().parent.parent
TEMPLATES_DIR = REPO_ROOT / ".moon" / "templates"

# Artifacts to ignore when copying
ARTIFACTS = [
    "__pycache__",
    "*.egg-info",
    ".venv",
    ".env",
    ".git",
    ".DS_Store",
    ".web",
    ".states",
    ".chainlit",
    "tests",
    ".pytest_cache",
    ".ruff_cache",
]


class JinjaTransformer(cst.CSTTransformer):
    """LibCST Transformer to parameterize Python code with Tera/Jinja tags."""

    def __init__(self, mappings: dict[str, str]):
        self.mappings = mappings

    def leave_SimpleString(
        self, original_node: cst.SimpleString, updated_node: cst.SimpleString
    ) -> cst.SimpleString:
        val = updated_node.value
        for golden, tag in self.mappings.items():
            if golden in val:
                new_val = val.replace(golden, tag)
                return updated_node.with_changes(value=new_val)
        return updated_node


def generate_sys_config(force: bool = False):
    """Generate sys-config template (workspace configuration)."""
    console.print("[bold]Generating sys-config template...[/bold]")

    target = TEMPLATES_DIR / "sys-config"
    if target.exists():
        if not force:
            console.print(
                f"[red]Error:[/red] Template directory {target} already exists. Use --force to overwrite."
            )
            return False
        shutil.rmtree(target)
    target.mkdir(parents=True)

    # Create template.yml
    template_yml = {
        "title": "System Configuration",
        "description": "RAG Facile workspace config (patches moon init defaults).",
        "destination": ".",
        "variables": {
            "project_name": {
                "type": "string",
                "default": "my-rag-project",
                "prompt": "What is the name of your project?",
            },
        },
    }
    (target / "template.yml").write_text(yaml.dump(template_yml, sort_keys=False))

    # Create .moon directory with config files
    moon_dir = target / ".moon"
    moon_dir.mkdir()

    toolchain = {
        "$schema": "https://moonrepo.dev/schemas/toolchain.json",
        "python": {"version": "3.13.11", "packageManager": "uv"},
    }
    (moon_dir / "toolchain.yml").write_text(yaml.dump(toolchain, sort_keys=False))

    workspace = {
        "projects": ["apps/*", "packages/*"],
        "vcs": {"manager": "git", "defaultBranch": "main"},
        "telemetry": False,
        "generator": {"templates": [".moon/templates"]},
    }
    (moon_dir / "workspace.yml").write_text(yaml.dump(workspace, sort_keys=False))

    # Create root pyproject.toml for uv workspace
    pyproject = """\
[project]
name = "{{ project_name }}"
version = "0.1.0"
description = "RAG Facile workspace"
requires-python = ">=3.13"
dependencies = []

[dependency-groups]
dev = ["ruff>=0.9", "ty>=0.0.1a7"]

[tool.ruff]
# Exclude moon templates (contain Jinja2 syntax, not valid Python/TOML)
extend-exclude = [".moon/templates"]

[tool.ruff.lint]
exclude = [".moon/templates"]

[tool.ruff.format]
exclude = [".moon/templates"]

[tool.ty.src]
exclude = [".moon/templates"]

[tool.uv]
managed = true

[tool.uv.workspace]
members = ["apps/*", "packages/*"]
"""
    (target / "pyproject.toml").write_text(pyproject)

    # Pin Python version for uv
    (target / ".python-version").write_text("3.13\n")

    # Create justfile for common commands
    justfile = """\
# {{ project_name }} - RAG Facile project

# Display available commands
default:
    @just --list

# Run all apps or a specific app (e.g., just run or just run chainlit-chat)
run name="":
    @if [ -z "{{ "{{ name }}" }}" ]; then \\
        moon run :dev; \\
    else \\
        moon run {{ "{{ name }}" }}:dev; \\
    fi

# Format code (write changes)
format:
    uv run ruff format .

# Check formatting without writing
format-check:
    uv run ruff format --check .

# Run linter
lint:
    uv run ruff check .

# Run linter with auto-fix
lint-fix:
    uv run ruff check --fix .

# Run type checker
type-check:
    uv run ty check .

# Run all checks (format-check, lint, type-check)
check: format-check lint type-check

# Sync dependencies and install pre-commit hooks
sync:
    uv sync
    uv run pre-commit install

# Add a new app from template (e.g., just add chainlit-chat)
add template:
    moon generate {% raw %}{{template}}{% endraw %}
"""
    (target / "justfile").write_text(justfile)

    # Create .prototools for proto toolchain management
    prototools = """\
# Proto toolchain configuration for {{ project_name }}
# This file pins versions of all tools used in the project
# See: https://moonrepo.dev/docs/proto

python = "3.13.11"

# Plugins for non-core tools
[plugins]
just = "source:https://raw.githubusercontent.com/Phault/proto-toml-plugins/main/just/plugin.toml"

# Tool-specific versions
[tools.just]
version = "1.34.0"
"""
    (target / ".prototools").write_text(prototools)

    console.print("[green]✓[/green] sys-config generated")


def generate_app_template(app_name: str, source_dir: Path, force: bool = False):
    """Generate an app template from source with parameterization."""
    console.print(f"[bold]Generating {app_name} template...[/bold]")

    target = TEMPLATES_DIR / app_name
    if target.exists():
        if not force:
            console.print(
                f"[red]Error:[/red] Template directory {target} already exists. Use --force to overwrite."
            )
            return False
        shutil.rmtree(target)

    # Copy source to target, ignoring artifacts
    shutil.copytree(source_dir, target, ignore=shutil.ignore_patterns(*ARTIFACTS))
    console.print(f"  Copied {source_dir.name} to template")

    # Determine parameterization mappings
    slug = app_name  # e.g., "chainlit-chat"
    slug_underscore = slug.replace("-", "_")

    mappings = {
        slug: "{{ project_name }}",
        slug_underscore: "{{ project_name | replace(from='-', to='_') }}",
    }

    # App-specific mappings
    if app_name == "chainlit-chat":
        mappings.update(
            {
                "Chainlit Chat with OpenAI Functions Streaming": "{{ description }}",
                "Welcome to Chainlit! 🚀🤖": "{{ welcome_message }}",
                "You are a helpful assistant.": "{{ system_prompt }}",
            }
        )
    elif app_name == "reflex-chat":
        mappings.update(
            {
                "Reflex Chat Application": "{{ description }}",
                "You are a friendly chatbot named Reflex. Respond in markdown.": (
                    "{{ system_prompt }}"
                ),
            }
        )

    # Phase 1: LibCST transformation for Python files (handles string literals)
    python_files = list(target.rglob("*.py"))
    for py_file in python_files:
        code = py_file.read_text()
        try:
            tree = cst.parse_module(code)
            transformer = JinjaTransformer(mappings)
            modified_tree = tree.visit(transformer)
            py_file.write_text(modified_tree.code)
            console.print(f"  [green]✓[/green] LibCST: {py_file.name}")
        except Exception as e:
            console.print(f"  [yellow]⚠[/yellow] LibCST failed for {py_file.name}: {e}")

    # Phase 1.5: Text-based replacement for import statements
    # LibCST doesn't parameterize module names in imports, so we do text replace
    for py_file in python_files:
        code = py_file.read_text()
        modified = code
        for golden, tag in mappings.items():
            # Replace in import statements
            modified = modified.replace(f"from {golden}.", f"from {tag}.")
            modified = modified.replace(f"import {golden}.", f"import {tag}.")
            modified = modified.replace(f"import {golden}\n", f"import {tag}\n")
        if modified != code:
            py_file.write_text(modified)
            console.print(f"  [green]✓[/green] Imports: {py_file.name}")

    # Phase 2: Parameterize pyproject.toml with conditional dependencies
    pyproject_path = target / "pyproject.toml"
    if pyproject_path.exists():
        content = pyproject_path.read_text()
        content = content.replace(f'"{slug}"', '"{{ project_name }}"')

        # Replace description
        if app_name == "chainlit-chat":
            content = content.replace(
                '"Chainlit Chat with OpenAI Functions Streaming"', '"{{ description }}"'
            )
        elif app_name == "reflex-chat":
            content = content.replace(
                '"Reflex Chat Application"', '"{{ description }}"'
            )
            # Also fix setuptools include pattern
            content = content.replace(
                f'["{slug_underscore}*"]',
                "[\"{{ project_name | replace(from='-', to='_') }}*\"]",
            )

        # Add [tool.uv] package = true if not present
        if "[tool.uv]\npackage = true" not in content:
            content += "\n[tool.uv]\npackage = true\n"

        pyproject_path.write_text(content)
        console.print("  [green]✓[/green] pyproject.toml parameterized")

    # Phase 3: Generate .env.template
    env_content = (
        "OPENAI_API_KEY={{ openai_api_key }}\n"
        "OPENAI_BASE_URL={{ openai_base_url }}\n"
        "OPENAI_MODEL={{ openai_model }}\n"
    )
    (target / ".env.template").write_text(env_content)
    console.print("  [green]✓[/green] .env.template generated")

    # Phase 5: App-specific parameterization
    if app_name == "chainlit-chat":
        # Parameterize chainlit.md
        md_path = target / "chainlit.md"
        if md_path.exists():
            content = md_path.read_text()
            content = content.replace(
                "# Welcome to Chainlit! 🚀🤖", "# {{ welcome_message }}"
            )
            md_path.write_text(content)
            console.print("  [green]✓[/green] chainlit.md parameterized")

    elif app_name == "reflex-chat":
        # Parameterize rxconfig.py
        rxconfig_path = target / "rxconfig.py"
        if rxconfig_path.exists():
            content = rxconfig_path.read_text()
            content = content.replace(
                'app_name="reflex_chat"',
                "app_name=\"{{ project_name | replace(from='-', to='_') }}\"",
            )
            rxconfig_path.write_text(content)
            console.print("  [green]✓[/green] rxconfig.py parameterized")

        # Rename package directory to static name (Windows-compatible)
        # Moon only supports simple variable interpolation in paths: [varName]
        # Filters like | replace() are NOT supported in directory names
        pkg_dir = target / "reflex_chat"
        if pkg_dir.exists():
            # Rename main app file to static name
            main_app = pkg_dir / "reflex_chat.py"
            if main_app.exists():
                # Use static name - actual module name is parameterized in rxconfig.py
                main_app.rename(pkg_dir / "app.py")

            # Rename package directory to static name
            pkg_dir.rename(target / "app")
            console.print("  [green]✓[/green] Reflex package structure parameterized")

    # Phase 6: Generate template.yml
    variables = {
        "project_name": {
            "type": "string",
            "default": f"my-{app_name.split('-')[0]}-app",
            "prompt": "What is the name of your project?",
        },
        "description": {
            "type": "string",
            "default": f"A {app_name.replace('-', ' ').title()}",
            "prompt": "Short description of the project",
        },
        "openai_api_key": {
            "type": "string",
            "prompt": "What is your Albert API Key? (Get one at https://albert.sites.beta.gouv.fr/access/)",
        },
        "openai_base_url": {
            "type": "string",
            "default": "https://albert.api.etalab.gouv.fr/v1",
            "prompt": "What is your OpenAI Base URL?",
        },
        "openai_model": {
            "type": "string",
            "default": "openweight-large",
            "prompt": "Default OpenAI model to use",
        },
        "system_prompt": {
            "type": "string",
            "default": "You are a helpful assistant."
            if app_name == "chainlit-chat"
            else "You are a friendly chatbot named Reflex. Respond in markdown.",
            "prompt": "Initial system prompt for the assistant",
        },
    }

    if app_name == "chainlit-chat":
        variables["welcome_message"] = {
            "type": "string",
            "default": "Welcome to Chainlit! 🚀🤖",
            "prompt": "Header text for the welcome screen",
        }

    template_yml = {
        "title": app_name.replace("-", " ").title(),
        "description": f"A {app_name.replace('-', ' ').title()} Application",
        "destination": f"apps/{app_name}",
        "variables": variables,
    }
    (target / "template.yml").write_text(
        yaml.dump(template_yml, sort_keys=False, allow_unicode=True)
    )
    console.print("  [green]✓[/green] template.yml generated")

    console.print(f"[green]✓ {app_name} template complete![/green]")


def generate_package_template(pkg_name: str, source_dir: Path, force: bool = False):
    """Generate a package template from source."""
    console.print(f"[bold]Generating {pkg_name} template...[/bold]")

    target = TEMPLATES_DIR / pkg_name
    if target.exists():
        if not force:
            console.print(
                f"[red]Error:[/red] Template directory {target} already exists. Use --force to overwrite."
            )
            return False
        shutil.rmtree(target)

    # Copy source to target, ignoring artifacts
    shutil.copytree(source_dir, target, ignore=shutil.ignore_patterns(*ARTIFACTS))
    console.print(f"  Copied {source_dir.name} to template")

    # Generate template.yml
    template_yml = {
        "title": pkg_name.replace("-", " ").title(),
        "description": f"{pkg_name.replace('-', ' ').title()} package",
        "destination": f"packages/{pkg_name}",
        "variables": {},
    }
    (target / "template.yml").write_text(yaml.dump(template_yml, sort_keys=False))
    console.print("  [green]✓[/green] template.yml generated")

    console.print(f"[green]✓ {pkg_name} template complete![/green]")


def main():
    parser = argparse.ArgumentParser(description="Generate RAG Facile templates")
    parser.add_argument(
        "--template",
        choices=[
            "sys-config",
            "chainlit-chat",
            "reflex-chat",
            "albert-client",
            "ingestion",
            "orchestration",
            "rag-core",
            "retrieval",
        ],
        help="Generate a specific template",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Generate all templates",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force overwrite existing templates",
    )
    args = parser.parse_args()

    if not args.template and not args.all:
        parser.print_help()
        return

    # Ensure templates directory exists
    TEMPLATES_DIR.mkdir(parents=True, exist_ok=True)

    templates_to_generate = []
    if args.all:
        templates_to_generate = [
            "sys-config",
            "chainlit-chat",
            "reflex-chat",
            "albert-client",
            "ingestion",
            "orchestration",
            "rag-core",
            "retrieval",
        ]
    else:
        templates_to_generate = [args.template]

    failed = []
    for template in templates_to_generate:
        console.print()
        success = True
        if template == "sys-config":
            result = generate_sys_config(force=args.force)
            if result is False:
                success = False
        elif template == "chainlit-chat":
            result = generate_app_template(
                "chainlit-chat", REPO_ROOT / "apps" / "chainlit-chat", force=args.force
            )
            if result is False:
                success = False
        elif template == "reflex-chat":
            result = generate_app_template(
                "reflex-chat", REPO_ROOT / "apps" / "reflex-chat", force=args.force
            )
            if result is False:
                success = False
        elif template == "albert-client":
            result = generate_package_template(
                "albert-client",
                REPO_ROOT / "packages" / "albert-client",
                force=args.force,
            )
            if result is False:
                success = False
        elif template == "ingestion":
            result = generate_package_template(
                "ingestion",
                REPO_ROOT / "packages" / "ingestion",
                force=args.force,
            )
            if result is False:
                success = False
        elif template == "orchestration":
            result = generate_package_template(
                "orchestration",
                REPO_ROOT / "packages" / "orchestration",
                force=args.force,
            )
            if result is False:
                success = False
        elif template == "retrieval":
            result = generate_package_template(
                "retrieval",
                REPO_ROOT / "packages" / "retrieval",
                force=args.force,
            )
            if result is False:
                success = False
        elif template == "rag-core":
            result = generate_package_template(
                "rag-core", REPO_ROOT / "packages" / "rag-core", force=args.force
            )
            if result is False:
                success = False
        if not success:
            failed.append(template)

    console.print()
    if failed:
        console.print(
            f"[bold yellow]Template generation partially complete.[/bold yellow] Failed templates: {', '.join(failed)}"
        )
        console.print("\nUse --force to overwrite existing templates.")
    else:
        console.print("[bold green]Template generation complete![/bold green]")


if __name__ == "__main__":
    main()
