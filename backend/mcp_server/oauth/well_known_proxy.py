"""ASGI middleware: rewrite OAuth/RFC-9728 discovery requests from the
domain root into the /mcp sub-app.

Why: claude.ai (and other strict OAuth clients) follow RFC 9728 / RFC 8414 to
the letter — they look for `.well-known/oauth-{authorization-server,
protected-resource}` at the **root** of the resource domain, ignoring any path
prefix in the issuer URL. In production behind nginx we serve the MCP server
on its own subdomain (`mcp.medhistory.ru`) where the root *is* the MCP root,
so this is a non-issue. In dev we run via ngrok pointing at port 8000 where
FastMCP is mounted at `/mcp` — without rewriting, those root-level lookups
return 404.

This middleware is a no-op when the requested path already starts with /mcp/.
"""
from starlette.types import ASGIApp, Receive, Scope, Send


_REWRITE_PREFIXES = (
    "/.well-known/oauth-authorization-server",
    "/.well-known/oauth-protected-resource",
    "/authorize",
    "/token",
    "/register",
    "/revoke",
)


class WellKnownProxyMiddleware:
    def __init__(self, app: ASGIApp, mount_prefix: str = "/mcp") -> None:
        self.app = app
        self.mount_prefix = mount_prefix.rstrip("/")

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] == "http":
            path = scope.get("path", "")
            if any(path == p or path.startswith(p + "/") or path.startswith(p + "?") for p in _REWRITE_PREFIXES):
                # Rewrite both `path` (used by routing) and `raw_path` (preserved
                # for upstreams that re-inspect the URL).
                new_path = f"{self.mount_prefix}{path}"
                scope = {**scope, "path": new_path, "raw_path": new_path.encode("latin-1")}
        await self.app(scope, receive, send)
