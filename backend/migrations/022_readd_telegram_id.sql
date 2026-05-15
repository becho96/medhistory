-- Migration: Re-add Telegram bot support
-- Date: 2026-05-15
--
-- Re-introduces telegram_id, originally added in 007 and dropped in 019.
-- The bot returns as a separate aiogram service; account linkage is via
-- this column. Conversation state lives in the bot's in-memory FSM, so
-- the old telegram_bot_state table is intentionally NOT re-created.
--
-- 152-ФЗ note: cross-border transfer consent for Telegram is handled as a
-- separate consent_type recorded in user_consents (no schema change needed).

ALTER TABLE users ADD COLUMN IF NOT EXISTS telegram_id BIGINT UNIQUE;

CREATE INDEX IF NOT EXISTS ix_users_telegram_id ON users(telegram_id);
