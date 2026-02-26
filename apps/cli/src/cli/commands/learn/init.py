"""First-run initialization wizard for the rag-facile chat assistant.

Called automatically by start_chat() when .rag-facile/ is absent from the workspace.
Creates the directory structure and initial memory files that the agent uses
to personalise responses and track learning progress across sessions.
"""

import subprocess
from datetime import date
from pathlib import Path

import questionary
from rich.console import Console
from rich.panel import Panel


console = Console()

# ── Directory / file layout ───────────────────────────────────────────────────

_AGENT_DIR = Path(".rag-facile") / "agent"
_MEMORY_FILE = _AGENT_DIR / "MEMORY.md"
_PROFILE_FILE = _AGENT_DIR / "profile.md"
_SKILLS_DIR = Path(".rag-facile") / "skills"

# ── Questionary style (matches setup.py palette) ─────────────────────────────

_STYLE = questionary.Style(
    [
        ("qmark", "fg:#00d7af bold"),
        ("question", "bold"),
        ("answer", "fg:#00d7af bold"),
        ("pointer", "fg:#00d7af bold"),
        ("highlighted", "fg:#00d7af bold"),
        ("selected", "fg:#00d7af"),
    ]
)

_EXPERIENCE_CHOICES = [
    questionary.Choice("New to RAG — explain everything step by step", value="new"),
    questionary.Choice("Some experience — skip the basics", value="intermediate"),
    questionary.Choice("Expert — minimal guidance", value="expert"),
]

_LANGUAGE_CHOICES = [
    questionary.Choice("Français 🇫🇷", value="fr"),
    questionary.Choice("English 🇬🇧", value="en"),
]


# ── Template generators ───────────────────────────────────────────────────────


def _memory_template(project_name: str, preset: str, experience: str) -> str:
    today = date.today().isoformat()
    return f"""\
---
updated: {today}
project: {project_name}
preset: {preset}
---

# Project Memory

## User Profile
- Experience level: {experience}
- Goals: (not yet defined — ask the user)
- Completed topics: (none yet)

## Project State
- Preset: {preset}
- Albert collections: (check ragfacile.toml)

## Learned Facts
(empty — will be populated across sessions)
"""


def _profile_template(experience: str, language: str) -> str:
    today = date.today().isoformat()
    experience_labels = {
        "new": "New to RAG",
        "intermediate": "Some experience",
        "expert": "Expert",
    }
    return f"""\
# User Profile

## Preferences
- Language: {language}
- Experience level: {experience_labels.get(experience, experience)}
- Initialized: {today}

## Learning Progress
(none yet — topics will be marked complete as you learn them)

## Session Count
0
"""


# ── Helpers ───────────────────────────────────────────────────────────────────


def _read_preset(workspace: Path) -> str:
    """Extract the preset name from ragfacile.toml, defaulting to 'balanced'."""
    config_file = workspace / "ragfacile.toml"
    if not config_file.exists():
        return "balanced"
    try:
        import tomllib

        with open(config_file, "rb") as f:
            data = tomllib.load(f)
        return data.get("meta", {}).get("preset", "balanced")
    except tomllib.TOMLDecodeError:
        return "balanced"
    except OSError:
        return "balanced"


def _git_add(workspace: Path) -> None:
    """Stage .rag-facile/ in the workspace git repo (best-effort)."""
    try:
        subprocess.run(
            ["git", "add", ".rag-facile/"],
            cwd=workspace,
            check=True,
            capture_output=True,
        )
    except FileNotFoundError:
        pass  # git not installed — silently skip
    except subprocess.CalledProcessError as exc:
        console.print(
            f"[dim yellow]⚠ git add .rag-facile/ failed: {exc.stderr.decode().strip()}[/dim yellow]"
        )


# ── Public API ────────────────────────────────────────────────────────────────


def needs_init(workspace: Path) -> bool:
    """Return True if the workspace has no .rag-facile/agent/ directory yet."""
    return not (workspace / _AGENT_DIR).exists()


def read_language(workspace: Path) -> str:
    """Read the preferred language from profile.md. Defaults to 'fr'."""
    profile = workspace / _PROFILE_FILE
    if not profile.exists():
        return "fr"
    for line in profile.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped.startswith("- Language:"):
            return stripped.split(":", 1)[1].strip()
    return "fr"


def run_init_wizard(workspace: Path) -> str:
    """Run the first-time setup wizard and create .rag-facile/ in the workspace.

    Idempotent if the directory already exists (guarded by needs_init()).
    Uses questionary for interactive prompts; falls back to defaults in
    non-interactive environments (CI, pipe).

    Returns:
        The selected language code ('fr' or 'en').
    """
    console.print(
        Panel(
            "[bold]Welcome to rag-facile![/bold]\n"
            "[dim]Let me set up your AI assistant. This takes about 30 seconds "
            "and only happens once.[/dim]",
            border_style="magenta",
            padding=(0, 1),
        )
    )
    console.print()

    # ── Ask 2 questions (language first so the rest adapts) ──────────────────
    # questionary returns None on Ctrl+C — check after each question so we
    # don't fall through to the next one when the user cancels.
    language = "fr"
    experience = "new"
    try:
        result = questionary.select(
            "Preferred language for our conversations?",
            choices=_LANGUAGE_CHOICES,
            style=_STYLE,
        ).ask()
        if result is not None:
            language = result
            result = questionary.select(
                "Your experience with RAG?",
                choices=_EXPERIENCE_CHOICES,
                style=_STYLE,
            ).ask()
            if result is not None:
                experience = result
    except (EOFError, OSError):
        pass  # non-interactive terminal (pipe, CI) — keep defaults

    # ── Create directory structure ────────────────────────────────────────────
    agent_dir = workspace / _AGENT_DIR
    agent_dir.mkdir(parents=True, exist_ok=True)
    (workspace / _SKILLS_DIR).mkdir(parents=True, exist_ok=True)

    project_name = workspace.name
    preset = _read_preset(workspace)

    # Write MEMORY.md
    (workspace / _MEMORY_FILE).write_text(
        _memory_template(project_name, preset, experience), encoding="utf-8"
    )

    # Write profile.md
    (workspace / _PROFILE_FILE).write_text(
        _profile_template(experience, language), encoding="utf-8"
    )

    # Stage new files in the workspace git
    _git_add(workspace)

    # ── Confirmation ──────────────────────────────────────────────────────────
    console.print()
    console.print("[green]✓[/green] Assistant ready")
    console.print(f"[dim]  Memory: {workspace / _MEMORY_FILE}[/dim]")
    console.print(f"[dim]  Profile: {workspace / _PROFILE_FILE}[/dim]")
    console.print()

    return language
