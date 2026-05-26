-- Migration: User feedback
-- Date: 2026-05-26
--
-- Stores user-submitted feedback messages with a snapshot of basic
-- metadata captured at submission time (route, viewport, user-agent).
-- user_email is duplicated alongside user_id to make analytical
-- queries straightforward without joining the users table.

BEGIN;

CREATE TABLE IF NOT EXISTS feedback (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    user_email VARCHAR(255),
    message TEXT NOT NULL,
    url TEXT,
    user_agent TEXT,
    client_meta JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_feedback_user_id
    ON feedback (user_id);

CREATE INDEX IF NOT EXISTS idx_feedback_created_at
    ON feedback (created_at DESC);

COMMIT;
