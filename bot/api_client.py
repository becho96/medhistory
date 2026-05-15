"""HTTP client for the MedHistory backend.

Auth model: the bot resolves a per-Telegram-user JWT through the trusted
/bot/auth endpoints (X-Bot-Secret) and caches it. Every per-user call then
reuses the existing /api/v1 endpoints with that JWT, so no business logic is
duplicated in the bot.
"""
import logging
from typing import Any, Optional

import httpx

import config

logger = logging.getLogger("medbot.api")


class ApiError(Exception):
    """A non-2xx response from the backend."""

    def __init__(self, status_code: int, detail: Any):
        self.status_code = status_code
        self.detail = detail
        super().__init__(f"API {status_code}: {detail}")


class NotLinkedError(Exception):
    """The Telegram user has no linked MedHistory account yet."""


def _detail(response: httpx.Response) -> Any:
    try:
        return response.json().get("detail", response.text)
    except Exception:
        return response.text


class ApiClient:
    def __init__(self) -> None:
        self._http = httpx.AsyncClient(
            base_url=config.BACKEND_URL + config.API_PREFIX,
            timeout=httpx.Timeout(120.0, connect=10.0),
        )
        self._tokens: dict[int, str] = {}
        self._user_ids: dict[int, str] = {}

    async def aclose(self) -> None:
        await self._http.aclose()

    def user_id(self, telegram_id: int) -> Optional[str]:
        return self._user_ids.get(telegram_id)

    # ── trusted bot endpoints (X-Bot-Secret) ─────────────────────────────────
    async def _bot_post(self, path: str, payload: dict) -> dict:
        response = await self._http.post(
            path, json=payload, headers={"X-Bot-Secret": config.BOT_SECRET}
        )
        if response.status_code >= 400:
            raise ApiError(response.status_code, _detail(response))
        return response.json()

    def _store_auth(self, telegram_id: int, data: dict) -> dict:
        self._tokens[telegram_id] = data["access_token"]
        self._user_ids[telegram_id] = data["user_id"]
        return data

    async def resolve(self, telegram_id: int) -> Optional[dict]:
        """Return fresh auth for a linked user, or None if not linked yet."""
        try:
            data = await self._bot_post("/bot/auth/resolve", {"telegram_id": telegram_id})
        except ApiError as exc:
            if exc.status_code == 404:
                return None
            raise
        return self._store_auth(telegram_id, data)

    async def register(
        self, telegram_id: int, full_name: Optional[str], consents: dict[str, str]
    ) -> dict:
        data = await self._bot_post("/bot/auth/register", {
            "telegram_id": telegram_id,
            "full_name": full_name,
            "consents": consents,
        })
        return self._store_auth(telegram_id, data)

    async def link(self, telegram_id: int, email: str, password: str) -> dict:
        data = await self._bot_post("/bot/auth/link", {
            "telegram_id": telegram_id,
            "email": email,
            "password": password,
        })
        return self._store_auth(telegram_id, data)

    # ── per-user calls (existing API, JWT auth) ──────────────────────────────
    async def _token(self, telegram_id: int) -> str:
        token = self._tokens.get(telegram_id)
        if token:
            return token
        auth = await self.resolve(telegram_id)
        if not auth:
            raise NotLinkedError()
        return auth["access_token"]

    async def request(
        self,
        method: str,
        path: str,
        telegram_id: int,
        *,
        profile_id: Optional[str] = None,
        **kwargs,
    ) -> httpx.Response:
        token = await self._token(telegram_id)
        headers = {"Authorization": f"Bearer {token}"}
        if profile_id:
            headers["X-Profile-Id"] = profile_id

        response = await self._http.request(method, path, headers=headers, **kwargs)
        if response.status_code == 401:
            # Token expired — re-resolve once.
            self._tokens.pop(telegram_id, None)
            auth = await self.resolve(telegram_id)
            if not auth:
                raise NotLinkedError()
            headers["Authorization"] = f"Bearer {auth['access_token']}"
            response = await self._http.request(method, path, headers=headers, **kwargs)

        if response.status_code >= 400:
            raise ApiError(response.status_code, _detail(response))
        return response

    async def _get_json(self, path: str, telegram_id: int, **kwargs) -> Any:
        return (await self.request("GET", path, telegram_id, **kwargs)).json()

    # documents
    async def upload_document(
        self, telegram_id: int, filename: str, content: bytes, profile_id=None
    ) -> dict:
        response = await self.request(
            "POST", "/documents/upload", telegram_id,
            profile_id=profile_id,
            files={"file": (filename, content)},
            timeout=180.0,
        )
        return response.json()

    async def list_documents(self, telegram_id: int, profile_id=None, limit: int = 50) -> list:
        return await self._get_json(
            "/documents/", telegram_id, profile_id=profile_id,
            params={"limit": limit, "sort_by": "created_at"},
        )

    async def get_document(self, telegram_id: int, document_id: str, profile_id=None) -> dict:
        return await self._get_json(
            f"/documents/{document_id}", telegram_id, profile_id=profile_id
        )

    async def get_labs(self, telegram_id: int, document_id: str, profile_id=None) -> dict:
        return await self._get_json(
            f"/documents/{document_id}/labs", telegram_id, profile_id=profile_id
        )

    async def download_file(self, telegram_id: int, document_id: str, profile_id=None) -> bytes:
        response = await self.request(
            "GET", f"/documents/{document_id}/file", telegram_id, profile_id=profile_id
        )
        return response.content

    async def list_analytes(self, telegram_id: int, profile_id=None) -> dict:
        return await self._get_json(
            "/documents/labs/analytes", telegram_id, profile_id=profile_id
        )

    async def get_timeseries(self, telegram_id: int, analyte: str, profile_id=None) -> dict:
        return await self._get_json(
            "/documents/labs/timeseries", telegram_id,
            profile_id=profile_id, params={"analyte": analyte},
        )

    # assistant
    async def ask_assistant(self, telegram_id: int, message: str, session_id=None) -> dict:
        response = await self.request(
            "POST", "/assistant/ask", telegram_id,
            json={"message": message, "session_id": session_id},
            timeout=180.0,
        )
        return response.json()

    # family
    async def list_profiles(self, telegram_id: int) -> list:
        return await self._get_json("/family/profiles", telegram_id)

    # subscription
    async def get_subscription(self, telegram_id: int) -> dict:
        return await self._get_json("/subscription/me", telegram_id)

    async def activate_promo(self, telegram_id: int, code: str) -> dict:
        response = await self.request(
            "POST", "/subscription/activate", telegram_id, json={"code": code}
        )
        return response.json()
