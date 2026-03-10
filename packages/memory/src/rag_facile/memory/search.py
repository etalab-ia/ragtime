"""Local keyword search across the ``.agent/`` memory directory.

Zero external dependencies — uses only stdlib (``re``, ``pathlib``,
``datetime``).  The search is designed for the "Search then Get" pattern:
results include file paths with line ranges so the agent can drill in
with ``memory_read(path:start-end)``.

Scoring
-------
1. Tokenize the query into significant words (≥3 chars, no stopwords).
2. Walk all ``.md`` files under ``.agent/``.
3. For each line, count how many query words appear (word-boundary match).
4. Bonuses: ``## `` header lines ×2, ``MEMORY.md`` ×1.5.
5. Group consecutive matching lines into snippets (max 5 lines).
6. Recency boost: newer files score higher.
7. Sort by score, return top *max_results*.
"""

from __future__ import annotations

import re
from datetime import date, datetime
from pathlib import Path
from typing import TypedDict

from rag_facile.memory._paths import AGENT_DIR

# ── Result type ───────────────────────────────────────────────────────────────


class SearchResult(TypedDict):
    """A single search hit with file location and snippet."""

    file: str  # relative to .agent/, e.g. "sessions/2026-03-01-setup.md"
    line_start: int  # 1-indexed
    line_end: int  # 1-indexed, inclusive
    snippet: str  # the matching lines with a small context window
    score: float


# ── Stopwords ─────────────────────────────────────────────────────────────────

_STOPWORDS = frozenset(
    "le la les un une des de du au aux et ou en à par pour dans sur "
    "avec est ce cette que qui ne pas se son sa ses leur mon ma mes "
    "the a an and or in on at to for with is are was were of from by not".split()
)


# ── Public API ────────────────────────────────────────────────────────────────


def keyword_search(
    workspace: Path,
    query: str,
    *,
    max_results: int = 10,
    context_lines: int = 2,
) -> list[SearchResult]:
    """Search all ``.md`` files under ``.agent/`` for *query* terms.

    Parameters
    ----------
    workspace:
        Root directory containing ``.agent/``.
    query:
        Free-text search query.
    max_results:
        Maximum number of snippets to return.
    context_lines:
        Number of lines of context above/below each matching line.

    Returns
    -------
    list[SearchResult]
        Snippets sorted by descending score.
    """
    agent_dir = workspace / AGENT_DIR
    if not agent_dir.exists():
        return []

    words = _tokenize(query)
    if not words:
        return []

    # Build regex patterns for each query word (word-boundary match)
    patterns = [re.compile(rf"\b{re.escape(w)}\b", re.IGNORECASE) for w in words]

    results: list[SearchResult] = []

    for md_file in _iter_md_files(agent_dir):
        rel_path = str(md_file.relative_to(agent_dir))
        lines = md_file.read_text(encoding="utf-8").splitlines()

        # Score each line
        line_scores: list[tuple[int, float]] = []  # (0-indexed line num, score)
        for i, line in enumerate(lines):
            score = _score_line(line, patterns)
            if score > 0:
                # Header bonus
                if line.strip().startswith("## "):
                    score *= 2.0
                # MEMORY.md priority
                if rel_path == "MEMORY.md":
                    score *= 1.5
                line_scores.append((i, score))

        if not line_scores:
            continue

        # Recency boost
        recency = _recency_multiplier(md_file)

        # Group into snippets
        snippets = _group_into_snippets(line_scores, lines, context_lines=context_lines)

        for snippet_start, snippet_end, snippet_score, snippet_text in snippets:
            results.append(
                SearchResult(
                    file=rel_path,
                    line_start=snippet_start + 1,  # 1-indexed
                    line_end=snippet_end + 1,
                    snippet=snippet_text,
                    score=round(snippet_score * recency, 4),
                )
            )

    # Sort by score descending, then by file name for stability
    results.sort(key=lambda r: (-r["score"], r["file"]))
    return results[:max_results]


# ── Internals ─────────────────────────────────────────────────────────────────


def _tokenize(query: str) -> list[str]:
    """Extract significant words from *query* (≥3 chars, no stopwords)."""
    return [w for w in re.findall(r"\b\w{3,}\b", query.lower()) if w not in _STOPWORDS]


def _iter_md_files(agent_dir: Path) -> list[Path]:
    """Return all ``.md`` files under *agent_dir*, recursively."""
    return sorted(agent_dir.rglob("*.md"))


def _score_line(line: str, patterns: list[re.Pattern[str]]) -> float:
    """Return the number of distinct query words found in *line*."""
    return sum(1.0 for p in patterns if p.search(line))


def _recency_multiplier(file_path: Path) -> float:
    """Return a multiplier ≥1.0 that boosts recent files.

    Extracts date from filename (``YYYY-MM-DD*.md``) or falls back to
    file modification time.  Files from today get 1.3×, yesterday 1.2×,
    older files 1.0×.
    """
    # Try to extract date from filename (e.g. "2026-03-01.md" or "2026-03-01-1430-topic.md")
    match = re.match(r"(\d{4}-\d{2}-\d{2})", file_path.name)
    if match:
        try:
            file_date = date.fromisoformat(match.group(1))
        except ValueError:
            file_date = None
    else:
        file_date = None

    if file_date is None:
        # Fall back to mtime
        try:
            mtime = file_path.stat().st_mtime
            file_date = datetime.fromtimestamp(mtime).date()  # noqa: DTZ006
        except OSError:
            return 1.0

    today = date.today()
    days_ago = (today - file_date).days

    if days_ago <= 0:
        return 1.3
    if days_ago <= 1:
        return 1.2
    if days_ago <= 7:
        return 1.1
    return 1.0


def _group_into_snippets(
    line_scores: list[tuple[int, float]],
    all_lines: list[str],
    *,
    context_lines: int = 2,
    max_snippet_lines: int = 7,
) -> list[tuple[int, int, float, str]]:
    """Group scored lines into contiguous snippets.

    Returns
    -------
    list of (start_idx, end_idx, total_score, text)
        Indices are 0-based.
    """
    if not line_scores:
        return []

    # Sort by line number
    line_scores.sort(key=lambda x: x[0])
    total_lines = len(all_lines)

    snippets: list[tuple[int, int, float, str]] = []
    current_start = max(0, line_scores[0][0] - context_lines)
    current_end = min(total_lines - 1, line_scores[0][0] + context_lines)
    current_score = line_scores[0][1]

    for line_idx, score in line_scores[1:]:
        expanded_start = max(0, line_idx - context_lines)
        expanded_end = min(total_lines - 1, line_idx + context_lines)

        # If this line's context overlaps with current snippet, merge
        if expanded_start <= current_end + 1:
            current_end = max(current_end, expanded_end)
            current_score += score
        else:
            # Emit current snippet
            _emit_snippet(
                snippets,
                current_start,
                current_end,
                current_score,
                all_lines,
                max_snippet_lines,
            )
            current_start = expanded_start
            current_end = expanded_end
            current_score = score

    # Emit last snippet
    _emit_snippet(
        snippets,
        current_start,
        current_end,
        current_score,
        all_lines,
        max_snippet_lines,
    )

    return snippets


def _emit_snippet(
    snippets: list[tuple[int, int, float, str]],
    start: int,
    end: int,
    score: float,
    all_lines: list[str],
    max_lines: int,
) -> None:
    """Build and append a snippet to *snippets*."""
    # Cap snippet length
    if end - start + 1 > max_lines:
        end = start + max_lines - 1
    text = "\n".join(all_lines[start : end + 1])
    snippets.append((start, end, score, text))
