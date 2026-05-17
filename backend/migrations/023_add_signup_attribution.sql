-- Migration: Marketing attribution + interview opt-in
-- Date: 2026-05-16
--
-- Supports the first-wave user acquisition campaign:
--  - signup_source:    normalized channel ('direct' | 'referral' | utm_source value)
--  - signup_utm:       full UTM payload + referrer captured on first landing
--  - interview_opt_in: user agreed to a product feedback interview

BEGIN;

ALTER TABLE users
    ADD COLUMN IF NOT EXISTS signup_source VARCHAR(64) NULL,
    ADD COLUMN IF NOT EXISTS signup_utm JSONB NULL,
    ADD COLUMN IF NOT EXISTS interview_opt_in BOOLEAN NOT NULL DEFAULT FALSE;

CREATE INDEX IF NOT EXISTS idx_users_signup_source
    ON users (signup_source)
    WHERE signup_source IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_users_interview_opt_in
    ON users (interview_opt_in)
    WHERE interview_opt_in = TRUE;

COMMIT;
