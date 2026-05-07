"""ASGI middleware: requires Authorization: Bearer <token> on every MCP request."""
import hmac
from starlette.types import ASGIApp, Receive, Scope, Send


class BearerAuthMiddleware:
    def __init__(self, app: ASGIApp, expected_token: str) -> None:
        self.app = app
        self.expected_token = expected_token

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        if not self._is_authorized(scope):
            await _send_401(send)
            return

        await self.app(scope, receive, send)

    def _is_authorized(self, scope: Scope) -> bool:
        for name, value in scope.get("headers", []):
            if name == b"authorization":
                header = value.decode("latin-1")
                if header.startswith("Bearer "):
                    presented = header[len("Bearer "):].strip()
                    return hmac.compare_digest(presented, self.expected_token)
                return False
        return False


async def _send_401(send: Send) -> None:
    await send({
        "type": "http.response.start",
        "status": 401,
        "headers": [
            (b"content-type", b"application/json"),
            (b"www-authenticate", b'Bearer realm="mcp"'),
        ],
    })
    await send({
        "type": "http.response.body",
        "body": b'{"error":"unauthorized"}',
    })
