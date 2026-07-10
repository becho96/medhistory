-- Migration: Reminders (Phase 1 — one-off, deadline-based)
-- Date: 2026-07-09
--
-- Single source of truth for patient reminders. Auto reminders are
-- materialized from extracted document orders (keyed by
-- source_document_id + source_order_index for idempotent upsert);
-- manual reminders are user-created rows (source_document_id IS NULL).
-- Auto-close (a later matching document fulfils the referral) and
-- urgency escalation are computed at read time.

BEGIN;

CREATE TABLE IF NOT EXISTS reminders (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,

    origin VARCHAR(16) NOT NULL,          -- 'auto' | 'manual'
    kind VARCHAR(32) NOT NULL,            -- follow_up_appointment | referral_research | referral_specialist
    title VARCHAR(500) NOT NULL,

    -- matching targets (mirror the extracted order fields), used for read-time auto-close
    order_type VARCHAR(32),
    target_document_type VARCHAR(100),
    target_document_subtype VARCHAR(100),
    target_research_area VARCHAR(100),
    target_specialty VARCHAR(100),

    -- source link (auto reminders only)
    source_document_id UUID REFERENCES documents(id) ON DELETE CASCADE,
    source_order_index INTEGER,

    -- deadline
    due_date DATE,
    due_source VARCHAR(16),               -- 'absolute' | 'relative' | 'manual'

    -- lifecycle
    status VARCHAR(16) NOT NULL DEFAULT 'active',   -- active | done | dismissed
    status_source VARCHAR(16) NOT NULL DEFAULT 'auto',
    resolution VARCHAR(32),               -- completed_uploaded | completed_manual | not_required | incorrect
    completed_document_id UUID REFERENCES documents(id) ON DELETE SET NULL,
    completed_at TIMESTAMPTZ,
    note TEXT,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Idempotent upsert key for auto reminders materialized from a document's orders.
CREATE UNIQUE INDEX IF NOT EXISTS idx_reminders_source
    ON reminders (source_document_id, source_order_index)
    WHERE source_document_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_reminders_user_active
    ON reminders (user_id, status, due_date);

COMMIT;
