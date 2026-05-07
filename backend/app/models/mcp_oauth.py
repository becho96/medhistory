"""SQLAlchemy models for the MCP OAuth 2.1 server (phase 2: multi-user)."""
from sqlalchemy import Column, String, DateTime, Boolean, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY
from sqlalchemy.sql import func

from app.db.postgres import Base


class McpOAuthClient(Base):
    """DCR-registered OAuth client (RFC 7591). One row per registered client app."""
    __tablename__ = "mcp_oauth_clients"

    client_id       = Column(String(255), primary_key=True)
    client_secret   = Column(String(255), nullable=True)
    client_metadata = Column(JSONB,        nullable=False)
    issued_at       = Column(DateTime(timezone=True), server_default=func.now())


class McpAuthorizationCode(Base):
    """Short-lived (~10 min) authorization code, exchanged for tokens."""
    __tablename__ = "mcp_authorization_codes"

    code                              = Column(String(255), primary_key=True)
    client_id                         = Column(String(255), ForeignKey("mcp_oauth_clients.client_id", ondelete="CASCADE"), nullable=False)
    user_id                           = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    scopes                            = Column(ARRAY(Text), nullable=False)
    expires_at                        = Column(DateTime(timezone=True), nullable=False)
    code_challenge                    = Column(String(255), nullable=False)
    redirect_uri                      = Column(Text, nullable=False)
    redirect_uri_provided_explicitly  = Column(Boolean, nullable=False)
    resource                          = Column(Text, nullable=True)
    created_at                        = Column(DateTime(timezone=True), server_default=func.now())


class McpAccessToken(Base):
    """Access token bound to (client_id, user_id). Read on every MCP request."""
    __tablename__ = "mcp_access_tokens"

    token       = Column(String(255), primary_key=True)
    client_id   = Column(String(255), ForeignKey("mcp_oauth_clients.client_id", ondelete="CASCADE"), nullable=False, index=True)
    user_id     = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    scopes      = Column(ARRAY(Text), nullable=False)
    expires_at  = Column(DateTime(timezone=True), nullable=True)
    resource    = Column(Text, nullable=True)
    created_at  = Column(DateTime(timezone=True), server_default=func.now())
    revoked_at  = Column(DateTime(timezone=True), nullable=True)


class McpRefreshToken(Base):
    """Refresh token, used to mint new access tokens."""
    __tablename__ = "mcp_refresh_tokens"

    token       = Column(String(255), primary_key=True)
    client_id   = Column(String(255), ForeignKey("mcp_oauth_clients.client_id", ondelete="CASCADE"), nullable=False)
    user_id     = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    scopes      = Column(ARRAY(Text), nullable=False)
    expires_at  = Column(DateTime(timezone=True), nullable=True)
    created_at  = Column(DateTime(timezone=True), server_default=func.now())
    revoked_at  = Column(DateTime(timezone=True), nullable=True)
