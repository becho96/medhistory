-- Migration 029: Manual treatment-plan overrides (Phase 1b)
-- Date: 2026-07-11
--
-- Read-time overrides on the DERIVED treatment-plan graph (episodes are
-- connected components of the referral graph — see services/treatment_plan.py).
-- Overrides are anchored to STABLE node keys (doc:<document_id>), never to the
-- volatile derived episode id, so they survive as the graph regrows.
--
--   kind='rename' : anchor_key = a node in the episode; title = custom name
--   kind='merge'  : anchor_key + other_key = force-union two components
--   kind='cut'    : anchor_key = referral edge source, other_key = its target;
--                   removes that edge from grouping so the component splits

BEGIN;

CREATE TABLE IF NOT EXISTS plan_overrides (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,

    kind VARCHAR(16) NOT NULL,        -- 'rename' | 'merge' | 'cut'
    anchor_key TEXT NOT NULL,         -- stable node key this override attaches to
    other_key TEXT,                   -- merge: node in other component; cut: edge target
    title VARCHAR(200),               -- rename only

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_plan_overrides_user ON plan_overrides (user_id);

COMMIT;
