"""Resolve the patient user_id for the current MCP request.

Two modes:
  - OAuth (multi-user): user_id comes from the bearer-token's auth context
  - Single-user fallback: settings.MCP_USER_ID (legacy phase 1)
"""
from typing import Optional

from mcp.server.auth.middleware.auth_context import get_access_token

from app.core.config import settings


def resolve_user_id() -> str:
    """Return the user_id whose data the current tool call should serve.

    Raises if no user can be resolved — defensive: tools should never silently
    serve nobody's data.
    """
    token = get_access_token()
    if token is not None:
        # MedHistoryAccessToken adds .user_id; falling back to attr access keeps
        # this working with any AccessToken subclass that exposes it.
        user_id = getattr(token, "user_id", None)
        if user_id:
            return user_id

    if settings.MCP_USER_ID:
        return settings.MCP_USER_ID

    raise RuntimeError("Cannot resolve user_id: no OAuth context and MCP_USER_ID not set")
