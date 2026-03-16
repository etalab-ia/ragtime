"""SQLite-backed tracing provider.

Uses Python's stdlib :mod:`sqlite3` — zero external dependencies.
The database file lives alongside the workspace (default:
``.rag-facile/traces.db``) and uses WAL mode for concurrent read
access in multi-user web deployments.

Config snapshots are normalised into a separate ``config_snapshots``
table keyed by SHA-256 hash, so identical configs (the common case)
are stored exactly once regardless of how many traces reference them.
"""

from __future__ import annotations

import hashlib
import json
import logging
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path

from ._base import TracingProvider
from ._models import TraceRecord

logger = logging.getLogger(__name__)

# ── Schema ────────────────────────────────────────────────────────────────────

_CREATE_CONFIG_TABLE = """\
CREATE TABLE IF NOT EXISTS config_snapshots (
    hash    TEXT PRIMARY KEY,
    config  TEXT NOT NULL
);
"""

_CREATE_TABLE = """\
CREATE TABLE IF NOT EXISTS traces (
    id                TEXT PRIMARY KEY,
    session_id        TEXT,
    user_id           TEXT,
    created_at        TEXT NOT NULL,
    response_at       TEXT,

    -- RAG pipeline data
    query             TEXT NOT NULL DEFAULT '',
    expanded_queries  TEXT NOT NULL DEFAULT '[]',
    retrieved_chunks  TEXT NOT NULL DEFAULT '[]',
    reranked_chunks   TEXT NOT NULL DEFAULT '[]',
    formatted_context TEXT NOT NULL DEFAULT '',
    collection_ids    TEXT NOT NULL DEFAULT '[]',

    -- LLM data
    response          TEXT,
    model             TEXT NOT NULL DEFAULT '',
    temperature       REAL NOT NULL DEFAULT 0.0,
    latency_ms        INTEGER,

    -- Config snapshot (FK → config_snapshots.hash)
    config_hash       TEXT NOT NULL DEFAULT '',

    -- User feedback
    feedback_score    INTEGER,
    feedback_tags     TEXT NOT NULL DEFAULT '[]',
    feedback_comment  TEXT
);
"""

_CREATE_INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_traces_session ON traces (session_id);",
    "CREATE INDEX IF NOT EXISTS idx_traces_user ON traces (user_id);",
    "CREATE INDEX IF NOT EXISTS idx_traces_created ON traces (created_at DESC);",
]

# JSON-serialised list/dict columns (on the traces table)
_JSON_FIELDS = frozenset(
    {
        "expanded_queries",
        "retrieved_chunks",
        "reranked_chunks",
        "collection_ids",
        "feedback_tags",
    }
)

# Datetime columns
_DATETIME_FIELDS = frozenset({"created_at", "response_at"})

# Valid column names for UPDATE — derived from TraceRecord fields.
# Prevents SQL injection via crafted keys in update_trace(**fields).
_VALID_COLUMNS = frozenset(
    {
        "session_id",
        "user_id",
        "created_at",
        "response_at",
        "query",
        "expanded_queries",
        "retrieved_chunks",
        "reranked_chunks",
        "formatted_context",
        "collection_ids",
        "response",
        "model",
        "temperature",
        "latency_ms",
        "feedback_score",
        "feedback_tags",
        "feedback_comment",
    }
)


# ── Helpers ───────────────────────────────────────────────────────────────────


def _dt_to_iso(dt: datetime | None) -> str | None:
    if dt is None:
        return None
    return dt.isoformat()


def _iso_to_dt(value: str | None) -> datetime | None:
    if value is None:
        return None
    return datetime.fromisoformat(value)


def _config_hash(config_dict: dict) -> str:
    """Compute a deterministic SHA-256 hash of a config dict."""
    canonical = json.dumps(config_dict, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode()).hexdigest()


def _row_to_trace(row: sqlite3.Row) -> TraceRecord:
    """Convert a sqlite3.Row to a TraceRecord, deserialising JSON columns.

    Expects the row to contain a ``config`` column (from a JOIN with
    ``config_snapshots``) rather than an inline ``config_snapshot``.
    """
    data = dict(row)

    # Reconstruct config_snapshot from the joined config column
    config_json = data.pop("config", None)
    data.pop("config_hash", None)  # internal column, not in TraceRecord
    data["config_snapshot"] = json.loads(config_json) if config_json else {}

    for key in _JSON_FIELDS:
        raw = data.get(key)
        if isinstance(raw, str):
            data[key] = json.loads(raw)
    for key in _DATETIME_FIELDS:
        data[key] = _iso_to_dt(data.get(key))
    return TraceRecord(**data)


# ── Provider ──────────────────────────────────────────────────────────────────


class SQLiteProvider(TracingProvider):
    """Store traces in a local SQLite database.

    Args:
        db_path: Path to the SQLite database file.  Parent directories
            are created automatically.
    """

    def __init__(self, db_path: str | Path) -> None:
        self._db_path = Path(db_path)
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    # ── Internal ──

    def _connect(self) -> sqlite3.Connection:
        """Open a new connection with WAL mode and row factory."""
        conn = sqlite3.connect(
            str(self._db_path),
            check_same_thread=False,
        )
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL;")
        return conn

    def _init_db(self) -> None:
        """Create the traces + config_snapshots tables and indexes.

        Also migrates databases created before the config normalisation
        refactor (``config_snapshot`` column → ``config_hash`` FK).
        """
        conn = self._connect()
        try:
            conn.execute(_CREATE_CONFIG_TABLE)
            conn.execute(_CREATE_TABLE)
            for idx_sql in _CREATE_INDEXES:
                conn.execute(idx_sql)

            # ── Migration: config_snapshot → config_hash ──
            columns = {
                row[1] for row in conn.execute("PRAGMA table_info(traces);").fetchall()
            }
            if "config_snapshot" in columns and "config_hash" not in columns:
                logger.info("Migrating traces table: config_snapshot → config_hash")
                # 1. Add new column
                conn.execute(
                    "ALTER TABLE traces ADD COLUMN config_hash TEXT NOT NULL DEFAULT '';"
                )
                # 2. Move existing snapshots into config_snapshots table
                rows = conn.execute("SELECT id, config_snapshot FROM traces").fetchall()
                for row in rows:
                    snapshot = row[1] or "{}"
                    c_hash = _config_hash(json.loads(snapshot))
                    conn.execute(
                        "INSERT OR IGNORE INTO config_snapshots (hash, config) "
                        "VALUES (?, ?)",
                        (c_hash, snapshot),
                    )
                    conn.execute(
                        "UPDATE traces SET config_hash = ? WHERE id = ?",
                        (c_hash, row[0]),
                    )
                # 3. Drop the old column (SQLite 3.35+)
                conn.execute("ALTER TABLE traces DROP COLUMN config_snapshot;")
                logger.info("Migration complete: %d traces migrated", len(rows))

            conn.commit()
        finally:
            conn.close()
        logger.debug("Tracing database initialised at %s", self._db_path)

    # ── TracingProvider interface ──

    def log_trace(self, trace: TraceRecord) -> str:
        """Insert a new trace into the database.

        The config snapshot is normalised: identical configs (keyed by
        SHA-256 hash) are stored once in ``config_snapshots`` and
        referenced from the trace row.  This is the common case — the
        config only changes when the user edits ``ragfacile.toml``.
        """
        c_hash = _config_hash(trace.config_snapshot)

        conn = self._connect()
        try:
            # Upsert config snapshot (INSERT OR IGNORE = skip if exists)
            conn.execute(
                "INSERT OR IGNORE INTO config_snapshots (hash, config) VALUES (?, ?)",
                (c_hash, json.dumps(trace.config_snapshot)),
            )

            conn.execute(
                """
                INSERT INTO traces (
                    id, session_id, user_id, created_at, response_at,
                    query, expanded_queries, retrieved_chunks, reranked_chunks,
                    formatted_context, collection_ids,
                    response, model, temperature, latency_ms,
                    config_hash,
                    feedback_score, feedback_tags, feedback_comment
                ) VALUES (
                    ?, ?, ?, ?, ?,
                    ?, ?, ?, ?,
                    ?, ?,
                    ?, ?, ?, ?,
                    ?,
                    ?, ?, ?
                )
                """,
                (
                    trace.id,
                    trace.session_id,
                    trace.user_id,
                    _dt_to_iso(trace.created_at),
                    _dt_to_iso(trace.response_at),
                    trace.query,
                    json.dumps(trace.expanded_queries),
                    json.dumps(trace.retrieved_chunks),
                    json.dumps(trace.reranked_chunks),
                    trace.formatted_context,
                    json.dumps(trace.collection_ids),
                    trace.response,
                    trace.model,
                    trace.temperature,
                    trace.latency_ms,
                    c_hash,
                    trace.feedback_score,
                    json.dumps(trace.feedback_tags),
                    trace.feedback_comment,
                ),
            )
            conn.commit()
        finally:
            conn.close()

        logger.debug("Logged trace %s for query: %s", trace.id, trace.query[:80])
        return trace.id

    def update_trace(self, trace_id: str, **fields: object) -> None:
        """Update specific fields on an existing trace."""
        if not fields:
            return

        # Validate column names to prevent SQL injection
        invalid = fields.keys() - _VALID_COLUMNS
        if invalid:
            msg = f"Invalid field names for trace update: {invalid!r}"
            raise ValueError(msg)

        # Serialise JSON and datetime fields
        processed: dict[str, object] = {}
        for key, value in fields.items():
            if key in _JSON_FIELDS:
                processed[key] = json.dumps(value)
            elif key in _DATETIME_FIELDS and isinstance(value, datetime):
                processed[key] = _dt_to_iso(value)
            else:
                processed[key] = value

        set_clause = ", ".join(f"{k} = ?" for k in processed)
        values = [*processed.values(), trace_id]

        conn = self._connect()
        try:
            conn.execute(
                f"UPDATE traces SET {set_clause} WHERE id = ?",  # noqa: S608
                values,
            )
            conn.commit()
        finally:
            conn.close()

    def get_trace(self, trace_id: str) -> TraceRecord | None:
        """Retrieve a single trace by ID (with config snapshot joined)."""
        conn = self._connect()
        try:
            cursor = conn.execute(
                """
                SELECT t.*, c.config
                FROM traces t
                LEFT JOIN config_snapshots c ON t.config_hash = c.hash
                WHERE t.id = ?
                """,
                (trace_id,),
            )
            row = cursor.fetchone()
        finally:
            conn.close()

        if row is None:
            return None
        return _row_to_trace(row)

    def list_traces(
        self,
        *,
        session_id: str | None = None,
        user_id: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[TraceRecord]:
        """List traces with optional filtering, newest first."""
        conditions: list[str] = []
        params: list[object] = []

        if session_id is not None:
            conditions.append("t.session_id = ?")
            params.append(session_id)
        if user_id is not None:
            conditions.append("t.user_id = ?")
            params.append(user_id)

        where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        sql = (  # noqa: S608
            f"SELECT t.*, c.config FROM traces t "
            f"LEFT JOIN config_snapshots c ON t.config_hash = c.hash "
            f"{where} ORDER BY t.created_at DESC LIMIT ? OFFSET ?"
        )
        params.extend([limit, offset])

        conn = self._connect()
        try:
            cursor = conn.execute(sql, params)
            rows = cursor.fetchall()
        finally:
            conn.close()

        return [_row_to_trace(row) for row in rows]

    def add_feedback(
        self,
        trace_id: str,
        score: int | None = None,
        tags: list[str] | None = None,
        comment: str | None = None,
    ) -> None:
        """Add or update user feedback on a trace."""
        updates: dict[str, object] = {}
        if score is not None:
            updates["feedback_score"] = score
        if tags is not None:
            updates["feedback_tags"] = tags
        if comment is not None:
            updates["feedback_comment"] = comment

        if updates:
            self.update_trace(trace_id, **updates)

    def delete_traces(self, *, older_than_days: int) -> int:
        """Delete traces older than N days. Returns count deleted."""
        cutoff = datetime.now(timezone.utc) - timedelta(days=older_than_days)
        conn = self._connect()
        try:
            cursor = conn.execute(
                "DELETE FROM traces WHERE created_at < ?",
                (_dt_to_iso(cutoff),),
            )
            conn.commit()
        finally:
            conn.close()
        return cursor.rowcount
