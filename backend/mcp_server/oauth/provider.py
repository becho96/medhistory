"""OAuth 2.1 authorization server provider for MCP (phase 2 multi-user).

Implements the `OAuthAuthorizationServerProvider` Protocol that FastMCP's
`create_auth_routes` consumes. State lives in Postgres (mcp_oauth_clients,
mcp_authorization_codes, mcp_access_tokens, mcp_refresh_tokens).

Flow:
  1. claude.ai discovers OAuth metadata, POSTs /oauth/register → register_client
  2. claude.ai redirects user to /oauth/authorize → authorize() returns a URL
     pointing at our consent screen on the medhistory frontend
  3. User logs in (if needed), reviews scopes, approves → frontend POSTs to
     /api/v1/oauth/consent/decision with the pending_id; that endpoint creates
     the McpAuthorizationCode row and redirects browser to claude.ai's
     redirect_uri with code+state
  4. claude.ai POSTs /oauth/token → exchange_authorization_code mints the
     access+refresh token pair, stored bound to (client_id, user_id)
  5. claude.ai uses Bearer access_token on every MCP request → token_verifier
     looks up the row, exposes user_id to tools
"""
from __future__ import annotations

import json
import secrets
import time
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession

from mcp.server.auth.provider import (
    AccessToken,
    AuthorizationCode,
    AuthorizationParams,
    OAuthAuthorizationServerProvider,
    RefreshToken,
)


class MedHistoryAccessToken(AccessToken):
    """Access token enriched with the medhistory user_id, exposed to tools
    via `get_access_token()` from `mcp.server.auth.middleware.auth_context`."""
    user_id: str
from mcp.shared.auth import OAuthClientInformationFull, OAuthToken

from app.models.mcp_oauth import (
    McpOAuthClient,
    McpAuthorizationCode,
    McpAccessToken,
    McpRefreshToken,
)
from mcp_server.oauth import pending

ACCESS_TOKEN_TTL = timedelta(hours=1)
REFRESH_TOKEN_TTL = timedelta(days=30)
AUTH_CODE_TTL = timedelta(minutes=10)
DEFAULT_SCOPES = ["read"]


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _to_epoch(dt: Optional[datetime]) -> Optional[int]:
    return int(dt.timestamp()) if dt else None


class MedHistoryOAuthProvider(OAuthAuthorizationServerProvider):
    """OAuth 2.1 provider backed by Postgres + in-memory pending store."""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession], consent_url: str) -> None:
        self._session_factory = session_factory
        self._consent_url = consent_url

    # ── Client registration (DCR, RFC 7591) ────────────────────────────────

    async def get_client(self, client_id: str) -> Optional[OAuthClientInformationFull]:
        async with self._session_factory() as db:
            row = await db.get(McpOAuthClient, client_id)
        if row is None:
            return None
        return OAuthClientInformationFull(
            client_id=row.client_id,
            client_secret=row.client_secret,
            client_id_issued_at=int(row.issued_at.timestamp()) if row.issued_at else None,
            **row.client_metadata,
        )

    async def register_client(self, client_info: OAuthClientInformationFull) -> None:
        if not client_info.client_id:
            client_info.client_id = uuid.uuid4().hex
        if not client_info.client_secret:
            client_info.client_secret = secrets.token_urlsafe(32)
        client_info.client_id_issued_at = int(time.time())

        # Persist all RFC 7591 metadata fields except the synthesized id/secret.
        metadata = client_info.model_dump(
            mode="json",
            exclude={"client_id", "client_secret", "client_id_issued_at", "client_secret_expires_at"},
            exclude_none=True,
        )

        async with self._session_factory() as db:
            db.add(McpOAuthClient(
                client_id=client_info.client_id,
                client_secret=client_info.client_secret,
                client_metadata=metadata,
            ))
            await db.commit()

    # ── Authorization code grant ───────────────────────────────────────────

    async def authorize(self, client: OAuthClientInformationFull, params: AuthorizationParams) -> str:
        """Stash the authorization request and redirect the user-agent to our
        consent screen. The user's identity is established there (via the main
        medhistory.ru session), and a real auth code is minted on approval."""
        req_id = secrets.token_urlsafe(32)
        pending.put(req_id, pending.PendingConsent(
            client_id=client.client_id or "",
            # Clients (e.g. claude.ai) often omit explicit `scope=` and rely on
            # the server's defaults — fall back to DEFAULT_SCOPES so the issued
            # token actually satisfies `required_scopes` on protected requests.
            scopes=params.scopes or DEFAULT_SCOPES,
            code_challenge=params.code_challenge,
            redirect_uri=str(params.redirect_uri),
            redirect_uri_provided_explicitly=params.redirect_uri_provided_explicitly,
            state=params.state,
            resource=params.resource,
            expires_at=time.time() + 600,
        ))
        sep = "&" if "?" in self._consent_url else "?"
        return f"{self._consent_url}{sep}req={req_id}"

    async def load_authorization_code(
        self, client: OAuthClientInformationFull, authorization_code: str
    ) -> Optional[AuthorizationCode]:
        async with self._session_factory() as db:
            row = await db.get(McpAuthorizationCode, authorization_code)
        if row is None or row.client_id != client.client_id:
            return None
        if row.expires_at < _now():
            return None
        return AuthorizationCode(
            code=row.code,
            scopes=list(row.scopes or []),
            expires_at=row.expires_at.timestamp(),
            client_id=row.client_id,
            code_challenge=row.code_challenge,
            redirect_uri=row.redirect_uri,
            redirect_uri_provided_explicitly=row.redirect_uri_provided_explicitly,
            resource=row.resource,
        )

    async def exchange_authorization_code(
        self, client: OAuthClientInformationFull, authorization_code: AuthorizationCode
    ) -> OAuthToken:
        async with self._session_factory() as db:
            row = await db.get(McpAuthorizationCode, authorization_code.code)
            if row is None:
                raise ValueError("authorization code not found")
            user_id = row.user_id
            scopes = list(row.scopes or [])
            resource = row.resource
            await db.delete(row)  # auth codes are single-use
            await db.commit()

        return await self._mint_token_pair(
            client_id=client.client_id or "",
            user_id=user_id,
            scopes=scopes,
            resource=resource,
        )

    # ── Refresh token flow ─────────────────────────────────────────────────

    async def load_refresh_token(
        self, client: OAuthClientInformationFull, refresh_token: str
    ) -> Optional[RefreshToken]:
        async with self._session_factory() as db:
            row = await db.get(McpRefreshToken, refresh_token)
        if row is None or row.client_id != client.client_id or row.revoked_at is not None:
            return None
        if row.expires_at and row.expires_at < _now():
            return None
        return RefreshToken(
            token=row.token,
            client_id=row.client_id,
            scopes=list(row.scopes or []),
            expires_at=_to_epoch(row.expires_at),
        )

    async def exchange_refresh_token(
        self,
        client: OAuthClientInformationFull,
        refresh_token: RefreshToken,
        scopes: list[str],
    ) -> OAuthToken:
        # Look up to recover user_id (not part of RefreshToken DTO).
        async with self._session_factory() as db:
            row = await db.get(McpRefreshToken, refresh_token.token)
            if row is None:
                raise ValueError("refresh token not found")
            user_id = row.user_id
            # Rotate: revoke the presented refresh token.
            row.revoked_at = _now()
            await db.commit()

        # Requested scopes must be a subset of originally-issued scopes.
        granted = scopes if scopes else list(refresh_token.scopes)
        return await self._mint_token_pair(
            client_id=client.client_id or "",
            user_id=user_id,
            scopes=granted,
            resource=None,
        )

    # ── Access token verification ──────────────────────────────────────────

    async def load_access_token(self, token: str) -> Optional[AccessToken]:
        async with self._session_factory() as db:
            row = await db.get(McpAccessToken, token)
        if row is None or row.revoked_at is not None:
            return None
        if row.expires_at and row.expires_at < _now():
            return None
        return MedHistoryAccessToken(
            token=row.token,
            client_id=row.client_id,
            scopes=list(row.scopes or []),
            expires_at=_to_epoch(row.expires_at),
            resource=row.resource,
            user_id=str(row.user_id),
        )

    # ── Revocation ────────────────────────────────────────────────────────

    async def revoke_token(self, token) -> None:
        # `token` is either AccessToken or RefreshToken. Revoke whichever row
        # exists; ignore unknown tokens (RFC 7009 §2.2).
        async with self._session_factory() as db:
            for model in (McpAccessToken, McpRefreshToken):
                row = await db.get(model, token.token)
                if row is not None and row.revoked_at is None:
                    row.revoked_at = _now()
            await db.commit()

    # ── Internal ──────────────────────────────────────────────────────────

    async def _mint_token_pair(
        self,
        *,
        client_id: str,
        user_id: uuid.UUID,
        scopes: list[str],
        resource: Optional[str],
    ) -> OAuthToken:
        access = secrets.token_urlsafe(48)
        refresh = secrets.token_urlsafe(48)
        now = _now()
        access_exp = now + ACCESS_TOKEN_TTL
        refresh_exp = now + REFRESH_TOKEN_TTL

        async with self._session_factory() as db:
            db.add(McpAccessToken(
                token=access,
                client_id=client_id,
                user_id=user_id,
                scopes=scopes,
                expires_at=access_exp,
                resource=resource,
            ))
            db.add(McpRefreshToken(
                token=refresh,
                client_id=client_id,
                user_id=user_id,
                scopes=scopes,
                expires_at=refresh_exp,
            ))
            await db.commit()

        return OAuthToken(
            access_token=access,
            token_type="Bearer",
            expires_in=int(ACCESS_TOKEN_TTL.total_seconds()),
            scope=" ".join(scopes) if scopes else None,
            refresh_token=refresh,
        )
