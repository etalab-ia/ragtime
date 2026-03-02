"""Optional Albert-backed semantic search for agent memory.

Uploads ``.agent/*.md`` files to a private Albert collection and uses the
``/search`` endpoint for semantic retrieval.  Falls back gracefully when
the ``albert`` package isn't installed or credentials are missing.

**Incremental indexing**: tracks file modification times in
``.agent/.search-state.json`` so only changed files are re-uploaded.

This module is never imported directly by the memory package's core code.
The ``memory_search`` tool in ``tool.py`` conditionally imports it.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from rag_facile.memory._paths import AGENT_DIR
from rag_facile.memory.search import SearchResult

logger = logging.getLogger(__name__)

_STATE_FILE = ".search-state.json"
_COLLECTION_PREFIX = "rag-facile-memory"


class AlbertMemoryIndex:
    """Sync ``.agent/`` files to an Albert collection for semantic search.

    Parameters
    ----------
    api_key:
        Albert API key (``OPENAI_API_KEY`` or ``ALBERT_API_KEY``).
    api_base:
        Albert API base URL.
    """

    def __init__(self, api_key: str, api_base: str) -> None:
        self._api_key = api_key
        self._api_base = api_base
        self._collection_id: int | None = None
        self._synced = False

    # ── Public API ────────────────────────────────────────────────────────────

    def sync(self, workspace: Path) -> None:
        """Upload new or changed ``.md`` files to the Albert collection.

        Reads the state file to determine which files have changed since the
        last sync.  Creates the collection on first call.
        """
        try:
            from albert import AlbertClient
        except ImportError:
            logger.debug("albert package not installed — skipping semantic sync")
            return

        agent_dir = workspace / AGENT_DIR
        if not agent_dir.exists():
            return

        state = self._load_state(agent_dir)
        self._collection_id = state.get("collection_id")

        client = AlbertClient(api_key=self._api_key, base_url=self._api_base)

        # Create collection on first sync
        if self._collection_id is None:
            import time

            name = f"{_COLLECTION_PREFIX}-{time.time_ns()}"
            collection = client.create_collection(name, visibility="private")
            self._collection_id = collection.id
            logger.info("Created memory collection: %s (id=%d)", name, collection.id)

        # Find changed files
        stored_mtimes: dict[str, float] = state.get("files", {})
        current_files = self._discover_md_files(agent_dir)
        changed: list[tuple[str, Path]] = []

        for rel_path, abs_path in current_files:
            mtime = abs_path.stat().st_mtime_ns
            if stored_mtimes.get(rel_path) != mtime:
                changed.append((rel_path, abs_path))
                stored_mtimes[rel_path] = mtime

        if not changed:
            logger.debug("No memory files changed since last sync")
            self._synced = True
            return

        # Upload changed files
        for rel_path, abs_path in changed:
            try:
                # Albert requires supported file types. Markdown is supported.
                # Upload directly if .md; otherwise convert to temp .md file.
                client.upload_document(
                    abs_path,
                    self._collection_id,
                    chunk_size=512,
                    chunk_overlap=50,
                    preset_separators="markdown",
                )
                logger.info("Uploaded memory file: %s", rel_path)
            except Exception:  # noqa: BLE001 — sync must not crash the chat
                logger.warning("Failed to upload %s — skipping", rel_path)
                # Don't update mtime so we retry next time
                stored_mtimes.pop(rel_path, None)

        # Save state
        self._save_state(agent_dir, stored_mtimes)
        self._synced = True

    def search(
        self,
        query: str,
        workspace: Path,
        *,
        limit: int = 8,
    ) -> list[SearchResult]:
        """Semantic search across memory files via Albert API.

        Syncs lazily on first search if not already synced.

        Returns
        -------
        list[SearchResult]
            Results with file path inferred from chunk metadata.
        """
        if not self._synced:
            self.sync(workspace)

        if self._collection_id is None:
            return []

        try:
            from albert import AlbertClient
        except ImportError:
            return []

        client = AlbertClient(api_key=self._api_key, base_url=self._api_base)

        try:
            response = client.search(
                prompt=query,
                collections=[self._collection_id],
                limit=limit,
                method="semantic",
            )
        except Exception:  # noqa: BLE001 — search must not crash the chat
            logger.warning("Albert memory search failed — falling back to keyword only")
            return []

        results: list[SearchResult] = []
        for hit in response.data:
            chunk = hit.chunk
            # Try to infer file path from metadata
            file_path = "unknown"
            if chunk.metadata and isinstance(chunk.metadata, dict):
                file_path = chunk.metadata.get("source", "unknown")

            # Extract snippet from chunk content
            snippet_lines = chunk.content.strip().splitlines()
            snippet = "\n".join(snippet_lines[:5])

            results.append(
                SearchResult(
                    file=file_path,
                    line_start=1,  # Albert doesn't provide line numbers
                    line_end=len(snippet_lines),
                    snippet=snippet,
                    score=round(hit.score, 4),
                )
            )

        return results

    # ── State persistence ─────────────────────────────────────────────────────

    def _load_state(self, agent_dir: Path) -> dict:
        """Load the sync state from ``.agent/.search-state.json``."""
        state_file = agent_dir / _STATE_FILE
        if not state_file.exists():
            return {}
        try:
            return json.loads(state_file.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return {}

    def _save_state(self, agent_dir: Path, file_mtimes: dict[str, float]) -> None:
        """Save the sync state to ``.agent/.search-state.json``."""
        state = {
            "collection_id": self._collection_id,
            "files": file_mtimes,
        }
        state_file = agent_dir / _STATE_FILE
        state_file.write_text(json.dumps(state, indent=2), encoding="utf-8")

    # ── File discovery ────────────────────────────────────────────────────────

    @staticmethod
    def _discover_md_files(agent_dir: Path) -> list[tuple[str, Path]]:
        """Return ``(relative_path, absolute_path)`` for all ``.md`` files."""
        results: list[tuple[str, Path]] = []
        for md_file in sorted(agent_dir.rglob("*.md")):
            rel = str(md_file.relative_to(agent_dir))
            results.append((rel, md_file))
        return results


# ── RRF fusion ────────────────────────────────────────────────────────────────


def fuse_search_results(
    keyword_results: list[SearchResult],
    semantic_results: list[SearchResult],
    *,
    k: int = 60,
    limit: int = 8,
) -> list[SearchResult]:
    """Merge keyword and semantic results via Reciprocal Rank Fusion.

    Dedup key: ``(file, line_start)``.  The snippet from the first-seen
    result is kept.
    """
    rrf_scores: dict[tuple[str, int], float] = {}
    best: dict[tuple[str, int], SearchResult] = {}

    for result_list in (keyword_results, semantic_results):
        for rank, result in enumerate(result_list):
            key = (result["file"], result["line_start"])
            score = 1.0 / (k + rank + 1)
            rrf_scores[key] = rrf_scores.get(key, 0.0) + score
            if key not in best:
                best[key] = result

    fused: list[SearchResult] = []
    for key, rrf_score in sorted(rrf_scores.items(), key=lambda x: x[1], reverse=True):
        entry = best[key].copy()
        entry["score"] = round(rrf_score, 4)
        fused.append(entry)

    return fused[:limit]
