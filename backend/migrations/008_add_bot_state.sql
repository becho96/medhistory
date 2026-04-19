-- Migration: Add Telegram bot conversation state table
-- Date: 2026-02-07

CREATE TABLE IF NOT EXISTS telegram_bot_state (
    chat_id BIGINT PRIMARY KEY,
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    state VARCHAR(50) NOT NULL DEFAULT 'idle',
    data JSONB DEFAULT '{}',
    jwt_token TEXT,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Index for user_id lookups
CREATE INDEX IF NOT EXISTS ix_telegram_bot_state_user_id ON telegram_bot_state(user_id);
