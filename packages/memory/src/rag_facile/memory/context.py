"""Bootstrap context loader for session start.

Assembles a formatted string from:
  1. Semantic Store (``memory.md`` — capped at 200 lines)
  2. Profile (``profile.md``)
  3. Recent Episodic Logs (today + yesterday)

The result is injected into the first user turn of the session so the
model pays full attention to it (instead of burying it at the end of
smolagents' long built-in system prompt).
"""

from __future__ import annotations

from pathlib import Path

from rag_facile.memory._paths import PROFILE_FILE
from rag_facile.memory.stores import EpisodicLog, SemanticStore


def bootstrap_context(workspace: Path, *, log_days: int = 2) -> str:
    """Return the combined memory context for the start of a session.

    Parameters
    ----------
    workspace:
        Root directory containing ``.rag-facile/``.
    log_days:
        Number of past days of episodic logs to include (default 2).

    Returns
    -------
    str
        Formatted context string (may be empty if no memory files exist).
    """
    sections: list[str] = []

    # 1. Semantic store (curated facts, capped at 200 lines)
    semantic = SemanticStore.load(workspace)
    if semantic:
        sections.append(f"[Memory — Semantic Store]\n{semantic}")

    # 2. Profile
    profile_path = workspace / PROFILE_FILE
    if profile_path.exists():
        profile = profile_path.read_text(encoding="utf-8").strip()
        if profile:
            sections.append(f"[Memory — Profile]\n{profile}")

    # 3. Recent episodic logs
    logs = EpisodicLog.read_recent(workspace, days=log_days)
    if logs:
        sections.append(f"[Memory — Recent Conversations]\n{logs}")

    if not sections:
        return ""

    return "\n\n---\n\n".join(sections)
