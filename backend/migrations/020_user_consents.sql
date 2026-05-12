-- Migration: User consent records (152-ФЗ)
-- Date: 2026-05-12
--
-- Stores explicit, time-stamped consent records granted by users at
-- registration (and later — when consent text is updated, or for
-- granular purposes such as cross-border processing).
--
-- document_version pins the consent to the exact text the user saw,
-- so we can prove compliance if a user disputes scope. We use a
-- content hash (sha256 of the legal markdown file) — change the file,
-- and new registrations get a new version automatically.

BEGIN;

CREATE TABLE IF NOT EXISTS user_consents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    consent_type TEXT NOT NULL,            -- 'terms_and_privacy' | 'special_category'
    document_version TEXT NOT NULL,        -- sha256 of the legal document at time of grant
    granted_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    revoked_at TIMESTAMPTZ,
    ip_address INET,
    user_agent TEXT
);

CREATE INDEX IF NOT EXISTS idx_user_consents_user
    ON user_consents (user_id);

CREATE INDEX IF NOT EXISTS idx_user_consents_active
    ON user_consents (user_id, consent_type)
    WHERE revoked_at IS NULL;

COMMIT;
