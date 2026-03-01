"""SQLite FTS5 index for memory search.

Stores chunked markdown content in an FTS5 virtual table for keyword/BM25
search, plus a separate table for optional embedding vectors (cosine
similarity search via Albert API).

The database lives at ``.rag-facile/agent/.index/memory.db`` and uses WAL
mode for safe concurrent reads.
"""

from __future__ import annotations

import hashlib
import math
import sqlite3
import struct
from dataclasses import dataclass
from pathlib import Path

from rag_facile.memory._paths import INDEX_DB, ensure_dirs

# ── Schema ────────────────────────────────────────────────────────────────────

_CREATE_FTS = """\
CREATE VIRTUAL TABLE IF NOT EXISTS memory_fts USING fts5(
    content,
    source_file,
    section,
    tokenize='unicode61'
);
"""

_CREATE_META = """\
CREATE TABLE IF NOT EXISTS chunk_meta (
    rowid       INTEGER PRIMARY KEY,
    line_start  INTEGER NOT NULL,
    line_end    INTEGER NOT NULL,
    chunk_hash  TEXT NOT NULL,
    updated_at  TEXT NOT NULL
);
"""

_CREATE_FILE_STATE = """\
CREATE TABLE IF NOT EXISTS file_state (
    path         TEXT PRIMARY KEY,
    mtime        REAL NOT NULL,
    content_hash TEXT NOT NULL
);
"""

_CREATE_EMBEDDINGS = """\
CREATE TABLE IF NOT EXISTS memory_embeddings (
    chunk_hash  TEXT PRIMARY KEY,
    embedding   BLOB NOT NULL,
    model       TEXT NOT NULL DEFAULT 'openweight-embeddings'
);
"""


# ── Data classes ──────────────────────────────────────────────────────────────


@dataclass
class MemoryChunk:
    """A chunk of markdown text ready for indexing."""

    content: str
    source_file: str  # relative path, e.g. "memory.md"
    section: str  # ## header text
    line_start: int
    line_end: int

    @property
    def hash(self) -> str:
        return hashlib.sha256(
            f"{self.source_file}:{self.line_start}:{self.content}".encode()
        ).hexdigest()[:16]


@dataclass
class SearchResult:
    """A single search result with metadata."""

    content: str
    source_file: str
    section: str
    line_start: int
    line_end: int
    score: float
    match_type: str  # "keyword", "semantic", or "both"


# ── Index ─────────────────────────────────────────────────────────────────────


class MemoryIndex:
    """SQLite-backed FTS5 + embedding index for memory search."""

    def __init__(self, workspace: Path) -> None:
        ensure_dirs(workspace)
        self._db_path = workspace / INDEX_DB
        self._conn = sqlite3.connect(str(self._db_path))
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA foreign_keys=ON")
        self._init_schema()

    def _init_schema(self) -> None:
        with self._conn:
            self._conn.executescript(
                _CREATE_FTS + _CREATE_META + _CREATE_FILE_STATE + _CREATE_EMBEDDINGS
            )

    def close(self) -> None:
        self._conn.close()

    # ── Write ─────────────────────────────────────────────────────────────

    def upsert_chunks(self, chunks: list[MemoryChunk], updated_at: str) -> None:
        """Insert or replace chunks in the FTS index."""
        with self._conn:
            for chunk in chunks:
                # Delete existing entry with same hash (if any)
                existing = self._conn.execute(
                    "SELECT rowid FROM chunk_meta WHERE chunk_hash = ?",
                    (chunk.hash,),
                ).fetchone()
                if existing:
                    rowid = existing[0]
                    self._conn.execute(
                        "DELETE FROM memory_fts WHERE rowid = ?", (rowid,)
                    )
                    self._conn.execute(
                        "DELETE FROM chunk_meta WHERE rowid = ?", (rowid,)
                    )

                # Insert into FTS
                self._conn.execute(
                    "INSERT INTO memory_fts(content, source_file, section) VALUES (?, ?, ?)",
                    (chunk.content, chunk.source_file, chunk.section),
                )
                rowid = self._conn.execute("SELECT last_insert_rowid()").fetchone()[0]

                # Insert metadata
                self._conn.execute(
                    "INSERT INTO chunk_meta(rowid, line_start, line_end, chunk_hash, updated_at) "
                    "VALUES (?, ?, ?, ?, ?)",
                    (rowid, chunk.line_start, chunk.line_end, chunk.hash, updated_at),
                )

    def remove_file(self, source_file: str) -> None:
        """Remove all chunks from a specific source file."""
        with self._conn:
            rows = self._conn.execute(
                "SELECT rowid FROM memory_fts WHERE source_file = ?",
                (source_file,),
            ).fetchall()
            for (rowid,) in rows:
                self._conn.execute("DELETE FROM memory_fts WHERE rowid = ?", (rowid,))
                self._conn.execute("DELETE FROM chunk_meta WHERE rowid = ?", (rowid,))
            self._conn.execute("DELETE FROM file_state WHERE path = ?", (source_file,))

    def update_file_state(self, path: str, mtime: float, content_hash: str) -> None:
        """Record a file's modification state for incremental indexing."""
        with self._conn:
            self._conn.execute(
                "INSERT OR REPLACE INTO file_state(path, mtime, content_hash) VALUES (?, ?, ?)",
                (path, mtime, content_hash),
            )

    def get_file_state(self, path: str) -> tuple[float, str] | None:
        """Return (mtime, content_hash) for a tracked file, or None."""
        row = self._conn.execute(
            "SELECT mtime, content_hash FROM file_state WHERE path = ?",
            (path,),
        ).fetchone()
        return (row[0], row[1]) if row else None

    # ── Embeddings ────────────────────────────────────────────────────────

    def store_embedding(
        self,
        chunk_hash: str,
        embedding: list[float],
        model: str = "openweight-embeddings",
    ) -> None:
        """Store an embedding vector for a chunk."""
        blob = struct.pack(f"{len(embedding)}f", *embedding)
        with self._conn:
            self._conn.execute(
                "INSERT OR REPLACE INTO memory_embeddings(chunk_hash, embedding, model) "
                "VALUES (?, ?, ?)",
                (chunk_hash, blob, model),
            )

    def get_all_embeddings(self) -> list[tuple[str, list[float]]]:
        """Return all (chunk_hash, embedding) pairs."""
        rows = self._conn.execute(
            "SELECT chunk_hash, embedding FROM memory_embeddings"
        ).fetchall()
        result = []
        for chunk_hash, blob in rows:
            n = len(blob) // 4  # float32 = 4 bytes
            embedding = list(struct.unpack(f"{n}f", blob))
            result.append((chunk_hash, embedding))
        return result

    def get_chunk_by_hash(self, chunk_hash: str) -> SearchResult | None:
        """Retrieve a chunk by its hash."""
        row = self._conn.execute(
            "SELECT f.content, f.source_file, f.section, m.line_start, m.line_end "
            "FROM memory_fts f "
            "JOIN chunk_meta m ON f.rowid = m.rowid "
            "WHERE m.chunk_hash = ?",
            (chunk_hash,),
        ).fetchone()
        if not row:
            return None
        return SearchResult(
            content=row[0],
            source_file=row[1],
            section=row[2],
            line_start=row[3],
            line_end=row[4],
            score=0.0,
            match_type="",
        )

    # ── Search ────────────────────────────────────────────────────────────

    def search_keyword(self, query: str, *, limit: int = 10) -> list[SearchResult]:
        """Run an FTS5 keyword search and return ranked results."""
        # FTS5 MATCH syntax — escape special chars for safety
        safe_query = query.replace('"', '""')
        try:
            rows = self._conn.execute(
                "SELECT f.content, f.source_file, f.section, m.line_start, m.line_end, "
                "       rank "
                "FROM memory_fts f "
                "JOIN chunk_meta m ON f.rowid = m.rowid "
                "WHERE memory_fts MATCH ? "
                "ORDER BY rank "
                "LIMIT ?",
                (f'"{safe_query}"', limit),
            ).fetchall()
        except sqlite3.OperationalError:
            # Malformed query — fall back to simple search
            return []

        return [
            SearchResult(
                content=row[0],
                source_file=row[1],
                section=row[2],
                line_start=row[3],
                line_end=row[4],
                score=-row[5],  # FTS5 rank is negative (lower = better)
                match_type="keyword",
            )
            for row in rows
        ]

    def search_semantic(
        self, query_embedding: list[float], *, limit: int = 10
    ) -> list[SearchResult]:
        """Search by cosine similarity against stored embeddings."""
        all_embeddings = self.get_all_embeddings()
        if not all_embeddings:
            return []

        scored: list[tuple[float, str]] = []
        for chunk_hash, embedding in all_embeddings:
            score = _cosine_similarity(query_embedding, embedding)
            scored.append((score, chunk_hash))

        scored.sort(reverse=True)
        results: list[SearchResult] = []
        for score, chunk_hash in scored[:limit]:
            chunk = self.get_chunk_by_hash(chunk_hash)
            if chunk:
                chunk.score = score
                chunk.match_type = "semantic"
                results.append(chunk)
        return results

    def chunk_count(self) -> int:
        """Return the total number of indexed chunks."""
        row = self._conn.execute("SELECT COUNT(*) FROM chunk_meta").fetchone()
        return row[0] if row else 0


# ── Math helpers ──────────────────────────────────────────────────────────────


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    """Compute cosine similarity between two vectors (no numpy)."""
    if len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return dot / (norm_a * norm_b)
