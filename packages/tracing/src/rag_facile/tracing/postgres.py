"""PostgreSQL-backed tracing provider.

Uses :mod:`psycopg` (v3) for synchronous access to a PostgreSQL database
(tested with Supabase's self-hosted stack).

Expects the schema from ``supabase/migrations/00000000000000_tracing.sql``
to already exist — this provider does NOT auto-create tables
(use ``supabase db push`` or run the migration manually).

Config snapshots are normalised into a separate ``config_snapshots``
table keyed by SHA-256 hash — identical to the SQLite provider pattern.
"""

from __future__ import annotations

import hashlib
import json
import logging
from datetime import datetime, timedelta, timezone

from ._base import TracingProvider
from ._models import TraceRecord

logger = logging.getLogger(__name__)

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

# Valid column names for UPDATE — prevents SQL injection via crafted keys.
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


def _config_hash(config_dict: dict) -> str:
    """Compute a deterministic SHA-256 hash of a config dict."""
    canonical = json.dumps(config_dict, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode()).hexdigest()


def _row_to_trace(row: dict) -> TraceRecord:
    """Convert a dict row from Postgres to a TraceRecord.

    Expects the row to contain a ``config`` column (from a JOIN with
    ``config_snapshots``) rather than an inline ``config_snapshot``.
    """
    data = dict(row)

    # Reconstruct config_snapshot from the joined config column
    config_json = data.pop("config", None)
    data.pop("config_hash", None)  # internal column, not in TraceRecord
    if isinstance(config_json, str):
        data["config_snapshot"] = json.loads(config_json)
    elif isinstance(config_json, dict):
        data["config_snapshot"] = config_json
    else:
        data["config_snapshot"] = {}

    # JSONB columns come back as native Python objects from psycopg —
    # but they could also be strings if the column is TEXT-typed.
    for key in _JSON_FIELDS:
        raw = data.get(key)
        if isinstance(raw, str):
            data[key] = json.loads(raw)

    # Datetime columns: psycopg returns datetime objects from TIMESTAMPTZ
    # but we also handle ISO strings for safety.
    for key in _DATETIME_FIELDS:
        val = data.get(key)
        if isinstance(val, str):
            data[key] = datetime.fromisoformat(val)

    return TraceRecord(**data)


# ── Provider ──────────────────────────────────────────────────────────────────


class PostgresProvider(TracingProvider):
    """Store traces in a PostgreSQL database.

    Requires the ``psycopg`` package (``pip install psycopg[binary]``).

    Args:
        connection_string: PostgreSQL connection string
            (e.g. ``postgresql://user:pass@host:5432/db``).
    """

    def __init__(self, connection_string: str) -> None:
        import psycopg

        self._conninfo = connection_string
        # Verify connectivity on init (fail fast)
        with psycopg.connect(self._conninfo) as conn:
            conn.execute("SELECT 1")
        logger.info("PostgresProvider connected to %s", self._safe_conninfo)

    @property
    def _safe_conninfo(self) -> str:
        """Connection string with password masked for logging."""
        import psycopg.conninfo

        try:
            params = psycopg.conninfo.conninfo_to_dict(self._conninfo)
            if "password" in params and params["password"]:
                params["password"] = "****"
            return psycopg.conninfo.make_conninfo(**params)
        except psycopg.ProgrammingError:
            # Fallback: mask URI-style password
            import re

            return re.sub(r"(://[^:]+:)[^@]+(@)", r"\1****\2", self._conninfo)

    # ── TracingProvider interface ──

    def log_trace(self, trace: TraceRecord) -> str:
        """Insert a new trace with config snapshot deduplication."""
        import psycopg
        from psycopg.types.json import Jsonb

        c_hash = _config_hash(trace.config_snapshot)

        with psycopg.connect(self._conninfo) as conn:
            # Upsert config snapshot (ON CONFLICT DO NOTHING = skip if exists)
            conn.execute(
                "INSERT INTO config_snapshots (hash, config) "
                "VALUES (%s, %s) ON CONFLICT (hash) DO NOTHING",
                (c_hash, Jsonb(trace.config_snapshot)),
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
                    %s, %s, %s, %s, %s,
                    %s, %s, %s, %s,
                    %s, %s,
                    %s, %s, %s, %s,
                    %s,
                    %s, %s, %s
                )
                """,
                (
                    trace.id,
                    trace.session_id,
                    trace.user_id,
                    trace.created_at,
                    trace.response_at,
                    trace.query,
                    Jsonb(trace.expanded_queries),
                    Jsonb(trace.retrieved_chunks),
                    Jsonb(trace.reranked_chunks),
                    trace.formatted_context,
                    Jsonb(trace.collection_ids),
                    trace.response,
                    trace.model,
                    trace.temperature,
                    trace.latency_ms,
                    c_hash,
                    trace.feedback_score,
                    Jsonb(trace.feedback_tags),
                    trace.feedback_comment,
                ),
            )
            conn.commit()

        logger.debug("Logged trace %s for query: %s", trace.id, trace.query[:80])
        return trace.id

    def update_trace(self, trace_id: str, **fields: object) -> None:
        """Update specific fields on an existing trace."""
        if not fields:
            return

        import psycopg
        from psycopg.types.json import Jsonb

        # Validate column names to prevent SQL injection
        invalid = fields.keys() - _VALID_COLUMNS
        if invalid:
            msg = f"Invalid field names for trace update: {invalid!r}"
            raise ValueError(msg)

        # Serialise JSON fields for Postgres JSONB
        processed: dict[str, object] = {}
        for key, value in fields.items():
            if key in _JSON_FIELDS:
                processed[key] = Jsonb(value)
            else:
                processed[key] = value

        # Build SET clause with %s placeholders (psycopg v3 server-side params)
        set_clause = ", ".join(f"{k} = %s" for k in processed)

        with psycopg.connect(self._conninfo) as conn:
            conn.execute(
                f"UPDATE traces SET {set_clause} WHERE id = %s",  # noqa: S608
                [*processed.values(), trace_id],
            )
            conn.commit()

    def get_trace(self, trace_id: str) -> TraceRecord | None:
        """Retrieve a single trace by ID (with config snapshot joined)."""
        import psycopg
        from psycopg.rows import dict_row

        with psycopg.connect(self._conninfo, row_factory=dict_row) as conn:
            row = conn.execute(
                """
                SELECT t.*, c.config
                FROM traces t
                LEFT JOIN config_snapshots c ON t.config_hash = c.hash
                WHERE t.id = %s
                """,
                (trace_id,),
            ).fetchone()

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
        import psycopg
        from psycopg.rows import dict_row

        conditions: list[str] = []
        params: list[object] = []

        if session_id is not None:
            conditions.append("t.session_id = %s")
            params.append(session_id)
        if user_id is not None:
            conditions.append("t.user_id = %s")
            params.append(user_id)

        where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        sql = (  # noqa: S608
            f"SELECT t.*, c.config FROM traces t "
            f"LEFT JOIN config_snapshots c ON t.config_hash = c.hash "
            f"{where} ORDER BY t.created_at DESC LIMIT %s OFFSET %s"
        )
        params.extend([limit, offset])

        with psycopg.connect(self._conninfo, row_factory=dict_row) as conn:
            rows = conn.execute(sql, params).fetchall()

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
        import psycopg

        cutoff = datetime.now(timezone.utc) - timedelta(days=older_than_days)
        with psycopg.connect(self._conninfo) as conn:
            cursor = conn.execute(
                "DELETE FROM traces WHERE created_at < %s",
                (cutoff,),
            )
            conn.commit()
        return cursor.rowcount
