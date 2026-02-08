import shutil
from enum import Enum
from pathlib import Path
from typing import Annotated

import libcst as cst
import typer
import yaml
from rich.console import Console


app = typer.Typer()
console = Console()


class AppType(str, Enum):
    chainlit = "chainlit-chat"
    reflex = "reflex-chat"


def _generate_template_yml(app_type: AppType) -> str:
    """Generate the template.yml content for Moon."""
    if app_type == AppType.chainlit:
        config = {
            "title": "Chainlit Chat",
            "description": "A Chainlit Chat Application with OpenAI Functions",
            "variables": {
                "project_name": {
                    "type": "string",
                    "default": "my-chainlit-app",
                    "prompt": "What is the name of your project?",
                },
                "description": {
                    "type": "string",
                    "default": "A Chainlit Chat Application",
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
                    "default": "You are a helpful assistant.",
                    "prompt": "Initial system prompt for the assistant",
                },
                "welcome_message": {
                    "type": "string",
                    "default": "Welcome to Chainlit! 🚀🤖",
                    "prompt": "Header text for the welcome screen",
                },
            },
        }
    else:
        config = {
            "title": "Reflex Chat",
            "description": "A Reflex Chat Application",
            "variables": {
                "project_name": {
                    "type": "string",
                    "default": "my-reflex-app",
                    "prompt": "What is the name of your project?",
                },
                "description": {
                    "type": "string",
                    "default": "A Reflex Chat Application",
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
                    "default": (
                        "You are a friendly chatbot named Reflex. Respond in markdown."
                    ),
                    "prompt": "Initial system prompt for the assistant",
                },
            },
        }
    return yaml.dump(config, sort_keys=False, allow_unicode=True)


# Placeholders to maintain valid Python syntax during CST pass
PLACEHOLDERS = {
    "chainlit_chat": "__PROJECT_SLUG_PLACEHOLDER__",
    "reflex_chat": "__PROJECT_SLUG_PLACEHOLDER__",
}


class JinjaTransformer(cst.CSTTransformer):
    """
    LibCST Transformer to parameterize Python code.
    Phase 1: Semantic Preparation
    """

    def __init__(self, mappings: dict[str, str]):
        self.mappings = mappings

    def leave_SimpleString(
        self, original_node: cst.SimpleString, updated_node: cst.SimpleString
    ) -> cst.SimpleString:
        # Parameterize strings
        val = updated_node.value
        for golden, tag in self.mappings.items():
            if golden in val:
                # Replace golden value with Jinja tag inside the string
                new_val = val.replace(golden, tag)
                return updated_node.with_changes(value=new_val)
        return updated_node

    def leave_Name(self, original_node: cst.Name, updated_node: cst.Name) -> cst.Name:
        # Parameterize identifiers using placeholders
        if updated_node.value in PLACEHOLDERS:
            return updated_node.with_changes(value=PLACEHOLDERS[updated_node.value])
        return updated_node


@app.command()
def generate(
    app_type: Annotated[
        AppType, typer.Option("--app", help="The application template to generate")
    ],
):
    """
    Generate a Chat app template using a Hybrid LibCST + ast-grep pipeline.
    Copies apps/<app_type> to .moon/templates/<app_type> and parameterizes it.
    """
    # Robustly find repo root (assumes gen_template.py is in apps/cli/src/cli/commands/)
    repo_root = Path(__file__).resolve().parents[5]
    source = repo_root / "apps" / app_type.value
    target = repo_root / ".moon" / "templates" / app_type.value

    if not source.exists():
        console.print(f"[red]Error: Source directory {source} does not exist.[/red]")
        raise typer.Exit(code=1)

    # Cleanup artifacts patterns
    artifacts = [
        "__pycache__",
        "*.egg-info",
        ".venv",
        ".env",
        ".git",
        ".DS_Store",
    ]
    # Specific artifacts per app
    if app_type == AppType.reflex:
        artifacts.extend([".web", ".states"])
    else:
        artifacts.extend([".chainlit"])

    console.print(f"Recreating {target}...")
    if target.exists():
        shutil.rmtree(target)

    # Copy source to target, ignoring artifacts
    shutil.copytree(source, target, ignore=shutil.ignore_patterns(*artifacts))

    # Bundle pdf-context package for chainlit-chat and reflex-chat
    if app_type in [AppType.chainlit, AppType.reflex]:
        pdf_pkg_src = repo_root / "packages" / "pdf-context"
        if pdf_pkg_src.exists():
            pkg_target = target / "packages" / "pdf-context"
            # Ignore same artifacts in pdf-context bundle
            shutil.copytree(
                pdf_pkg_src, pkg_target, ignore=shutil.ignore_patterns(*artifacts)
            )
            console.print("✔ Bundled pdf-context package")

    # Moon renders all files, so we don't strictly need .jinja suffixes.
    # We'll remove them to ensure the output files have the correct names.
    console.print("Applying parameterization pipeline...")

    # Phase 1: Semantic Preparation with LibCST
    mappings = {
        app_type.value: "{{ project_name }}",
        app_type.value.replace(
            "-", "_"
        ): "{{ project_name | replace(from='-', to='_') }}",
        "You are a helpful assistant.": "{{ system_prompt }}",
        "You are a friendly chatbot named Reflex. Respond in markdown.": (
            "{{ system_prompt }}"
        ),
    }

    if app_type == AppType.chainlit:
        mappings.update(
            {
                "Chainlit Chat with OpenAI Functions Streaming": "{{ description }}",
                "Welcome to Chainlit! 🚀🤖": "{{ welcome_message }}",
            }
        )
    else:
        mappings.update(
            {
                "Reflex Chat Application": "{{ description }}",
            }
        )

    python_files = list(target.rglob("*.py"))
    for py_file in python_files:
        code = py_file.read_text()
        try:
            tree = cst.parse_module(code)
            transformer = JinjaTransformer(mappings)
            modified_tree = tree.visit(transformer)
            py_file.write_text(modified_tree.code)
            console.print(f"✔ LibCST pass applied to {py_file.name}")
        except Exception as e:
            console.print(
                f"[yellow]Warning: LibCST failed for {py_file.name}: {e}[/yellow]"
            )

    # Phase 2: Structural Injection (Replacing placeholders)
    # Inject actual Tera tags where LibCST placeholders were used
    for placeholder in set(PLACEHOLDERS.values()):
        replacement = "{{ project_name | replace(from='-', to='_') }}"
        for file_path in target.rglob("*"):
            if file_path.is_file() and not file_path.suffix == ".so":
                try:
                    content = file_path.read_text()
                    if placeholder in content:
                        file_path.write_text(content.replace(placeholder, replacement))
                        console.print(
                            f"✔ Placeholder {placeholder} replaced in {file_path.name}"
                        )
                except (UnicodeDecodeError, PermissionError):
                    continue

    # Phase 3: App-Specific Parameterization and Metadata
    template_yml = _generate_template_yml(app_type)

    # Parameterize pyproject.toml
    pyproject_path = target / "pyproject.toml"
    if pyproject_path.exists():
        content = pyproject_path.read_text()
        content = content.replace(f'"{app_type.value}"', '"{{ project_name }}"')

        # Rewrite pdf-context dependency to local path
        content = content.replace(
            "pdf-context = { workspace = true }",
            'pdf-context = { path = "packages/pdf-context" }',
        )

        if app_type == AppType.chainlit:
            msg = "Chainlit Chat with OpenAI Functions Streaming"
            content = content.replace(f'"{msg}"', '"{{ description }}"')
        else:
            content = content.replace(
                '"Reflex Chat Application"', '"{{ description }}"'
            )

        # Add tool.uv.package = true to suppress warnings about entry points
        content += "\n[tool.uv]\npackage = true\n"

        pyproject_path.write_text(content)
        console.print("✔ pyproject.toml parameterized")

    # Generate parameterized .env.template
    console.print("Generating parameterized .env.template...")
    env_content = (
        "OPENAI_API_KEY={{ openai_api_key }}\n"
        "OPENAI_BASE_URL={{ openai_base_url }}\n"
        "OPENAI_MODEL={{ openai_model }}\n"
    )
    (target / ".env.template").write_text(env_content)

    if app_type == AppType.chainlit:
        # Parameterize chainlit.md
        md_path = target / "chainlit.md"
        if md_path.exists():
            content = md_path.read_text()
            content = content.replace(
                "# Welcome to Chainlit! 🚀🤖", "# {{ welcome_message }}"
            )
            md_path.write_text(content)
            console.print("✔ chainlit.md parameterized")

    elif app_type == AppType.reflex:
        # Parameterize rxconfig.py
        rxconfig_path = target / "rxconfig.py"
        if rxconfig_path.exists():
            content = rxconfig_path.read_text()
            content = content.replace(
                'app_name="reflex_chat"',
                "app_name=\"{{ project_name | replace(from='-', to='_') }}\"",
            )
            rxconfig_path.write_text(content)
            console.print("✔ rxconfig.py parameterized")

        # Reflex specific directory renames
        pkg_dir = target / "reflex_chat"
        if pkg_dir.exists():
            # Rename main app file
            main_app = pkg_dir / "reflex_chat.py"
            if main_app.exists():
                # Use Moon path interpolation syntax [var]
                new_app_name = "[project_name | replace(from='-', to='_')].py"
                main_app.rename(pkg_dir / new_app_name)

            # Rename package directory
            new_pkg_dir_name = "[project_name | replace(from='-', to='_')]"
            pkg_dir.rename(target / new_pkg_dir_name)
            console.print("✔ Reflex package structure parameterized")

    # Generate template.yml
    console.print("Generating template.yml...")
    (target / "template.yml").write_text(template_yml)

    console.print(f"[green]Template generation complete for {app_type.value}![/green]")


if __name__ == "__main__":
    app()
