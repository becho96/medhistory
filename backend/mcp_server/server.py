"""
FastMCP server exposing patient medical data as tools.

Mounted into the main FastAPI app as a Starlette sub-app. Two modes:

  - Phase 1 (single-user, dev fallback): static bearer token, MCP_USER_ID hardcoded.
    Triggered when MCP_OAUTH_ENABLED=false. No DCR, no consent flow.
  - Phase 2 (multi-user, prod): real OAuth 2.1 + DCR via FastMCP's built-in
    auth scaffolding. Each request's user_id resolved from the bearer token.
"""
from mcp.server.auth.settings import AuthSettings, ClientRegistrationOptions, RevocationOptions
from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings

from app.core.config import settings
from app.db.postgres import AsyncSessionLocal
from mcp_server.auth import BearerAuthMiddleware
from mcp_server.oauth.provider import MedHistoryOAuthProvider
from mcp_server.tools import (
    profile,
    lab_results,
    documents,
    health_events,
    interpretations,
    search,
)

DEFAULT_SCOPES = ["read"]


def _build_mcp() -> FastMCP:
    auth_kwargs = {}
    if settings.MCP_OAUTH_ENABLED:
        provider = MedHistoryOAuthProvider(
            session_factory=AsyncSessionLocal,
            consent_url=settings.MCP_CONSENT_URL,
        )
        auth_kwargs = dict(
            auth_server_provider=provider,
            auth=AuthSettings(
                issuer_url=settings.MCP_PUBLIC_URL,
                resource_server_url=settings.MCP_PUBLIC_URL,
                client_registration_options=ClientRegistrationOptions(
                    enabled=True,
                    valid_scopes=DEFAULT_SCOPES,
                    default_scopes=DEFAULT_SCOPES,
                ),
                revocation_options=RevocationOptions(enabled=True),
                required_scopes=DEFAULT_SCOPES,
            ),
        )

    mcp = FastMCP(
        "medhistory-patient-data",
        instructions=(
            "You have access to the authenticated patient's medical history "
            "stored in the MedHistory service. Always retrieve the patient "
            "profile first to get gender and age for proper medical context "
            "and reference range selection."
        ),
        # Default streamable_http_path="/mcp"; with mount at "/mcp" final path
        # becomes "/mcp/mcp" — unambiguous, no trailing-slash redirect that POST
        # clients (e.g. claude.ai) refuse to follow.
        # DNS rebinding protection: off for ngrok/cloudflared dev tunnels;
        # production should set allowed_hosts=["mcp.medhistory.ru"] and re-enable.
        transport_security=TransportSecuritySettings(
            enable_dns_rebinding_protection=False,
        ),
        **auth_kwargs,
    )
    profile.register(mcp)
    lab_results.register(mcp)
    documents.register(mcp)
    health_events.register(mcp)
    interpretations.register(mcp)
    search.register(mcp)
    return mcp


# Module-level instance reused by both the mounted ASGI app and the stdio entrypoint.
mcp = _build_mcp()


def create_mcp_app(bearer_token: str | None):
    """Return an ASGI app (Starlette) ready to be mounted at /mcp.

    If OAuth is enabled, the FastMCP-built app already has its own auth
    middleware — we DO NOT wrap with BearerAuthMiddleware in that case.
    """
    inner = mcp.streamable_http_app()
    if settings.MCP_OAUTH_ENABLED:
        return inner
    if not bearer_token:
        return inner
    return BearerAuthMiddleware(inner, expected_token=bearer_token)


if __name__ == "__main__":
    # Local stdio debug: `python -m mcp_server.server`
    mcp.run()
