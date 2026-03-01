"""Incremental indexer — scans memory files and updates the search index.

Only re-indexes files that have changed since the last scan (tracked via
``file_state`` table in SQLite).  Embedding generation is optional — if
no ``embed_fn`` is provided, only FTS5 keyword search is available.
"""

from __future__ import annotations

import hashlib
import logging
from datetime import date
from pathlib import Path

from rag_facile.memory._paths import AGENT_DIR
from rag_facile.memory.index import MemoryChunk, MemoryIndex

logger = logging.getLogger(__name__)


def rebuild_index(
    workspace: Path,
    index: MemoryIndex,
    *,
    embed_fn: object | None = None,
) -> int:
    """Scan all memory markdown files and update the index incrementally.

    Parameters
    ----------
    embed_fn:
        Optional callable ``(texts: list[str]) -> list[list[float]]`` that
        generates embeddings for a batch of text chunks.  Typically wraps
        the Albert API ``openweight-embeddings`` model.

    Returns
    -------
    int
        Number of files re-indexed.
    """
    agent_dir = workspace / AGENT_DIR
    if not agent_dir.exists():
        return 0

    # Collect all .md files under .rag-facile/agent/
    md_files = list(agent_dir.rglob("*.md"))
    # Exclude files inside the .index/ directory
    md_files = [f for f in md_files if ".index" not in f.parts]

    updated_count = 0
    today = date.today().isoformat()

    for md_path in md_files:
        relative = str(md_path.relative_to(workspace / AGENT_DIR))
        content = md_path.read_text(encoding="utf-8")
        content_hash = hashlib.sha256(content.encode()).hexdigest()[:16]
        mtime = md_path.stat().st_mtime

        # Check if file has changed
        state = index.get_file_state(relative)
        if state is not None:
            old_mtime, old_hash = state
            if old_hash == content_hash:
                continue  # unchanged

        # Re-index this file
        chunks = chunk_markdown(content, source_file=relative)
        if chunks:
            index.remove_file(relative)
            index.upsert_chunks(chunks, updated_at=today)

            # Generate embeddings if available
            if embed_fn is not None and chunks:
                _embed_chunks(index, chunks, embed_fn)

        index.update_file_state(relative, mtime, content_hash)
        updated_count += 1
        logger.info("Re-indexed %s (%d chunks)", relative, len(chunks))

    return updated_count


def chunk_markdown(content: str, *, source_file: str) -> list[MemoryChunk]:
    """Split markdown content at ``##`` headers into chunks.

    Each chunk contains the header + body text until the next ``##`` header
    or end of file.  Chunks shorter than 10 characters are skipped.
    """
    lines = content.splitlines()
    chunks: list[MemoryChunk] = []
    current_section = ""
    current_lines: list[str] = []
    section_start = 0

    for i, line in enumerate(lines):
        if line.startswith("## "):
            # Flush previous section
            if current_lines:
                text = "\n".join(current_lines).strip()
                if len(text) >= 10:
                    chunks.append(
                        MemoryChunk(
                            content=text,
                            source_file=source_file,
                            section=current_section,
                            line_start=section_start + 1,  # 1-indexed
                            line_end=i,
                        )
                    )
            current_section = line.lstrip("# ").strip()
            current_lines = [line]
            section_start = i
        else:
            current_lines.append(line)

    # Flush last section
    if current_lines:
        text = "\n".join(current_lines).strip()
        if len(text) >= 10:
            chunks.append(
                MemoryChunk(
                    content=text,
                    source_file=source_file,
                    section=current_section,
                    line_start=section_start + 1,
                    line_end=len(lines),
                )
            )

    return chunks


def _embed_chunks(
    index: MemoryIndex,
    chunks: list[MemoryChunk],
    embed_fn: object,
) -> None:
    """Generate and store embeddings for chunks (best-effort)."""
    texts = [c.content for c in chunks]
    try:
        embeddings = embed_fn(texts)
        for chunk, embedding in zip(chunks, embeddings):
            index.store_embedding(chunk.hash, embedding)
    except (OSError, ValueError) as exc:
        logger.warning("Embedding generation failed — keyword search only: %s", exc)
