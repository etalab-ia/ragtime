"""First-run initialization wizard for the rag-facile chat assistant.

Called automatically by start_chat() when .agent/ is absent from the workspace.
Creates the directory structure and profile file that the agent uses
to personalise responses across sessions.
"""

import locale
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
    questionary.Choice("New to RAG — explain everything step by step", value="new"),
    questionary.Choice("Some experience — skip the basics", value="intermediate"),
    questionary.Choice("Expert — minimal guidance", value="expert"),
]


# ── Language detection ────────────────────────────────────────────────────────


def _detect_language() -> str:
    """Infer preferred language from the system locale.

    Returns 'en' when the locale starts with 'en' (e.g. en_US, en_GB),
    'fr' for everything else (French government default).
    """
    try:
        lang, _ = locale.getlocale()
        if lang and lang.lower().startswith("en"):
            return "en"
    except ValueError:
        pass
    return "fr"


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
            "[bold]Welcome to rag-facile![/bold]\n"
            "[dim]Let me set up your AI assistant. This takes about 30 seconds "
            "and only happens once.[/dim]",
            border_style="magenta",
            padding=(0, 1),
        )
    )
    console.print()

    # Language is detected from the system locale — no need to ask.
    language = _detect_language()

    # ── Ask one question ──────────────────────────────────────────────────────
    # questionary returns None on Ctrl+C — fall back to default.
    experience = "new"
    try:
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

    # Write profile.md
    (workspace / _PROFILE_FILE).write_text(
        _profile_template(experience, language), encoding="utf-8"
    )

    # Stage new files in the workspace git
    _git_add(workspace)

    # ── Confirmation ──────────────────────────────────────────────────────────
    console.print()
    console.print("[green]✓[/green] Assistant ready")
    console.print(f"[dim]  Profile: {workspace / _PROFILE_FILE}[/dim]")
    console.print()

    return language
