-- Migration: Subscription tiers (Free/Pro) and promo code system
-- Date: 2026-05-13
--
-- Introduces a two-tier subscription model with promo code activation.
--
-- Free tier: 2 documents/month, no family account.
-- Pro tier: 100 documents/month, family account enabled, expires at pro_expires_at.
--
-- For family accounts the document quota is a shared pool consumed by the
-- billing owner (the family owner). Members do not have a separate quota.
--
-- Promo codes have a configurable duration_days (how long Pro is granted),
-- max_activations (1 = single-use, N = multi-use campaign), and an optional
-- expires_at (lifetime of the code itself, not of the Pro it grants).

BEGIN;

ALTER TABLE users
    ADD COLUMN IF NOT EXISTS subscription_tier VARCHAR(16) NOT NULL DEFAULT 'free',
    ADD COLUMN IF NOT EXISTS pro_expires_at TIMESTAMPTZ NULL,
    ADD COLUMN IF NOT EXISTS pro_source VARCHAR(32) NULL,     -- 'promo' | 'admin'
    ADD COLUMN IF NOT EXISTS is_admin BOOLEAN NOT NULL DEFAULT FALSE;

CREATE INDEX IF NOT EXISTS idx_users_pro_expires_at
    ON users (pro_expires_at)
    WHERE pro_expires_at IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_users_is_admin
    ON users (is_admin)
    WHERE is_admin = TRUE;

CREATE TABLE IF NOT EXISTS promo_codes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    code VARCHAR(64) NOT NULL UNIQUE,
    duration_days INTEGER NOT NULL CHECK (duration_days > 0),
    max_activations INTEGER NOT NULL DEFAULT 1 CHECK (max_activations > 0),
    activations_count INTEGER NOT NULL DEFAULT 0,
    expires_at TIMESTAMPTZ NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    comment TEXT NULL,
    created_by UUID NULL REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_promo_codes_active
    ON promo_codes (is_active)
    WHERE is_active = TRUE;

CREATE TABLE IF NOT EXISTS promo_code_activations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    promo_code_id UUID NOT NULL REFERENCES promo_codes(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    activated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    pro_extended_to TIMESTAMPTZ NOT NULL,
    UNIQUE (promo_code_id, user_id)
);

CREATE INDEX IF NOT EXISTS idx_promo_activations_user
    ON promo_code_activations (user_id);

-- Speeds up the monthly document counter used by the quota check.
CREATE INDEX IF NOT EXISTS idx_documents_user_created_at
    ON documents (user_id, created_at DESC);

COMMIT;
