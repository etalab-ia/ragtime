"""Standard file-operation tools for agent memory (Read / Write / Edit / Search).

Four ``@tool``-decorated functions scoped to the ``.agent/`` directory:

- ``memory_read``   — list a directory or read a file (with optional line range)
- ``memory_write``  — create or overwrite a file
- ``memory_edit``   — find-and-replace in a file
- ``memory_search`` — keyword search across all memory files

All paths are validated to stay within ``.agent/`` (path traversal protection).
"""

from __future__ import annotations

from pathlib import Path

from smolagents import tool

from rag_facile.memory._paths import AGENT_DIR

# ── Module-level workspace reference ──────────────────────────────────────────
# Set once at session start by the agent harness.

_workspace_root: Path | None = None


def set_workspace_root(root: Path | None) -> None:
    """Register the workspace root so memory tools can locate ``.agent/``."""
    global _workspace_root  # noqa: PLW0603
    _workspace_root = root


# ── Path safety ───────────────────────────────────────────────────────────────


def _agent_dir() -> Path | None:
    """Return the resolved ``.agent/`` path, or ``None`` if no workspace."""
    if _workspace_root is None:
        return None
    return (_workspace_root / AGENT_DIR).resolve()


def _safe_resolve(path_str: str, agent_dir: Path) -> Path:
    """Resolve *path_str* inside *agent_dir*, raising on traversal escape.

    Raises
    ------
    ValueError
        If the resolved path is outside *agent_dir*.
    """
    resolved = (agent_dir / path_str).resolve()
    # relative_to raises ValueError if *resolved* is not under *agent_dir*
    resolved.relative_to(agent_dir)
    return resolved


# ── Auto-bootstrap ────────────────────────────────────────────────────────────


def _ensure_memory_file(workspace_root: Path) -> None:
    """Create ``MEMORY.md`` from the template if it doesn't exist yet."""
    memory_path = workspace_root / AGENT_DIR / "MEMORY.md"
    if memory_path.exists():
        return
    from rag_facile.memory.stores import SemanticStore

    SemanticStore.create(workspace_root)


# ── Directory listing ─────────────────────────────────────────────────────────


def _list_directory(directory: Path, agent_dir: Path) -> str:
    """Return a tree listing of *directory* (2 levels deep) with sizes."""
    items: list[str] = []
    rel_root = directory.relative_to(agent_dir)
    prefix = str(rel_root) if str(rel_root) != "." else "."

    for child in sorted(directory.iterdir()):
        if child.name.startswith("."):
            continue  # skip hidden files
        rel = child.relative_to(agent_dir)
        if child.is_dir():
            items.append(f"  {prefix}/{child.name}/")
            # One level deeper
            try:
                for grandchild in sorted(child.iterdir()):
                    if grandchild.name.startswith("."):
                        continue
                    items.append(f"    {prefix}/{child.name}/{grandchild.name}")
            except PermissionError:
                pass
        else:
            size = child.stat().st_size
            size_str = _format_size(size)
            items.append(f"  {size_str}\t{rel}")

    if not items:
        return f"Directory '{prefix}' is empty."
    header = (
        f"Files in .agent/{rel_root}:" if str(rel_root) != "." else "Files in .agent/:"
    )
    return header + "\n" + "\n".join(items)


def _format_size(size: int) -> str:
    """Format byte size as human-readable (e.g. 1.5K, 3.2M)."""
    if size < 1024:
        return f"{size}B"
    if size < 1024 * 1024:
        return f"{size / 1024:.1f}K"
    return f"{size / (1024 * 1024):.1f}M"


# ── File reading ──────────────────────────────────────────────────────────────


def _read_file(
    file_path: Path, start: int | None = None, end: int | None = None
) -> str:
    """Read a file with line numbers; optionally restrict to *start*–*end*."""
    content = file_path.read_text(encoding="utf-8")
    lines = content.splitlines()

    if start is not None and end is not None:
        # Clamp to valid range (1-indexed)
        start = max(1, start)
        end = min(len(lines), end)
        if start > len(lines):
            return f"Line {start} is beyond end of file ({len(lines)} lines)."
        selected = lines[start - 1 : end]
        numbered = [f"{i:>6}\t{line}" for i, line in enumerate(selected, start=start)]
        return "\n".join(numbered)

    numbered = [f"{i:>6}\t{line}" for i, line in enumerate(lines, start=1)]
    return "\n".join(numbered)


def _parse_line_range(path_str: str) -> tuple[str, int | None, int | None]:
    """Parse ``"file.md:5-15"`` into ``("file.md", 5, 15)``.

    Returns ``(path, None, None)`` if no range is specified.
    """
    if ":" in path_str:
        parts = path_str.rsplit(":", 1)
        range_part = parts[1]
        if "-" in range_part:
            try:
                start_s, end_s = range_part.split("-", 1)
                return parts[0], int(start_s), int(end_s)
            except ValueError:
                pass
    return path_str, None, None


# ── Tools ─────────────────────────────────────────────────────────────────────


@tool
def memory_read(path: str) -> str:
    """Read from the agent's persistent memory directory (.agent/).

    Lists directory contents or reads a file with line numbers.
    Always call memory_read(".") at the start of a session to check for
    existing context from previous conversations.

    Supports optional line ranges: "MEMORY.md:5-15" reads lines 5 to 15.

    Args:
        path: Path relative to .agent/, e.g. "." (root), "MEMORY.md",
              "logs/2026-03-01.md", or "MEMORY.md:5-15" for a line range.
    """
    agent = _agent_dir()
    if agent is None:
        return "No workspace detected — memory unavailable."

    # Parse optional line range
    path_str, start, end = _parse_line_range(path)

    try:
        resolved = _safe_resolve(path_str, agent)
    except ValueError:
        return f"Access denied: path '{path}' is outside the memory directory."

    if not resolved.exists():
        # Auto-bootstrap: if reading root or MEMORY.md, try to create it
        if path_str in (".", "", "MEMORY.md"):
            assert _workspace_root is not None  # guaranteed by _agent_dir() check
            _ensure_memory_file(_workspace_root)
            if not resolved.exists():
                return f"File not found: {path_str}"
        else:
            return f"File not found: {path_str}"

    if resolved.is_dir():
        return _list_directory(resolved, agent)

    return _read_file(resolved, start, end)


@tool
def memory_write(path: str, content: str) -> str:
    """Create or overwrite a file in the agent's memory directory (.agent/).

    Use this to save important facts, update notes, or create new files.
    Parent directories are created automatically.

    Args:
        path: File path relative to .agent/, e.g. "MEMORY.md", "notes/project.md".
        content: The full content to write to the file.
    """
    agent = _agent_dir()
    if agent is None:
        return "No workspace detected — memory unavailable."

    try:
        resolved = _safe_resolve(path, agent)
    except ValueError:
        return f"Access denied: path '{path}' is outside the memory directory."

    # Create parent directories
    resolved.parent.mkdir(parents=True, exist_ok=True)

    resolved.write_text(content, encoding="utf-8")
    return f"Written to .agent/{path} ({len(content)} chars)."


@tool
def memory_edit(path: str, old_str: str, new_str: str) -> str:
    """Find and replace text in a memory file.

    Use this to update specific facts without rewriting the entire file.
    The old_str must match exactly one location in the file.

    Args:
        path: File path relative to .agent/, e.g. "MEMORY.md".
        old_str: Exact text to find (must be unique in the file).
        new_str: Replacement text.
    """
    agent = _agent_dir()
    if agent is None:
        return "No workspace detected — memory unavailable."

    try:
        resolved = _safe_resolve(path, agent)
    except ValueError:
        return f"Access denied: path '{path}' is outside the memory directory."

    if not resolved.exists():
        return f"File not found: {path}"
    if resolved.is_dir():
        return f"Cannot edit a directory: {path}"

    content = resolved.read_text(encoding="utf-8")

    count = content.count(old_str)
    if count == 0:
        return f"Text not found in {path}. Make sure old_str matches exactly."
    if count > 1:
        return f"Found {count} matches in {path}. old_str must be unique — add more context."

    new_content = content.replace(old_str, new_str, 1)
    resolved.write_text(new_content, encoding="utf-8")
    return f"Edited .agent/{path}: replaced 1 occurrence."


@tool
def memory_search(query: str) -> str:
    """Search across all memory files for relevant information.

    Uses keyword matching to find snippets in MEMORY.md, daily logs, and
    session archives.  Results include file paths with line ranges — use
    memory_read(path:start-end) to read more context.

    Use this BEFORE memory_read when you need to find information but don't
    know which file contains it.

    Args:
        query: Natural language search query, e.g. "deployment config",
               "Albert API rate limit", "user preferences".
    """
    if _workspace_root is None:
        return "No workspace detected — memory unavailable."

    from rag_facile.memory.search import keyword_search

    results = keyword_search(_workspace_root, query, max_results=8)

    if not results:
        return f'No results found for "{query}".'

    lines: list[str] = [f'Found {len(results)} result(s) for "{query}":\n']
    for i, r in enumerate(results, 1):
        path_ref = f"{r['file']}:{r['line_start']}-{r['line_end']}"
        lines.append(f"{i}. [{r['score']:.2f}] {path_ref}")
        # Indent snippet lines with >
        for snippet_line in r["snippet"].splitlines()[:4]:
            lines.append(f"   > {snippet_line}")
        lines.append("")

    lines.append(
        'Use memory_read("file:start-end") to read more context from any result.'
    )
    return "\n".join(lines)
