"""Validation of Telegram Mini App initData (WebApp authentication).

Implements the HMAC-SHA256 check from Telegram's WebApp documentation: the
initData payload is signed with a key derived from the bot token. Used by the
/bot/auth/miniapp endpoint to authenticate a user opening the Mini App.
"""
import hashlib
import hmac
import json
import time
from urllib.parse import parse_qsl


class InitDataError(Exception):
    """Raised when Telegram initData fails validation."""


def parse_init_data(init_data: str, bot_token: str, *, max_age_seconds: int = 86400) -> dict:
    """Validate Telegram Mini App initData and return its parsed fields.

    The returned dict has the raw query fields plus `user` parsed into a dict.
    Raises InitDataError on any failure: missing token, malformed payload,
    signature mismatch, or a missing/expired auth_date.
    """
    if not bot_token:
        raise InitDataError("Telegram bot token is not configured")

    try:
        fields = dict(parse_qsl(init_data, strict_parsing=True))
    except ValueError as exc:
        raise InitDataError("initData is not a valid query string") from exc

    received_hash = fields.pop("hash", None)
    if not received_hash:
        raise InitDataError("initData is missing hash")

    data_check_string = "\n".join(f"{key}={fields[key]}" for key in sorted(fields))
    secret_key = hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()
    computed_hash = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()

    if not hmac.compare_digest(computed_hash, received_hash):
        raise InitDataError("initData signature mismatch")

    auth_date = fields.get("auth_date", "")
    if not auth_date.isdigit():
        raise InitDataError("initData is missing a valid auth_date")
    if time.time() - int(auth_date) > max_age_seconds:
        raise InitDataError("initData has expired")

    user_raw = fields.get("user")
    if not user_raw:
        raise InitDataError("initData is missing the user field")
    try:
        fields["user"] = json.loads(user_raw)
    except json.JSONDecodeError as exc:
        raise InitDataError("initData user field is not valid JSON") from exc

    return fields
