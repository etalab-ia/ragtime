"""Session lifecycle hooks — checkpointing, finalisation, git commit.

Coordinates the memory stores during and after a chat session:

* **Checkpointing** — mid-session flush of key details before they scroll
  out of the agent's context window.
* **Finalisation** — end-of-session: save snapshot, update semantic store,
  increment session count, git commit.
* **Git commit** — best-effort commit of ``.rag-facile/`` changes.
"""

from __future__ import annotations

import logging
import re
import subprocess
from datetime import datetime
from pathlib import Path

from rag_facile.memory._paths import PROFILE_FILE
from rag_facile.memory.stores import EpisodicLog, SemanticStore, SessionSnapshot

logger = logging.getLogger(__name__)


# ── Checkpointing ─────────────────────────────────────────────────────────────


def should_checkpoint(turn_count: int, *, interval: int = 8) -> bool:
    """Return True if it's time for a mid-session checkpoint."""
    return turn_count > 0 and turn_count % interval == 0


def run_checkpoint(
    workspace: Path,
    recent_turns: list[dict[str, str]],
    *,
    summarise_fn: object | None = None,
) -> None:
    """Execute a mid-session checkpoint.

    1. Build a transcript from *recent_turns*
    2. If *summarise_fn* is provided, call it to generate a summary;
       otherwise use the last assistant response as a rough summary.
    3. Append a Checkpoint entry to today's episodic log.

    Parameters
    ----------
    summarise_fn:
        Optional callable ``(transcript: str) -> str`` that produces a
        concise summary.  Typically wraps an Albert API call.
    """
    if not recent_turns:
        return

    transcript = _format_transcript(recent_turns)
    if summarise_fn is not None:
        summary = str(summarise_fn(transcript))
    else:
        # Fallback: use the last assistant message as the summary
        assistant_msgs = [
            t["content"] for t in recent_turns if t["role"] == "assistant"
        ]
        summary = (
            (assistant_msgs[-1][:200] + "…") if assistant_msgs else "Session checkpoint"
        )

    EpisodicLog.append_checkpoint(workspace, summary=summary)


# ── Session finalisation ──────────────────────────────────────────────────────


def finalize_session(
    workspace: Path,
    turns: list[dict[str, str]],
    start_time: datetime,
    *,
    summarise_fn: object | None = None,
    extract_facts_fn: object | None = None,
) -> None:
    """Run all end-of-session housekeeping.

    1. Skip if there are no turns (immediate quit).
    2. Generate a summary (via *summarise_fn* or fallback).
    3. Save a session snapshot.
    4. If *extract_facts_fn* is provided, extract facts and update the
       semantic store.
    5. Increment the session count in ``profile.md``.
    6. Git-commit all changes.

    Parameters
    ----------
    summarise_fn:
        Optional ``(transcript: str) -> str``.
    extract_facts_fn:
        Optional ``(transcript: str) -> list[str]`` returning new facts
        to add to the semantic store.
    """
    if not turns:
        return

    transcript = _format_transcript(turns)

    # Summary
    if summarise_fn is not None:
        summary = str(summarise_fn(transcript))
    else:
        # Simple fallback: first user question
        user_msgs = [t["content"] for t in turns if t["role"] == "user"]
        summary = (user_msgs[0][:80] + "…") if user_msgs else "Chat session"

    # Topics: extract unique non-trivial words from user messages (naive)
    topics = _extract_topics(turns)

    # 1. Session snapshot
    SessionSnapshot.save(
        workspace,
        turns=turns,
        summary=summary,
        topics=topics,
        start_time=start_time,
    )

    # 2. Semantic store updates (if we have an LLM-backed extractor)
    if extract_facts_fn is not None:
        try:
            facts = extract_facts_fn(transcript)
            for fact in facts:
                if fact and fact.strip():
                    SemanticStore.add_entry(workspace, "Key Facts", fact.strip())
        except (OSError, ValueError):
            logger.warning("Failed to extract facts — skipping semantic update")

    # 3. Session count
    increment_session_count(workspace)

    # 4. Git commit
    git_commit_session(workspace)


# ── Session count ─────────────────────────────────────────────────────────────


def increment_session_count(workspace: Path) -> int:
    """Increment the Session Count in profile.md and return the new value."""
    profile_file = workspace / PROFILE_FILE
    if not profile_file.exists():
        return 1

    content = profile_file.read_text(encoding="utf-8")

    match = re.search(r"(## Session Count\n)(\d+)", content)
    if match:
        new_count = int(match.group(2)) + 1
        content = content[: match.start(2)] + str(new_count) + content[match.end(2) :]
        profile_file.write_text(content, encoding="utf-8")
        return new_count
    return 1


# ── Git ───────────────────────────────────────────────────────────────────────


def git_commit_session(workspace: Path) -> None:
    """Best-effort git commit of ``.rag-facile/`` changes.

    Silently skips if:
    - git is not installed
    - the workspace is not a git repo
    - ``.rag-facile/`` is gitignored
    - there's nothing to commit
    """
    try:
        # Check if .rag-facile/ is gitignored — if so, skip silently
        result = subprocess.run(
            ["git", "check-ignore", "-q", str(workspace / ".rag-facile")],
            cwd=workspace,
            capture_output=True,
        )
        if result.returncode == 0:
            return  # gitignored

        # Stage changes
        subprocess.run(
            ["git", "add", str(workspace / ".rag-facile/")],
            cwd=workspace,
            check=True,
            capture_output=True,
        )

        # Check if there's anything staged
        diff = subprocess.run(
            ["git", "diff", "--cached", "--quiet"],
            cwd=workspace,
            capture_output=True,
        )
        if diff.returncode == 0:
            return  # nothing to commit

        # Commit
        subprocess.run(
            [
                "git",
                "commit",
                "-m",
                f"agent: session {datetime.now().strftime('%Y-%m-%d')}",
            ],  # noqa: DTZ005
            cwd=workspace,
            check=True,
            capture_output=True,
        )
    except FileNotFoundError:
        pass  # git not installed
    except subprocess.CalledProcessError as exc:
        logger.debug(
            "git commit failed: %s", exc.stderr.decode() if exc.stderr else exc
        )


# ── Helpers ───────────────────────────────────────────────────────────────────


def _format_transcript(turns: list[dict[str, str]]) -> str:
    """Format a list of turns into a readable transcript string."""
    lines: list[str] = []
    for turn in turns:
        label = "Vous" if turn.get("role") == "user" else "Assistant"
        lines.append(f"{label}: {turn.get('content', '')}")
    return "\n".join(lines)


# Simple French stopwords for topic extraction
_STOPWORDS = frozenset(
    "le la les un une des de du au aux et ou en à par pour dans sur "
    "avec est ce cette que qui ne pas je tu il elle nous vous ils elles "
    "se son sa ses leur leurs mon ma mes ton ta tes notre votre "
    "the a an and or in on at to for with is are was were of from by".split()
)


def _extract_topics(turns: list[dict[str, str]], *, max_topics: int = 5) -> list[str]:
    """Extract simple keyword topics from user messages."""
    words: dict[str, int] = {}
    for turn in turns:
        if turn.get("role") != "user":
            continue
        for word in re.findall(r"\b\w{4,}\b", turn.get("content", "").lower()):
            if word not in _STOPWORDS:
                words[word] = words.get(word, 0) + 1
    # Return top N by frequency
    return sorted(words, key=lambda w: words[w], reverse=True)[:max_topics]
