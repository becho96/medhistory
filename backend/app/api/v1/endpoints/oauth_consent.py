"""Consent endpoints for the MCP OAuth flow.

claude.ai redirects the browser to /authorize on the MCP server. Our provider
redirects to medhistory.ru/oauth/consent?req=<id> (frontend route). The frontend
calls these two endpoints:

  GET  /api/v1/oauth/consent/info?req=<id>     — get client + scopes to show
  POST /api/v1/oauth/consent/decision           — approve/deny, returns redirect URL

Both require the medhistory JWT (auth_token in localStorage).
"""
import secrets
from datetime import timedelta
from typing import Literal, Optional
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.postgres import get_db
from app.models.mcp_oauth import McpAuthorizationCode, McpOAuthClient
from app.models.user import User
from mcp_server.oauth import pending
from mcp_server.oauth.provider import AUTH_CODE_TTL, _now

router = APIRouter()


class ConsentInfoResponse(BaseModel):
    client_id: str
    client_name: Optional[str]
    client_uri: Optional[str]
    scopes: list[str]


class ConsentDecisionRequest(BaseModel):
    req: str
    decision: Literal["approve", "deny"]


class ConsentDecisionResponse(BaseModel):
    redirect_url: str


@router.get("/consent/info", response_model=ConsentInfoResponse)
async def consent_info(
    req: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ConsentInfoResponse:
    p = pending.peek(req)
    if p is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Consent request expired or invalid")

    client = await db.get(McpOAuthClient, p.client_id)
    metadata = (client.client_metadata if client else None) or {}
    return ConsentInfoResponse(
        client_id=p.client_id,
        client_name=metadata.get("client_name"),
        client_uri=metadata.get("client_uri"),
        scopes=p.scopes,
    )


@router.post("/consent/decision", response_model=ConsentDecisionResponse)
async def consent_decision(
    body: ConsentDecisionRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ConsentDecisionResponse:
    p = pending.take(body.req)
    if p is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Consent request expired or invalid")

    if body.decision == "deny":
        params = {"error": "access_denied", "error_description": "User denied the request"}
        if p.state:
            params["state"] = p.state
        return ConsentDecisionResponse(redirect_url=f"{p.redirect_uri}?{urlencode(params)}")

    # Approved: mint a single-use authorization code bound to this user.
    code = secrets.token_urlsafe(48)
    db.add(McpAuthorizationCode(
        code=code,
        client_id=p.client_id,
        user_id=current_user.id,
        scopes=p.scopes,
        expires_at=_now() + AUTH_CODE_TTL,
        code_challenge=p.code_challenge,
        redirect_uri=p.redirect_uri,
        redirect_uri_provided_explicitly=p.redirect_uri_provided_explicitly,
        resource=p.resource,
    ))
    await db.commit()

    params = {"code": code}
    if p.state:
        params["state"] = p.state
    return ConsentDecisionResponse(redirect_url=f"{p.redirect_uri}?{urlencode(params)}")
