-- Migration: Add Telegram bot support
-- Date: 2026-02-07

-- Add telegram_id column to users table
ALTER TABLE users ADD COLUMN IF NOT EXISTS telegram_id BIGINT UNIQUE;

-- Create index for faster lookups
CREATE INDEX IF NOT EXISTS ix_users_telegram_id ON users(telegram_id);
