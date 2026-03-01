"""Storage backends for the three memory types.

* **SemanticStore** — curated ``memory.md`` with fixed section headers
* **EpisodicLog** — append-only daily logs under ``logs/``
* **SessionSnapshot** — archived session transcripts under ``sessions/``
"""

from __future__ import annotations

import re
import textwrap
from datetime import date, datetime
from pathlib import Path

from rag_facile.memory._paths import (
    LOGS_DIR,
    MEMORY_FILE,
    SESSIONS_DIR,
    ensure_dirs,
)

# ── Semantic Store ────────────────────────────────────────────────────────────

# Fixed section headers (order matters for the template).
SEMANTIC_SECTIONS: list[str] = [
    "User Identity",
    "Preferences",
    "Project State",
    "Key Facts",
    "Routing Table",
    "Recent Context",
]

_MEMORY_TEMPLATE = textwrap.dedent("""\
    ---
    updated: {today}
    ---

    # Agent Memory

    ## User Identity
    - Name: (not yet known)
    - Role: (not yet known)

    ## Preferences

    ## Project State

    ## Key Facts

    ## Routing Table
    | Topic | File |
    |-------|------|

    ## Recent Context
""")

# Cap for bootstrap injection (mirrors Claude Code's CLAUDE.md strategy).
MAX_SEMANTIC_LINES = 200


class SemanticStore:
    """Read / write operations on the structured ``memory.md``."""

    # ── Read ──────────────────────────────────────────────────────────────

    @staticmethod
    def load(workspace: Path, *, max_lines: int = MAX_SEMANTIC_LINES) -> str:
        """Return the full content of ``memory.md``, capped at *max_lines*.

        Returns an empty string if the file does not exist.
        """
        path = workspace / MEMORY_FILE
        if not path.exists():
            return ""
        lines = path.read_text(encoding="utf-8").splitlines()
        return "\n".join(lines[:max_lines])

    @staticmethod
    def read_section(workspace: Path, section: str) -> list[str]:
        """Return the entries (lines) under a ``## <section>`` header.

        Lines are stripped; blank lines and sub-headers are excluded.
        """
        path = workspace / MEMORY_FILE
        if not path.exists():
            return []
        content = path.read_text(encoding="utf-8")
        pattern = rf"^## {re.escape(section)}\s*$"
        match = re.search(pattern, content, re.MULTILINE)
        if not match:
            return []
        # Collect lines until the next ## header or EOF
        start = match.end()
        rest = content[start:]
        next_section = re.search(r"^## ", rest, re.MULTILINE)
        block = rest[: next_section.start()] if next_section else rest
        return [
            line.strip()
            for line in block.splitlines()
            if line.strip() and not line.strip().startswith("## ")
        ]

    # ── Write ─────────────────────────────────────────────────────────────

    @staticmethod
    def create(workspace: Path) -> Path:
        """Create the initial ``memory.md`` from the template.

        Returns the path to the created file.
        """
        ensure_dirs(workspace)
        path = workspace / MEMORY_FILE
        path.write_text(
            _MEMORY_TEMPLATE.format(today=date.today().isoformat()),
            encoding="utf-8",
        )
        return path

    @staticmethod
    def add_entry(workspace: Path, section: str, entry: str) -> None:
        """Append a date-stamped entry to *section* in ``memory.md``.

        Creates the file from the template if it does not exist yet.
        """
        path = workspace / MEMORY_FILE
        if not path.exists():
            SemanticStore.create(workspace)
        content = path.read_text(encoding="utf-8")

        today = date.today().isoformat()
        stamped = f"- [{today}] {entry}"

        header_pattern = rf"^(## {re.escape(section)}\s*\n)"
        match = re.search(header_pattern, content, re.MULTILINE)
        if not match:
            # Section missing — append at end
            content = content.rstrip() + f"\n\n## {section}\n{stamped}\n"
        else:
            insert_pos = match.end()
            content = content[:insert_pos] + stamped + "\n" + content[insert_pos:]

        # Update frontmatter date
        content = re.sub(
            r"^(updated:\s*).+$",
            rf"\g<1>{today}",
            content,
            count=1,
            flags=re.MULTILINE,
        )
        path.write_text(content, encoding="utf-8")

    @staticmethod
    def update_frontmatter(workspace: Path, **fields: str) -> None:
        """Update YAML frontmatter key-value pairs in ``memory.md``."""
        path = workspace / MEMORY_FILE
        if not path.exists():
            return
        content = path.read_text(encoding="utf-8")
        for key, value in fields.items():
            pattern = rf"^({re.escape(key)}:\s*).+$"
            if re.search(pattern, content, re.MULTILINE):
                content = re.sub(
                    pattern, rf"\g<1>{value}", content, count=1, flags=re.MULTILINE
                )
            else:
                # Insert after the opening --- line
                content = content.replace("---\n", f"---\n{key}: {value}\n", 1)
        path.write_text(content, encoding="utf-8")


# ── Episodic Log ──────────────────────────────────────────────────────────────


class EpisodicLog:
    """Append-only daily logs under ``logs/YYYY-MM-DD.md``."""

    @staticmethod
    def today_path(workspace: Path) -> Path:
        """Return the path to today's log file."""
        return workspace / LOGS_DIR / f"{date.today().isoformat()}.md"

    @staticmethod
    def append_turn(workspace: Path, role: str, content: str) -> None:
        """Append a timestamped turn to today's daily log.

        Creates the file (with a date header) if it doesn't exist yet.
        """
        ensure_dirs(workspace)
        path = EpisodicLog.today_path(workspace)
        now = datetime.now().strftime("%H:%M")  # noqa: DTZ005 — local time is intentional
        label = "Vous" if role == "user" else "Assistant"

        parts: list[str] = []
        if not path.exists():
            parts.append(f"# {date.today().isoformat()}\n")
        parts.append(f"\n## {now} — {label}\n{content}\n")

        with path.open("a", encoding="utf-8") as f:
            f.write("".join(parts))

    @staticmethod
    def append_checkpoint(
        workspace: Path,
        summary: str,
        decisions: str = "",
        facts: str = "",
    ) -> None:
        """Append a structured checkpoint entry to today's log."""
        ensure_dirs(workspace)
        path = EpisodicLog.today_path(workspace)
        now = datetime.now().strftime("%H:%M")  # noqa: DTZ005

        lines = [f"\n## {now} — Checkpoint\n**Summary**: {summary}\n"]
        if decisions:
            lines.append(f"**Decisions**: {decisions}\n")
        if facts:
            lines.append(f"**New facts**: {facts}\n")

        with path.open("a", encoding="utf-8") as f:
            f.write("".join(lines))

    @staticmethod
    def read_recent(workspace: Path, *, days: int = 2) -> str:
        """Return the content of the last *days* log files, most recent first.

        Returns an empty string if no log files exist.
        """
        logs_dir = workspace / LOGS_DIR
        if not logs_dir.exists():
            return ""
        files = sorted(logs_dir.glob("*.md"), reverse=True)[:days]
        if not files:
            return ""
        return "\n\n---\n\n".join(f.read_text(encoding="utf-8").strip() for f in files)


# ── Session Snapshot ──────────────────────────────────────────────────────────


def _slugify(text: str, max_words: int = 5) -> str:
    """Convert text to a filename-safe slug (first *max_words* words)."""
    words = re.sub(r"[^\w\s-]", "", text.lower()).split()[:max_words]
    return "-".join(words) or "session"


class SessionSnapshot:
    """Archived session transcripts under ``sessions/``."""

    @staticmethod
    def save(
        workspace: Path,
        turns: list[dict[str, str]],
        summary: str,
        topics: list[str],
        start_time: datetime,
    ) -> Path:
        """Write a session snapshot and return the file path.

        *turns* is a list of ``{"role": ..., "content": ...}`` dicts.
        """
        ensure_dirs(workspace)
        end_time = datetime.now()  # noqa: DTZ005
        slug = _slugify(summary)
        filename = f"{start_time.strftime('%Y-%m-%d-%H%M')}-{slug}.md"
        path = workspace / SESSIONS_DIR / filename

        # Build YAML frontmatter
        topics_yaml = "\n".join(f"  - {t}" for t in topics) if topics else "  []"
        header = (
            f"---\n"
            f"date: {start_time.strftime('%Y-%m-%d')}\n"
            f'started: "{start_time.strftime("%H:%M")}"\n'
            f'ended: "{end_time.strftime("%H:%M")}"\n'
            f"turns: {len(turns)}\n"
            f"summary: {summary}\n"
            f"topics:\n{topics_yaml}\n"
            f"---\n\n"
        )

        # Build transcript body
        body_parts = [f"# Session: {summary}\n"]
        for turn in turns:
            label = "Vous" if turn.get("role") == "user" else "Assistant"
            body_parts.append(f"\n## {label}\n{turn.get('content', '')}\n")

        path.write_text(header + "".join(body_parts), encoding="utf-8")
        return path

    @staticmethod
    def list_recent(workspace: Path, *, n: int = 10) -> list[Path]:
        """Return paths to the *n* most recent session snapshots."""
        sessions_dir = workspace / SESSIONS_DIR
        if not sessions_dir.exists():
            return []
        return sorted(sessions_dir.glob("*.md"), reverse=True)[:n]

    @staticmethod
    def load(path: Path) -> str:
        """Read a snapshot file and return its content."""
        return path.read_text(encoding="utf-8")
