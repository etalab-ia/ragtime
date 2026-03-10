-- Migration: RAG pipeline tracing schema
--
-- Stores RAG pipeline observability data: queries, retrieved chunks,
-- LLM responses, latency, config snapshots, and user feedback.
--
-- This is the Postgres equivalent of the SQLite schema in
-- packages/tracing/src/rag_facile/tracing/sqlite.py.
-- Key differences: UUID primary keys, TIMESTAMPTZ, native JSONB,
-- and SHA-256 config deduplication via a separate table.

-- ── Config snapshot deduplication ─────────────────────────────────
-- Identical ragfacile.toml configs (the common case) are stored
-- exactly once, keyed by SHA-256 hash of the canonical JSON.

CREATE TABLE IF NOT EXISTS config_snapshots (
    hash    TEXT PRIMARY KEY,
    config  JSONB NOT NULL
);

-- ── Traces ────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS traces (
    id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id        TEXT,
    user_id           TEXT,
    created_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    response_at       TIMESTAMPTZ,

    -- RAG pipeline data
    query             TEXT NOT NULL DEFAULT '',
    expanded_queries  JSONB NOT NULL DEFAULT '[]'::jsonb,
    retrieved_chunks  JSONB NOT NULL DEFAULT '[]'::jsonb,
    reranked_chunks   JSONB NOT NULL DEFAULT '[]'::jsonb,
    formatted_context TEXT NOT NULL DEFAULT '',
    collection_ids    JSONB NOT NULL DEFAULT '[]'::jsonb,

    -- LLM data
    response          TEXT,
    model             TEXT NOT NULL DEFAULT '',
    temperature       DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    latency_ms        INTEGER,

    -- Config snapshot (FK → config_snapshots.hash)
    config_hash       TEXT NOT NULL DEFAULT ''
        REFERENCES config_snapshots(hash),

    -- User feedback
    feedback_score    INTEGER,
    feedback_tags     JSONB NOT NULL DEFAULT '[]'::jsonb,
    feedback_comment  TEXT
);

-- Performance indexes
CREATE INDEX IF NOT EXISTS idx_traces_session
    ON traces (session_id) WHERE session_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_traces_user
    ON traces (user_id) WHERE user_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_traces_created
    ON traces (created_at DESC);

-- ── RAGAS export view ─────────────────────────────────────────────
-- Convenience view that flattens traces into the format expected by
-- the RAGAS evaluation framework (user_input, retrieved_contexts,
-- response, reference).

CREATE OR REPLACE VIEW ragas_export
    WITH (security_invoker = on)
AS
SELECT
    t.id,
    t.query              AS user_input,
    t.retrieved_chunks   AS retrieved_contexts,
    t.response,
    t.model,
    t.latency_ms,
    t.feedback_score,
    t.created_at,
    c.config             AS config_snapshot
FROM traces t
LEFT JOIN config_snapshots c ON t.config_hash = c.hash;

-- ── Row Level Security ────────────────────────────────────────────
-- Minimal RLS: tables are locked down by default. The application
-- connects as a privileged role (service_role or direct Postgres
-- credentials) that bypasses RLS. This prevents accidental exposure
-- via Supabase's PostgREST API (anon/authenticated roles).
--
-- If multi-tenant isolation is needed later, add policies like:
--   USING ((select auth.uid())::text = user_id)

ALTER TABLE config_snapshots ENABLE ROW LEVEL SECURITY;
ALTER TABLE traces ENABLE ROW LEVEL SECURITY;

-- service_role bypasses RLS automatically (Supabase built-in).
-- For the application's direct Postgres connection, grant full access
-- to the postgres role (used by psycopg/SQLAlchemy connections).
CREATE POLICY config_snapshots_app_full_access ON config_snapshots
    FOR ALL
    TO postgres
    USING (true)
    WITH CHECK (true);

CREATE POLICY traces_app_full_access ON traces
    FOR ALL
    TO postgres
    USING (true)
    WITH CHECK (true);

-- Deny anon and authenticated roles by default (no policies = no access).
-- This is the RLS default behavior — enabled + no matching policy = denied.
