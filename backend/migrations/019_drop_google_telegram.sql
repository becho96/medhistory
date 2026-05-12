-- Migration: Drop Google OAuth + Telegram bot integration
-- Date: 2026-05-12
--
-- Reverses migrations 006, 007, 008.
-- Background: 152-ФЗ requires written consent for cross-border transfer
-- of personal data. Google (US) and Telegram (UAE) integrations triggered
-- such transfer; removing them avoids that legal surface area entirely.
--
-- Forward-only. To recover historical google_id / telegram_id values,
-- restore from backup before applying.

BEGIN;

DROP TABLE IF EXISTS telegram_bot_state;

ALTER TABLE users DROP COLUMN IF EXISTS google_id;
ALTER TABLE users DROP COLUMN IF EXISTS telegram_id;

COMMIT;
