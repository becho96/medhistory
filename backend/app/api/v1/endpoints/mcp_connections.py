"""User-facing endpoints for managing MCP OAuth connections.

A "connection" = an active access token bound to (client_id, user_id). We let
the user list and revoke their connections from the medhistory.ru UI.
"""
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import and_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.postgres import get_db
from app.models.mcp_oauth import McpAccessToken, McpOAuthClient, McpRefreshToken
from app.models.user import User
from mcp_server.oauth.provider import _now

router = APIRouter()


class ConnectionItem(BaseModel):
    client_id: str
    client_name: Optional[str]
    issued_at: datetime
    expires_at: Optional[datetime]
    scopes: list[str]


@router.get("/connections", response_model=list[ConnectionItem])
async def list_connections(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[ConnectionItem]:
    """All non-revoked, non-expired access tokens for the current user."""
    now = _now()
    q = (
        select(McpAccessToken, McpOAuthClient)
        .join(McpOAuthClient, McpOAuthClient.client_id == McpAccessToken.client_id)
        .where(and_(
            McpAccessToken.user_id == current_user.id,
            McpAccessToken.revoked_at.is_(None),
        ))
        .order_by(McpAccessToken.created_at.desc())
    )
    rows = (await db.execute(q)).all()
    items: list[ConnectionItem] = []
    for tok, client in rows:
        if tok.expires_at and tok.expires_at < now:
            continue
        metadata = client.client_metadata or {}
        items.append(ConnectionItem(
            client_id=tok.client_id,
            client_name=metadata.get("client_name"),
            issued_at=tok.created_at,
            expires_at=tok.expires_at,
            scopes=list(tok.scopes or []),
        ))
    return items


@router.delete("/connections/{client_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_connection(
    client_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Revoke ALL tokens (access + refresh) for the given client tied to the
    current user. Future MCP calls with these tokens will return 401."""
    now = _now()
    await db.execute(
        update(McpAccessToken)
        .where(and_(
            McpAccessToken.user_id == current_user.id,
            McpAccessToken.client_id == client_id,
            McpAccessToken.revoked_at.is_(None),
        ))
        .values(revoked_at=now)
    )
    await db.execute(
        update(McpRefreshToken)
        .where(and_(
            McpRefreshToken.user_id == current_user.id,
            McpRefreshToken.client_id == client_id,
            McpRefreshToken.revoked_at.is_(None),
        ))
        .values(revoked_at=now)
    )
    await db.commit()
