"""First-run initialization wizard for the rag-facile chat assistant.

Called automatically by start_chat() when .agent/ is absent from the workspace.
Creates the directory structure and profile file that the agent uses
to personalise responses across sessions.
"""

import subprocess
from datetime import date
from pathlib import Path

import questionary
from rich.console import Console
from rich.panel import Panel


console = Console()

# ── Directory / file layout ───────────────────────────────────────────────────

_AGENT_DIR = Path(".agent")
_PROFILE_FILE = _AGENT_DIR / "profile.md"
_SKILLS_DIR = Path(".agents") / "skills"

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
    questionary.Choice("Nouveau — expliquer pas à pas", value="new"),
    questionary.Choice("Quelques notions — passer les bases", value="intermediate"),
    questionary.Choice("Expert — guidance minimale", value="expert"),
]


# ── Template generators ───────────────────────────────────────────────────────


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

## Session Count
0
"""


# ── Helpers ───────────────────────────────────────────────────────────────────


def _git_add(workspace: Path) -> None:
    """Stage .agent/ in the workspace git repo (best-effort)."""
    try:
        subprocess.run(
            ["git", "add", ".agent/"],
            cwd=workspace,
            check=True,
            capture_output=True,
        )
    except FileNotFoundError:
        pass  # git not installed — silently skip
    except subprocess.CalledProcessError as exc:
        console.print(
            f"[dim yellow]⚠ git add .agent/ failed: {exc.stderr.decode().strip()}[/dim yellow]"
        )


# ── Public API ────────────────────────────────────────────────────────────────


def needs_init(workspace: Path) -> bool:
    """Return True if the workspace has no .agent/ directory yet."""
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


def read_experience(workspace: Path) -> str:
    """Read the experience level from profile.md. Defaults to 'new'.

    Returns one of: 'new', 'intermediate', 'expert'.
    """
    profile = workspace / _PROFILE_FILE
    if not profile.exists():
        return "new"
    text = profile.read_text(encoding="utf-8")
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("- Experience level:"):
            value = stripped.split(":", 1)[1].strip().lower()
            if "intermediate" in value or "quelques" in value:
                return "intermediate"
            if "expert" in value:
                return "expert"
            return "new"
    return "new"


def run_init_wizard(workspace: Path) -> str:
    """Run the first-time setup wizard and create .agent/ in the workspace.

    Idempotent if the directory already exists (guarded by needs_init()).
    Uses questionary for interactive prompts; falls back to defaults in
    non-interactive environments (CI, pipe).

    Language is inferred from the system locale (no question asked).

    Returns:
        The detected language code ('fr' or 'en').
    """
    console.print(
        Panel(
            "[bold]Bienvenue dans rag-facile\u00a0![/bold]\n"
            "[dim]Configurons votre assistant IA. Cela prend environ 30 secondes "
            "et ne se fait qu'une seule fois.[/dim]",
            border_style="magenta",
            padding=(0, 1),
        )
    )
    console.print()

    # ── Ask 1 question (language is always French) ────────────────────────────
    language = "fr"
    experience = "new"
    try:
        result = questionary.select(
            "Votre niveau d'expérience avec RAG ?",
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

    # Write profile.md
    (workspace / _PROFILE_FILE).write_text(
        _profile_template(experience, language), encoding="utf-8"
    )

    # Stage new files in the workspace git
    _git_add(workspace)

    # ── Confirmation ──────────────────────────────────────────────────────────
    console.print()
    console.print("[green]✓[/green] Assistant prêt")
    console.print(f"[dim]  Profile: {workspace / _PROFILE_FILE}[/dim]")
    console.print()

    return language
