"""SQLite-backed trace and feedback store.

All storage is handled by a single ``.db`` file in the workspace's
``.rag-facile/`` directory.  No external dependencies — uses the
Python standard-library ``sqlite3`` module exclusively.
"""

from __future__ import annotations

import json
import logging
import sqlite3
from pathlib import Path
from typing import TYPE_CHECKING, Any

from ._models import FeedbackRecord, TraceRecord


if TYPE_CHECKING:
    pass


logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# DDL
# ---------------------------------------------------------------------------

_DDL = """
CREATE TABLE IF NOT EXISTS traces (
    trace_id        TEXT PRIMARY KEY,
    session_id      TEXT NOT NULL,
    created_at      TEXT NOT NULL,
    question        TEXT NOT NULL,
    chunks          TEXT,
    prompt_sent     TEXT,
    system_prompt   TEXT,
    answer          TEXT NOT NULL,
    model_alias     TEXT NOT NULL,
    model_resolved  TEXT,
    preset          TEXT,
    pipeline_config TEXT NOT NULL,
    latency_ms      INTEGER
);

CREATE TABLE IF NOT EXISTS feedback (
    feedback_id TEXT PRIMARY KEY,
    trace_id    TEXT NOT NULL REFERENCES traces(trace_id) ON DELETE CASCADE,
    created_at  TEXT NOT NULL,
    star_rating INTEGER,
    sentiment   TEXT,
    tags        TEXT,
    comment     TEXT
);

CREATE INDEX IF NOT EXISTS idx_traces_session  ON traces(session_id);
CREATE INDEX IF NOT EXISTS idx_traces_created  ON traces(created_at);
CREATE INDEX IF NOT EXISTS idx_feedback_trace  ON feedback(trace_id);

CREATE VIRTUAL TABLE IF NOT EXISTS traces_fts USING fts5(
    question, answer,
    content=traces, content_rowid=rowid
);

CREATE VIEW IF NOT EXISTS ragas_export AS
SELECT
    t.trace_id,
    t.question           AS user_input,
    t.chunks             AS retrieved_contexts_json,
    t.answer             AS response,
    json_object(
        'model_resolved', t.model_resolved,
        'model_alias',    t.model_alias,
        'preset',         t.preset,
        'pipeline_config', json(t.pipeline_config),
        'star_rating',    f.star_rating,
        'sentiment',      f.sentiment,
        'tags',           json(f.tags)
    )                    AS _metadata
FROM traces t
LEFT JOIN feedback f ON f.trace_id = t.trace_id;
"""


# ---------------------------------------------------------------------------
# Store
# ---------------------------------------------------------------------------


class TraceStore:
    """SQLite-backed store for RAG turn traces and user feedback.

    Creates the database file and schema automatically on first use.
    Thread-safe for single-writer / multi-reader workloads (SQLite WAL mode).

    Args:
        db_path: Path to the SQLite database file.
    """

    def __init__(self, db_path: str | Path) -> None:
        self._db_path = Path(db_path)
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    # ── Initialisation ──

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        return conn

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.executescript(_DDL)

    # ── Write ──

    def record_turn(self, record: TraceRecord) -> str:
        """Insert a trace record and return its ``trace_id``.

        Args:
            record: Completed RAG turn data.

        Returns:
            The ``trace_id`` of the inserted record.
        """
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO traces (
                    trace_id, session_id, created_at,
                    question, chunks, prompt_sent, system_prompt,
                    answer, model_alias, model_resolved,
                    preset, pipeline_config, latency_ms
                ) VALUES (
                    :trace_id, :session_id, :created_at,
                    :question, :chunks, :prompt_sent, :system_prompt,
                    :answer, :model_alias, :model_resolved,
                    :preset, :pipeline_config, :latency_ms
                )
                """,
                record,
            )
        logger.debug(
            "Recorded trace %s (latency=%sms)", record["trace_id"], record["latency_ms"]
        )
        return record["trace_id"]

    def record_feedback(self, fb: FeedbackRecord) -> None:
        """Insert or replace a feedback record.

        Args:
            fb: User evaluation data linked to a trace.
        """
        # Serialise tags list → JSON string for storage
        row: dict[str, Any] = {**fb, "tags": json.dumps(fb["tags"])}
        with self._connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO feedback (
                    feedback_id, trace_id, created_at,
                    star_rating, sentiment, tags, comment
                ) VALUES (
                    :feedback_id, :trace_id, :created_at,
                    :star_rating, :sentiment, :tags, :comment
                )
                """,
                row,
            )
        logger.debug(
            "Recorded feedback %s for trace %s", fb["feedback_id"], fb["trace_id"]
        )

    # ── Read ──

    def recent(self, n: int = 20) -> list[dict[str, Any]]:
        """Return the *n* most recent traces (newest first).

        Each row includes any linked feedback fields (NULL when absent).

        Args:
            n: Maximum number of rows to return.

        Returns:
            List of dicts with combined trace + feedback fields.
        """
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT
                    t.trace_id, t.session_id, t.created_at,
                    t.question, t.answer,
                    t.model_alias, t.model_resolved,
                    t.preset, t.latency_ms,
                    f.star_rating, f.sentiment, f.tags
                FROM traces t
                LEFT JOIN feedback f ON f.trace_id = t.trace_id
                ORDER BY t.created_at DESC
                LIMIT ?
                """,
                (n,),
            ).fetchall()
        return [dict(r) for r in rows]

    def export_ragas(self, limit: int = 1000) -> list[dict[str, Any]]:
        """Export traces in RAGAS ``SingleTurnSample``-compatible format.

        Maps directly to the ``ragas_export`` view defined in the schema.

        Args:
            limit: Maximum number of rows to export.

        Returns:
            List of dicts with ``user_input``, ``retrieved_contexts``,
            ``response``, and ``_metadata``.
        """
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM ragas_export ORDER BY trace_id LIMIT ?", (limit,)
            ).fetchall()

        results = []
        for row in rows:
            d = dict(row)
            # Deserialise JSON columns
            chunks_raw = d.pop("retrieved_contexts_json", None)
            d["retrieved_contexts"] = (
                [c["content"] for c in json.loads(chunks_raw)] if chunks_raw else []
            )
            d["_metadata"] = json.loads(d["_metadata"]) if d.get("_metadata") else {}
            results.append(d)
        return results

    def stats(self) -> dict[str, Any]:
        """Return summary statistics over all stored traces/feedback.

        Returns:
            Dict with ``total_traces``, ``total_feedback``, ``avg_star``,
            ``top_tags``.
        """
        with self._connect() as conn:
            total_traces = conn.execute("SELECT COUNT(*) FROM traces").fetchone()[0]
            total_feedback = conn.execute("SELECT COUNT(*) FROM feedback").fetchone()[0]
            avg_star = conn.execute(
                "SELECT AVG(star_rating) FROM feedback WHERE star_rating IS NOT NULL"
            ).fetchone()[0]
            tags_rows = conn.execute(
                "SELECT tags FROM feedback WHERE tags IS NOT NULL AND tags != '[]'"
            ).fetchall()

        # Tally individual tags
        tag_counts: dict[str, int] = {}
        for row in tags_rows:
            for tag in json.loads(row[0]):
                tag_counts[tag] = tag_counts.get(tag, 0) + 1
        top_tags = sorted(tag_counts.items(), key=lambda x: x[1], reverse=True)[:10]

        return {
            "total_traces": total_traces,
            "total_feedback": total_feedback,
            "avg_star": round(avg_star, 2) if avg_star is not None else None,
            "top_tags": top_tags,
        }

    def prune(self, older_than_days: int) -> int:
        """Delete traces (and their feedback) older than *older_than_days* days.

        Args:
            older_than_days: Retention period in days.

        Returns:
            Number of traces deleted.
        """
        from datetime import datetime, timedelta, timezone

        cutoff = (
            datetime.now(timezone.utc) - timedelta(days=older_than_days)
        ).isoformat()
        with self._connect() as conn:
            # ON DELETE CASCADE on the feedback FK ensures feedback rows are
            # removed automatically when their parent trace is deleted.
            cursor = conn.execute("DELETE FROM traces WHERE created_at < ?", (cutoff,))
            deleted = cursor.rowcount
        if deleted:
            logger.info("Pruned %d traces older than %d days", deleted, older_than_days)
        return deleted
