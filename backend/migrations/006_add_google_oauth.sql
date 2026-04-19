-- Migration: Add Google OAuth support
-- Date: 2026-01-05

-- Add google_id column to users table
ALTER TABLE users ADD COLUMN IF NOT EXISTS google_id VARCHAR(255) UNIQUE;

-- Create index for faster lookups
CREATE INDEX IF NOT EXISTS ix_users_google_id ON users(google_id);

