"""Git-backed session memory for the rag-facile chat assistant.

Handles four concerns:
  - load_context()          : read MEMORY.md + profile.md → system instructions
  - append_turn()           : write each exchange to today's conversation log
  - update_memory()         : post-session Albert call → append new facts to MEMORY.md
  - git_commit_session()    : git add .rag-facile/ && commit
  - increment_session_count(): bump Session Count in profile.md
"""

import os
import re
import subprocess
from datetime import date, datetime
from pathlib import Path

import openai
from rich.console import Console


console = Console()

# ── File paths (mirrors init.py layout) ──────────────────────────────────────

_AGENT_DIR = Path(".rag-facile") / "agent"
_MEMORY_FILE = _AGENT_DIR / "MEMORY.md"
_PROFILE_FILE = _AGENT_DIR / "profile.md"
_CONVERSATIONS_DIR = _AGENT_DIR / "conversations"

# ── Context loading ───────────────────────────────────────────────────────────


def load_context(workspace: Path) -> str:
    """Return MEMORY.md + profile.md as a formatted string for system instructions.

    Returns empty string if neither file exists (e.g. outside a workspace).
    """
    parts: list[str] = []

    memory_file = workspace / _MEMORY_FILE
    if memory_file.exists():
        parts.append(memory_file.read_text(encoding="utf-8").strip())

    profile_file = workspace / _PROFILE_FILE
    if profile_file.exists():
        parts.append(profile_file.read_text(encoding="utf-8").strip())

    return "\n\n---\n\n".join(parts) if parts else ""


# ── Turn logging ──────────────────────────────────────────────────────────────


def _conversation_file(workspace: Path) -> Path:
    """Return path to today's conversation log, creating the dir if needed."""
    conv_dir = workspace / _CONVERSATIONS_DIR
    conv_dir.mkdir(parents=True, exist_ok=True)
    return conv_dir / f"{date.today().isoformat()}.md"


def append_turn(workspace: Path, role: str, content: str) -> None:
    """Append a single exchange turn to today's conversation log.

    Creates the file with a header on first write of the day.
    """
    log_file = _conversation_file(workspace)
    timestamp = datetime.now().strftime("%H:%M")

    if not log_file.exists():
        log_file.write_text(
            f"# Session {date.today().isoformat()}\n\n", encoding="utf-8"
        )

    with log_file.open("a", encoding="utf-8") as f:
        label = "Vous" if role == "user" else "Assistant"
        f.write(f"## {timestamp} {label}\n\n{content}\n\n")


# ── Session count ─────────────────────────────────────────────────────────────


def increment_session_count(workspace: Path) -> int:
    """Increment the Session Count in profile.md and return the new value."""
    profile_file = workspace / _PROFILE_FILE
    if not profile_file.exists():
        return 1

    content = profile_file.read_text(encoding="utf-8")

    # Profile ends with "## Session Count\n<number>"
    match = re.search(r"(## Session Count\n)(\d+)", content)
    if match:
        new_count = int(match.group(2)) + 1
        content = content[: match.start(2)] + str(new_count) + content[match.end(2) :]
        profile_file.write_text(content, encoding="utf-8")
        return new_count
    return 1


# ── Post-session memory update ────────────────────────────────────────────────

_UPDATE_SYSTEM = """\
You are updating an AI assistant's persistent memory file.
Given the current memory and a session transcript, extract 0-3 new facts
worth remembering for future sessions.

Rules:
- Return ONLY bullet points starting with "- ", one per line
- Do NOT repeat facts already present in the memory
- If nothing new is worth noting, return an empty string
- Keep each fact concise (one sentence max)
"""


def update_memory(workspace: Path, session_log: str) -> None:
    """Ask Albert to extract new facts from the session and append to MEMORY.md.

    Best-effort: logs a warning on API failure, never raises.
    """
    if not session_log.strip():
        return

    memory_file = workspace / _MEMORY_FILE
    if not memory_file.exists():
        return

    current_memory = memory_file.read_text(encoding="utf-8")

    try:
        client = openai.OpenAI(
            api_key=os.getenv("OPENAI_API_KEY") or os.getenv("ALBERT_API_KEY", ""),
            base_url=os.getenv(
                "OPENAI_BASE_URL", "https://albert.api.etalab.gouv.fr/v1"
            ),
        )
        response = client.chat.completions.create(
            model=os.getenv("OPENAI_MODEL", "meta-llama/Llama-3.1-70B-Instruct"),
            messages=[
                {"role": "system", "content": _UPDATE_SYSTEM},
                {
                    "role": "user",
                    "content": (
                        f"Current memory:\n{current_memory}\n\n"
                        f"Session transcript:\n{session_log}"
                    ),
                },
            ],
            max_tokens=200,
            temperature=0.1,
        )
        new_facts = (response.choices[0].message.content or "").strip()
    except openai.APIError as exc:
        console.print(f"[dim yellow]⚠ Memory update skipped: {exc}[/dim yellow]")
        return

    if not new_facts:
        return

    # Remove placeholder line if still present
    updated = current_memory.replace("(empty — will be populated across sessions)", "")

    # Update frontmatter 'updated' date
    updated = re.sub(
        r"^updated: .*$",
        f"updated: {date.today().isoformat()}",
        updated,
        flags=re.MULTILINE,
    )

    # Ensure "## Learned Facts" section exists, then append
    if "## Learned Facts" not in updated:
        updated = updated.rstrip() + "\n\n## Learned Facts\n"
    updated = updated.rstrip() + f"\n{new_facts}\n"

    memory_file.write_text(updated, encoding="utf-8")


# ── Git commit ────────────────────────────────────────────────────────────────


def git_commit_session(workspace: Path) -> None:
    """Stage and commit .rag-facile/ changes with a session commit message.

    Best-effort: silent when git is absent or .rag-facile/ is gitignored
    (expected when running from the source repo during development).
    """
    today = date.today().isoformat()
    try:
        # Skip silently if .rag-facile/ is ignored by the workspace .gitignore
        # (exit code 0 = ignored, 1 = not ignored, 128 = not a git repo)
        check = subprocess.run(
            ["git", "check-ignore", "-q", ".rag-facile/"],
            cwd=workspace,
            capture_output=True,
        )
        if check.returncode == 0:
            return  # gitignored — skip (dev / source-repo scenario)

        subprocess.run(
            ["git", "add", ".rag-facile/"],
            cwd=workspace,
            check=True,
            capture_output=True,
        )
        diff = subprocess.run(
            ["git", "diff", "--cached", "--quiet"],
            cwd=workspace,
            capture_output=True,
        )
        if diff.returncode == 0:
            return  # nothing staged — skip commit

        subprocess.run(
            ["git", "commit", "-m", f"agent: session {today}"],
            cwd=workspace,
            check=True,
            capture_output=True,
        )
    except FileNotFoundError:
        pass  # git not installed
    except subprocess.CalledProcessError as exc:
        console.print(
            f"[dim yellow]⚠ Session commit failed: {exc.stderr.decode().strip()}[/dim yellow]"
        )
