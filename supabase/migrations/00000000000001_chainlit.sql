-- Migration: Chainlit data layer schema
--
-- Tables required by Chainlit's ChainlitDataLayer (asyncpg) for persistent
-- conversation history, step tracking, file elements, and feedback.
--
-- Table and column names must match exactly what ChainlitDataLayer queries.
-- Chainlit uses PascalCase table names and camelCase column names (with double
-- quotes) — we preserve them exactly to avoid mapping issues.
--
-- Derived from chainlit/data/chainlit_data_layer.py INSERT/SELECT statements.

-- ── Users ──────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS "User" (
    "id"         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    "identifier" TEXT NOT NULL UNIQUE,
    "metadata"   JSONB NOT NULL DEFAULT '{}'::jsonb,
    "createdAt"  TIMESTAMPTZ DEFAULT now(),
    "updatedAt"  TIMESTAMPTZ DEFAULT now()
);

-- ── Threads (conversations) ────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS "Thread" (
    "id"             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    "name"           TEXT,
    "userId"         UUID REFERENCES "User"("id") ON DELETE SET NULL,
    "userIdentifier" TEXT,
    "tags"           TEXT[],
    "metadata"       JSONB,
    "createdAt"      TIMESTAMPTZ DEFAULT now(),
    "updatedAt"      TIMESTAMPTZ DEFAULT now(),
    "deletedAt"      TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_thread_user ON "Thread" ("userId");
CREATE INDEX IF NOT EXISTS idx_thread_updated ON "Thread" ("updatedAt" DESC);

-- ── Steps (messages and tool calls) ───────────────────────────────────────

CREATE TABLE IF NOT EXISTS "Step" (
    "id"            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    "threadId"      UUID NOT NULL REFERENCES "Thread"("id") ON DELETE CASCADE,
    "parentId"      UUID,
    "name"          TEXT NOT NULL,
    "type"          TEXT NOT NULL,
    "input"         TEXT,
    "output"        TEXT,
    "metadata"      JSONB,
    "tags"          TEXT[],
    "showInput"     TEXT,
    "isError"       BOOLEAN DEFAULT false,
    "startTime"     TIMESTAMPTZ,
    "endTime"       TIMESTAMPTZ,
    "createdAt"     TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_step_thread ON "Step" ("threadId");
CREATE INDEX IF NOT EXISTS idx_step_start ON "Step" ("startTime");

-- ── Elements (file attachments, images, etc.) ─────────────────────────────

CREATE TABLE IF NOT EXISTS "Element" (
    "id"          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    "threadId"    UUID REFERENCES "Thread"("id") ON DELETE CASCADE,
    "stepId"      UUID REFERENCES "Step"("id") ON DELETE CASCADE,
    "type"        TEXT,
    "url"         TEXT,
    "chainlitKey" TEXT,
    "name"        TEXT NOT NULL,
    "display"     TEXT,
    "objectKey"   TEXT,
    "size"        TEXT,
    "page"        INT,
    "language"    TEXT,
    "mime"        TEXT,
    "props"       JSONB,
    "metadata"    JSONB
);

CREATE INDEX IF NOT EXISTS idx_element_thread ON "Element" ("threadId");
CREATE INDEX IF NOT EXISTS idx_element_step ON "Element" ("stepId");

-- ── Feedbacks ──────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS "Feedback" (
    "id"      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    "stepId"  UUID NOT NULL REFERENCES "Step"("id") ON DELETE CASCADE,
    "name"    TEXT,
    "value"   INT NOT NULL,
    "comment" TEXT
);

CREATE INDEX IF NOT EXISTS idx_feedback_step ON "Feedback" ("stepId");

-- ── Row Level Security ─────────────────────────────────────────────────────
-- RLS is enabled to prevent direct PostgREST access from anon/authenticated
-- roles. The application connects as the postgres role which has full access.

ALTER TABLE "User" ENABLE ROW LEVEL SECURITY;
ALTER TABLE "Thread" ENABLE ROW LEVEL SECURITY;
ALTER TABLE "Step" ENABLE ROW LEVEL SECURITY;
ALTER TABLE "Element" ENABLE ROW LEVEL SECURITY;
ALTER TABLE "Feedback" ENABLE ROW LEVEL SECURITY;

CREATE POLICY user_app_full_access ON "User"
    FOR ALL TO postgres USING (true) WITH CHECK (true);

CREATE POLICY thread_app_full_access ON "Thread"
    FOR ALL TO postgres USING (true) WITH CHECK (true);

CREATE POLICY step_app_full_access ON "Step"
    FOR ALL TO postgres USING (true) WITH CHECK (true);

CREATE POLICY element_app_full_access ON "Element"
    FOR ALL TO postgres USING (true) WITH CHECK (true);

CREATE POLICY feedback_app_full_access ON "Feedback"
    FOR ALL TO postgres USING (true) WITH CHECK (true);

-- ── Future: per-user row isolation ────────────────────────────────────────
-- When multi-user auth is production-hardened, add policies like:
--
--   CREATE POLICY thread_user_isolation ON "Thread"
--       FOR ALL TO authenticated
--       USING ((select auth.uid()::text) = "userIdentifier")
--       WITH CHECK ((select auth.uid()::text) = "userIdentifier");
--
-- Note: wrap auth.uid() in (select ...) to prevent per-row evaluation.
