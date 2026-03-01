"""Path constants for the .rag-facile/ memory layout.

All paths are relative to the workspace root (the directory containing
``ragfacile.toml``).  Functions accept a ``workspace: Path`` argument and
return absolute paths.
"""

from __future__ import annotations

from pathlib import Path


# ── Relative path segments ────────────────────────────────────────────────────

AGENT_DIR = Path(".rag-facile") / "agent"
MEMORY_FILE = AGENT_DIR / "memory.md"
PROFILE_FILE = AGENT_DIR / "profile.md"
LOGS_DIR = AGENT_DIR / "logs"
SESSIONS_DIR = AGENT_DIR / "sessions"
INDEX_DIR = AGENT_DIR / ".index"
INDEX_DB = INDEX_DIR / "memory.db"


# ── Resolved helpers ──────────────────────────────────────────────────────────


def ensure_dirs(workspace: Path) -> None:
    """Create all memory directories if they don't exist."""
    for d in (AGENT_DIR, LOGS_DIR, SESSIONS_DIR, INDEX_DIR):
        (workspace / d).mkdir(parents=True, exist_ok=True)
