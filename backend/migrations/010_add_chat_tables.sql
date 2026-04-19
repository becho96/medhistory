-- ==================================================
-- MedHistory - Chat tables for AI Assistant
-- ==================================================
-- Миграция: таблицы чата (сессии и сообщения)
-- Выполнить: psql -U medhistory_user medhistory -f backend/migrations/010_add_chat_tables.sql
-- ==================================================

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Chat sessions: один чат = один диалог с ассистентом
CREATE TABLE IF NOT EXISTS chat_sessions (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id         UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title           VARCHAR(500) NOT NULL DEFAULT 'Новый чат',
    model_provider  VARCHAR(50) NOT NULL DEFAULT 'anthropic',
    model_id        VARCHAR(100) NOT NULL DEFAULT 'claude-sonnet-4-6',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_chat_sessions_user_id ON chat_sessions(user_id);

-- Chat messages: сообщения внутри сессии
CREATE TABLE IF NOT EXISTS chat_messages (
    id         UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id UUID NOT NULL REFERENCES chat_sessions(id) ON DELETE CASCADE,
    role       VARCHAR(20) NOT NULL,
    content    TEXT NOT NULL,
    metadata   JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_chat_messages_session_id ON chat_messages(session_id);
