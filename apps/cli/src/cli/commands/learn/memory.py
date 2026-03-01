"""User profile context for the rag-facile chat assistant.

Handles two concerns:
  - load_context()            : read profile.md → context string for the agent
  - increment_session_count() : bump Session Count in profile.md
"""

import re
from pathlib import Path


# ── File paths (mirrors init.py layout) ──────────────────────────────────────

_AGENT_DIR = Path(".rag-facile") / "agent"
_PROFILE_FILE = _AGENT_DIR / "profile.md"


# ── Context loading ───────────────────────────────────────────────────────────


def load_context(workspace: Path) -> str:
    """Return profile.md as a formatted string for the agent's first turn.

    Returns empty string if the file does not exist (e.g. outside a workspace).
    """
    profile_file = workspace / _PROFILE_FILE
    if profile_file.exists():
        return profile_file.read_text(encoding="utf-8").strip()
    return ""


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
