-- 027_analyte_mapping_queue.sql
-- Review queue for unmapped lab analytes (Phase 1 auto-mapper).
-- Each row = one distinct (test_name, unit) that the exact-dictionary lookup missed.
-- The resolver (embeddings kNN + LLM arbiter) pre-fills a proposal; a human approves
-- or rejects it in db-viewer. Nothing is written to analyte_synonyms automatically.

CREATE TABLE IF NOT EXISTS analyte_mapping_queue (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    original_name       TEXT NOT NULL,
    original_name_lower TEXT NOT NULL,
    unit                TEXT NOT NULL DEFAULT '',
    unit_lower          TEXT NOT NULL DEFAULT '',
    occurrences         INTEGER NOT NULL DEFAULT 1,

    -- resolver proposal
    candidates          JSONB,            -- [{canonical, score, std_unit, category}]
    proposed_action     TEXT,             -- 'map' | 'create' | 'uncertain'
    proposed_target     TEXT,             -- canonical name (when action='map')
    proposed_new_name   TEXT,             -- when action='create'
    proposed_new_category TEXT,
    proposed_new_unit   TEXT,
    proposed_coefficient NUMERIC(15, 6) DEFAULT 1.0,
    llm_confidence      NUMERIC(4, 3),
    llm_reason          TEXT,

    -- workflow
    status              TEXT NOT NULL DEFAULT 'pending',  -- pending | approved | rejected
    resolved_at         TIMESTAMPTZ,
    resolved_by         TEXT,

    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- One queue row per distinct (name, unit).
CREATE UNIQUE INDEX IF NOT EXISTS ix_amq_name_unit
    ON analyte_mapping_queue (original_name_lower, unit_lower);

CREATE INDEX IF NOT EXISTS ix_amq_status
    ON analyte_mapping_queue (status);
