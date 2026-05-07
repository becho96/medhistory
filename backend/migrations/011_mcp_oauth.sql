-- ==================================================
-- MedHistory — MCP OAuth 2.1 server tables
-- ==================================================
-- Phase 2: multi-user remote MCP. Stores DCR-registered clients,
-- authorization codes, access tokens, refresh tokens. Each issued token
-- is bound to (client_id, user_id) — that's how MCP tools resolve
-- whose medical history to serve on each request.
--
-- Apply: psql -U medhistory_user medhistory -f backend/migrations/011_mcp_oauth.sql
-- ==================================================

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- DCR-registered OAuth clients (RFC 7591). One row per (claude.ai instance / app)
-- that registered with us. Clients are NOT tied to a single user — many users can
-- authorize the same client; user binding lives on tokens.
CREATE TABLE IF NOT EXISTS mcp_oauth_clients (
    client_id        VARCHAR(255) PRIMARY KEY,
    client_secret    VARCHAR(255),
    client_metadata  JSONB        NOT NULL,
    issued_at        TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

-- Short-lived (~10 min) auth codes. Issued after user consent, exchanged for tokens.
CREATE TABLE IF NOT EXISTS mcp_authorization_codes (
    code                              VARCHAR(255) PRIMARY KEY,
    client_id                         VARCHAR(255) NOT NULL REFERENCES mcp_oauth_clients(client_id) ON DELETE CASCADE,
    user_id                           UUID         NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    scopes                            TEXT[]       NOT NULL,
    expires_at                        TIMESTAMPTZ  NOT NULL,
    code_challenge                    VARCHAR(255) NOT NULL,
    redirect_uri                      TEXT         NOT NULL,
    redirect_uri_provided_explicitly  BOOLEAN      NOT NULL,
    resource                          TEXT,
    created_at                        TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_mcp_authcodes_expires ON mcp_authorization_codes(expires_at);

-- Access tokens. Bound to (client_id, user_id). The MCP request handler reads
-- Authorization: Bearer <token>, looks up the row, extracts user_id, and gates
-- every tool call by it.
CREATE TABLE IF NOT EXISTS mcp_access_tokens (
    token       VARCHAR(255) PRIMARY KEY,
    client_id   VARCHAR(255) NOT NULL REFERENCES mcp_oauth_clients(client_id) ON DELETE CASCADE,
    user_id     UUID         NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    scopes      TEXT[]       NOT NULL,
    expires_at  TIMESTAMPTZ,
    resource    TEXT,
    created_at  TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    revoked_at  TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS idx_mcp_accesstokens_user      ON mcp_access_tokens(user_id);
CREATE INDEX IF NOT EXISTS idx_mcp_accesstokens_client    ON mcp_access_tokens(client_id);
CREATE INDEX IF NOT EXISTS idx_mcp_accesstokens_active    ON mcp_access_tokens(user_id) WHERE revoked_at IS NULL;

-- Refresh tokens. Long-lived (~30 days). Used to mint new access tokens.
CREATE TABLE IF NOT EXISTS mcp_refresh_tokens (
    token       VARCHAR(255) PRIMARY KEY,
    client_id   VARCHAR(255) NOT NULL REFERENCES mcp_oauth_clients(client_id) ON DELETE CASCADE,
    user_id     UUID         NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    scopes      TEXT[]       NOT NULL,
    expires_at  TIMESTAMPTZ,
    created_at  TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    revoked_at  TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS idx_mcp_refreshtokens_user ON mcp_refresh_tokens(user_id);
